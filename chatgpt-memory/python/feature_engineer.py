#!/usr/bin/env python3
"""
Phase 2: feature_engineer.py
Extracts the full Phase 2 feature taxonomy from JSONL shards.
Produces feature-table.parquet and feature-table.jsonl.

Run: python feature_engineer.py --shards workspace/shards/ --out workspace/features/
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("[WARN] vaderSentiment not installed. Sentiment features will be null.")


# ---------------------------------------------------------------------------
# Regex patterns (compiled once)
# ---------------------------------------------------------------------------

RE_CONSTRAINTS      = re.compile(r"\b(do not|must|only|never|always|required|mandatory)\b", re.I)
RE_NUMBERED_STEPS   = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)
RE_ROLE_ASSIGN      = re.compile(r"\b(you are|act as|pretend|imagine you|you're a)\b", re.I)
RE_QUESTION_END     = re.compile(r"\?(?:\s|$)")
RE_CODE_BLOCK       = re.compile(r"```")
RE_CORRECTION       = re.compile(r"\b(that'?s wrong|not what i meant|try again|incorrect|that is wrong|no,|wrong,)\b", re.I)
RE_SUCCESS          = re.compile(r"\b(perfect|exactly|works?|that'?s it|great|thank|correct|yes,? that)\b", re.I)
RE_URGENCY          = re.compile(r"\b(urgent|asap|immediately|critical|emergency|right now)\b", re.I)
RE_FRUSTRATION      = re.compile(r"\b(frustrated|annoying|useless|wrong again|still wrong|not working|terrible)\b", re.I)
RE_GRATITUDE        = re.compile(r"\b(thank|thanks|grateful|appreciate|great job|well done|perfect)\b", re.I)
RE_REFUSAL          = re.compile(r"\b(i'?m not able to|i can'?t help|i cannot help|unable to assist)\b", re.I)
RE_POLICY           = re.compile(r"\b(against my guidelines|my guidelines|harmful content|not appropriate)\b", re.I)
RE_CAUTION          = re.compile(r"\b(i should note|please note|caution|warning:|disclaimer)\b", re.I)
RE_CITATIONS        = re.compile(r"(https?://\S+|\[\d+\]|\(\d+\)|\bsource:)", re.I)
RE_ASSUMPTIONS      = re.compile(r"\b(assuming|i'?ll assume|i assume|assuming that)\b", re.I)
RE_FAIL_CLOSED      = re.compile(r"\b(i don'?t have|i cannot|i need more|insufficient information|not enough)\b", re.I)
RE_CONFIDENCE       = re.compile(r"\b(i think|likely|probably|approximately|roughly|around|maybe)\b", re.I)
RE_MULTI_STEP       = re.compile(r"(?:^\s*\d+[.)]\s.+\n){3,}", re.MULTILINE)


# ---------------------------------------------------------------------------
# Feature extraction per conversation
# ---------------------------------------------------------------------------

def extract_features(conv: dict, vader: object | None) -> dict:
    conv_id = conv.get("conv_id", "")
    create_time = conv.get("create_time")
    model = conv.get("model")
    messages = conv.get("messages") or []

    user_messages = [m for m in messages if m.get("role") == "user"]
    asst_messages = [m for m in messages if m.get("role") == "assistant"]
    tool_messages = [m for m in messages if m.get("role") == "tool"]

    first_user_text = _join_texts(user_messages[:1])
    all_user_text   = _join_texts(user_messages)
    all_asst_text   = _join_texts(asst_messages)

    # --- Prompt attributes ---
    prompt_token_est  = sum(m.get("token_est") or 0 for m in user_messages)
    response_token_est = sum(m.get("token_est") or 0 for m in asst_messages)
    turn_count        = conv.get("turn_count") or 0
    avg_response_len  = (response_token_est / len(asst_messages)) if asst_messages else None

    has_system_instruction  = conv.get("has_system_message") or False
    has_explicit_constraints = bool(RE_CONSTRAINTS.search(first_user_text))
    has_numbered_steps       = bool(RE_NUMBERED_STEPS.search(first_user_text))
    has_role_assignment      = bool(RE_ROLE_ASSIGN.search(first_user_text))
    question_count           = len(RE_QUESTION_END.findall(all_user_text))
    specificity_score        = _specificity(first_user_text)

    # --- Complexity proxies ---
    code_block_count = len(RE_CODE_BLOCK.findall(all_asst_text)) // 2
    code_line_count  = _count_code_lines(all_asst_text)
    tool_call_count  = len(tool_messages)
    multi_step_plan  = bool(RE_MULTI_STEP.search(all_asst_text))
    branching_depth  = _compute_branching_depth(messages)

    # --- Emotional signals ---
    sentiment = None
    if vader and first_user_text:
        scores = vader.polarity_scores(first_user_text)
        sentiment = round(scores["compound"], 4)

    urgency_signal     = bool(RE_URGENCY.search(all_user_text))
    frustration_signal = bool(RE_FRUSTRATION.search(all_user_text))
    gratitude_signal   = bool(RE_GRATITUDE.search(all_user_text))
    conflict_signal    = frustration_signal and (sentiment is not None and sentiment < -0.3)

    # --- Performance outcomes ---
    rework_count   = _count_rework_loops(messages)
    correction_count = len(RE_CORRECTION.findall(all_user_text))
    success_signal = bool(RE_SUCCESS.search(all_user_text[-500:] if len(all_user_text) > 500 else all_user_text))
    abandoned      = bool(messages) and messages[-1].get("role") == "user"
    regression     = _count_regressions(user_messages)

    first_time = _get_time(messages, "user")
    success_time = _get_time(messages, "user", last=True) if success_signal else None
    time_to_res = None
    if first_time and success_time and success_signal:
        time_to_res = round((success_time - first_time) / 60, 2)

    # --- Governance ---
    has_citations     = bool(RE_CITATIONS.search(all_asst_text))
    explicit_assume   = bool(RE_ASSUMPTIONS.search(all_asst_text))
    fail_closed       = bool(RE_FAIL_CLOSED.search(all_asst_text))
    confidence_qual   = bool(RE_CONFIDENCE.search(all_asst_text))

    # --- Safety ---
    refusal_detected  = bool(RE_REFUSAL.search(all_asst_text))
    policy_boundary   = bool(RE_POLICY.search(all_asst_text))
    content_warning   = bool(RE_CAUTION.search(all_asst_text))

    return {
        "conv_id":                   conv_id,
        "create_time":               create_time,
        "model":                     model,
        "computed_at":               time.time(),
        "prompt_token_est":          prompt_token_est,
        "response_token_est":        response_token_est,
        "turn_count":                turn_count,
        "avg_response_length":       avg_response_len,
        "has_system_instruction":    has_system_instruction,
        "has_explicit_constraints":  has_explicit_constraints,
        "has_numbered_steps":        has_numbered_steps,
        "has_role_assignment":       has_role_assignment,
        "question_count":            question_count,
        "specificity_score":         specificity_score,
        "prompt_archetype":          None,          # LLM-assisted; filled later
        "prompt_archetype_method":   None,
        "code_block_count":          code_block_count,
        "code_line_count":           code_line_count,
        "tool_call_count":           tool_call_count,
        "multi_step_plan_detected":  multi_step_plan,
        "branching_depth":           branching_depth,
        "prompt_sentiment":          sentiment,
        "urgency_signal":            urgency_signal,
        "frustration_signal":        frustration_signal,
        "gratitude_signal":          gratitude_signal,
        "conflict_signal":           conflict_signal,
        "rework_loop_count":         rework_count,
        "correction_count":          correction_count,
        "success_signal":            success_signal,
        "conversation_abandoned":    abandoned,
        "regression_count":          regression,
        "time_to_resolution":        time_to_res,
        "has_citations":             has_citations,
        "explicit_assumptions":      explicit_assume,
        "fail_closed_language":      fail_closed,
        "confidence_qualifier":      confidence_qual,
        "refusal_detected":          refusal_detected,
        "policy_boundary_hit":       policy_boundary,
        "content_warning_present":   content_warning,
    }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _join_texts(messages: list[dict]) -> str:
    parts = [m.get("text") or "" for m in messages]
    return " ".join(parts)


def _specificity(text: str) -> float | None:
    if not text:
        return None
    words = text.lower().split()
    if not words:
        return None
    # Proxy: unique words / total words (higher = more specific vocabulary)
    return round(len(set(words)) / len(words), 4)


def _count_code_lines(text: str) -> int:
    in_block = False
    count = 0
    for line in text.splitlines():
        if line.startswith("```"):
            in_block = not in_block
        elif in_block:
            count += 1
    return count


def _compute_branching_depth(messages: list[dict]) -> int:
    # Simple proxy: number of turns (actual tree depth needs the raw mapping)
    return len(messages)


def _count_rework_loops(messages: list[dict]) -> int:
    count = 0
    for i in range(1, len(messages) - 1):
        prev_role = messages[i - 1].get("role")
        curr_role = messages[i].get("role")
        if prev_role == "assistant" and curr_role == "user":
            text = messages[i].get("text") or ""
            if RE_CORRECTION.search(text):
                count += 1
    return count


def _count_regressions(user_messages: list[dict]) -> int:
    texts = [m.get("text") or "" for m in user_messages]
    count = 0
    for i in range(1, len(texts)):
        for j in range(i):
            if texts[j] and texts[i] and texts[j][:50].lower() == texts[i][:50].lower():
                count += 1
                break
    return count


def _get_time(messages: list[dict], role: str, last: bool = False) -> float | None:
    times = [m.get("create_time") for m in messages if m.get("role") == role and m.get("create_time")]
    if not times:
        return None
    return times[-1] if last else times[0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2: Feature engineering")
    parser.add_argument("--shards", required=True, help="Directory containing shard JSONL files")
    parser.add_argument("--out",    required=True, help="Output directory for feature files")
    args = parser.parse_args()

    shards_dir = Path(args.shards).resolve()
    out_dir    = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    shard_files = sorted(shards_dir.glob("shard_*.jsonl"))
    if not shard_files:
        print(f"ERROR: No shard files found in {shards_dir}", file=sys.stderr)
        sys.exit(1)

    vader = SentimentIntensityAnalyzer() if VADER_AVAILABLE else None

    rows = []
    for shard_path in tqdm(shard_files, desc="Processing shards"):
        with open(shard_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                conv = json.loads(line)
                rows.append(extract_features(conv, vader))

    print(f"Extracted features for {len(rows):,} conversations.")

    df = pd.DataFrame(rows)

    parquet_path = out_dir / "feature-table.parquet"
    jsonl_path   = out_dir / "feature-table.jsonl"

    df.to_parquet(parquet_path, index=False, engine="pyarrow")
    df.to_json(jsonl_path, orient="records", lines=True, force_ascii=False)

    print(f"  Parquet : {parquet_path} ({parquet_path.stat().st_size / 1e6:.1f} MB)")
    print(f"  JSONL   : {jsonl_path}")
    print(f"\nNext: python build_index.py --shards {shards_dir} --features {out_dir}")


if __name__ == "__main__":
    main()
