#!/usr/bin/env python3
"""
Phase 1: parse_export.py
Streaming parse of conversations.json from a ChatGPT export zip.
Produces deterministic JSONL shards + a python-manifest.json.

Run: python parse_export.py --zip export.zip --out workspace/
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import ijson
from tqdm import tqdm

PIPELINE_VERSION = "1.0.0"
TARGET_SHARD_BYTES = 8 * 1024 * 1024   # 8 MB uncompressed per shard
CONVERSATIONS_FILENAME = "conversations.json"


# ---------------------------------------------------------------------------
# ID helpers (must match schemas/conversation.schema.json)
# ---------------------------------------------------------------------------

def conv_id(source_id: str, create_time: float | None) -> str:
    sha8 = hashlib.sha256(source_id.encode()).hexdigest()[:8]
    epoch = int(create_time) if create_time else 0
    return f"conv_{sha8}_{epoch}"


def msg_id(conv_source_id: str, turn_index: int, role: str) -> str:
    sha8 = hashlib.sha256(conv_source_id.encode()).hexdigest()[:8]
    role3 = (role or "unk")[:3]
    return f"msg_{sha8}_{turn_index:04d}_{role3}"


# ---------------------------------------------------------------------------
# Conversation normalizer
# ---------------------------------------------------------------------------

def normalize_conversation(raw: dict) -> dict:
    """Convert a raw ChatGPT export conversation into the canonical schema."""
    source_id   = raw.get("id") or raw.get("conversation_id") or ""
    create_time = raw.get("create_time")
    update_time = raw.get("update_time")
    title       = raw.get("title")

    cid = conv_id(source_id, create_time)

    # Linearise the conversation tree (mapping → ordered list of messages)
    mapping     = raw.get("mapping") or {}
    current_node = raw.get("current_node")
    messages    = _linearise_mapping(mapping, current_node)

    # Detect model from assistant metadata
    model = _detect_model(messages)

    turn_count = sum(
        1 for m in messages
        if m.get("role") in ("user", "assistant")
    ) // 2

    msg_ids = [
        msg_id(source_id, i, m.get("role", "unk"))
        for i, m in enumerate(messages)
    ]

    has_system = any(m.get("role") == "system" for m in messages)

    return {
        "conv_id":            cid,
        "source_id":          source_id,
        "title":              title,
        "create_time":        create_time,
        "update_time":        update_time,
        "model":              model,
        "turn_count":         turn_count,
        "message_ids":        msg_ids,
        "has_system_message": has_system,
        "plugin_ids":         _detect_plugins(messages),
        "messages":           messages,   # inline for shard storage
        # shard_file / shard_line filled by sharding logic
    }


def _linearise_mapping(mapping: dict, current_node: str | None) -> list[dict]:
    """Walk the conversation tree from root → current_node and return ordered messages."""
    if not mapping:
        return []

    # Build child → parent map and collect all node IDs
    parent_of: dict[str, str | None] = {}
    for node_id, node in mapping.items():
        parent_of[node_id] = node.get("parent")

    # Find root (node with no parent or parent not in mapping)
    root_ids = [nid for nid, par in parent_of.items() if not par or par not in mapping]
    root_id  = root_ids[0] if root_ids else None

    # Walk from current_node back to root to get the active path
    path: list[str] = []
    node = current_node
    while node and node in mapping:
        path.append(node)
        node = parent_of.get(node)

    path.reverse()   # root first

    messages = []
    for idx, node_id in enumerate(path):
        raw_node = mapping.get(node_id, {})
        raw_msg  = raw_node.get("message") or {}
        if not raw_msg:
            continue

        author  = raw_msg.get("author") or {}
        role    = author.get("role", "unknown")
        content = raw_msg.get("content") or {}
        parts   = content.get("parts") or []

        text = _extract_text(parts, content.get("content_type", "text"))

        messages.append({
            "role":         role,
            "content_type": content.get("content_type", "text"),
            "text":         text,
            "token_est":    _estimate_tokens(text),
            "create_time":  raw_msg.get("create_time"),
            "metadata":     raw_msg.get("metadata") or {},
        })

    return messages


def _extract_text(parts: list, content_type: str) -> str | None:
    if content_type == "text":
        texts = [p for p in parts if isinstance(p, str)]
        return "\n".join(texts) if texts else None
    if content_type in ("tether_browsing_display", "tether_quote"):
        return None   # Non-text; skip for now
    # For code and other types, try string extraction
    texts = [p for p in parts if isinstance(p, str)]
    return "\n".join(texts) if texts else None


def _estimate_tokens(text: str | None) -> int | None:
    if text is None:
        return None
    return math.ceil(len(text.split()) * 1.3)


def _detect_model(messages: list[dict]) -> str | None:
    for m in reversed(messages):
        slug = (m.get("metadata") or {}).get("model_slug")
        if slug:
            return slug
    return None


def _detect_plugins(messages: list[dict]) -> list[str]:
    plugins: set[str] = set()
    for m in messages:
        meta = m.get("metadata") or {}
        if "invoked_plugin" in meta:
            plugins.add(meta["invoked_plugin"].get("namespace", "unknown"))
    return sorted(plugins)


# ---------------------------------------------------------------------------
# Sharding
# ---------------------------------------------------------------------------

def shard_conversations(conversations: list[dict], target_bytes: int) -> list[list[dict]]:
    """
    Pack conversations into shards.
    Deterministic: conversations sorted by create_time ASC, then source_id.
    Never splits a conversation across shards.
    """
    sorted_convs = sorted(
        conversations,
        key=lambda c: (c.get("create_time") or 0, c.get("source_id") or "")
    )

    shards: list[list[dict]] = []
    current_shard: list[dict] = []
    current_size = 0

    for conv in sorted_convs:
        conv_bytes = len(json.dumps(conv).encode())
        if current_shard and (current_size + conv_bytes) > target_bytes:
            shards.append(current_shard)
            current_shard = []
            current_size  = 0
        current_shard.append(conv)
        current_size += conv_bytes

    if current_shard:
        shards.append(current_shard)

    return shards


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1: Parse ChatGPT export → JSONL shards")
    parser.add_argument("--zip",   required=True, help="Path to export zip file")
    parser.add_argument("--out",   required=True, help="Workspace root directory")
    parser.add_argument("--shard-mb", type=int, default=8, help="Target shard size in MB (default: 8)")
    args = parser.parse_args()

    zip_path  = Path(args.zip).resolve()
    out_root  = Path(args.out).resolve()
    shards_dir    = out_root / "shards"
    manifests_dir = out_root / "manifests"

    shards_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    target_bytes = args.shard_mb * 1024 * 1024

    if not zip_path.exists():
        print(f"ERROR: Zip not found: {zip_path}", file=sys.stderr)
        sys.exit(1)

    # ----- Stream parse conversations.json from zip -----
    print(f"Opening {zip_path} ({zip_path.stat().st_size / 1e9:.2f} GB)…")

    conversations: list[dict] = []
    total_messages = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        if CONVERSATIONS_FILENAME not in zf.namelist():
            print(f"ERROR: {CONVERSATIONS_FILENAME} not found in zip.", file=sys.stderr)
            sys.exit(1)

        with zf.open(CONVERSATIONS_FILENAME) as raw_stream:
            # Use text wrapper for ijson
            text_stream = io.TextIOWrapper(raw_stream, encoding="utf-8")
            items = ijson.items(text_stream, "item")

            print("Parsing conversations (streaming)…")
            for raw_conv in tqdm(items, unit=" conv"):
                norm = normalize_conversation(raw_conv)
                total_messages += len(norm.get("messages") or [])
                conversations.append(norm)

    print(f"Parsed {len(conversations):,} conversations, {total_messages:,} messages.")

    # ----- Shard -----
    print(f"Sharding (target {args.shard_mb} MB per shard)…")
    sharded = shard_conversations(conversations, target_bytes)
    print(f"  {len(sharded)} shards.")

    # ----- Write shards + conv-index -----
    shard_manifest_entries = []
    conv_index_path = manifests_dir / "conv-index.jsonl"

    with open(conv_index_path, "w", encoding="utf-8") as conv_idx:
        for shard_idx, shard in enumerate(tqdm(sharded, desc="Writing shards")):
            times = [c.get("create_time") or 0 for c in shard]
            first_dt = datetime.fromtimestamp(min(times), tz=timezone.utc).date().isoformat()
            last_dt  = datetime.fromtimestamp(max(times), tz=timezone.utc).date().isoformat()

            filename = f"shard_{shard_idx:04d}_{first_dt}_{last_dt}.jsonl"
            shard_path = shards_dir / filename

            sha = hashlib.sha256()
            msg_count = 0

            with open(shard_path, "w", encoding="utf-8") as sf:
                for line_idx, conv in enumerate(shard):
                    conv["shard_file"] = filename
                    conv["shard_line"] = line_idx

                    line = json.dumps(conv, ensure_ascii=False)
                    sf.write(line + "\n")
                    sha.update(line.encode())
                    msg_count += len(conv.get("messages") or [])

                    # Write minimal entry to conv-index
                    index_entry = {
                        "conv_id":      conv["conv_id"],
                        "source_id":    conv["source_id"],
                        "title":        conv.get("title"),
                        "create_time":  conv.get("create_time"),
                        "model":        conv.get("model"),
                        "turn_count":   conv.get("turn_count"),
                        "shard_file":   filename,
                        "shard_line":   line_idx,
                    }
                    conv_idx.write(json.dumps(index_entry, ensure_ascii=False) + "\n")

            shard_manifest_entries.append({
                "shard_index":       shard_idx,
                "filename":          filename,
                "sha256":            sha.hexdigest(),
                "size_bytes":        shard_path.stat().st_size,
                "conversation_count": len(shard),
                "message_count":     msg_count,
                "first_create_time": datetime.fromtimestamp(min(times), tz=timezone.utc).isoformat(),
                "last_create_time":  datetime.fromtimestamp(max(times), tz=timezone.utc).isoformat(),
                "conv_ids":          [c["conv_id"] for c in shard],
            })

    # ----- Write python-manifest.json -----
    all_times = [c.get("create_time") or 0 for c in conversations]
    python_manifest = {
        "pipeline_version":  PIPELINE_VERSION,
        "generated_at":      datetime.now(tz=timezone.utc).isoformat(),
        "total_conversations": len(conversations),
        "total_messages":    total_messages,
        "date_range": {
            "earliest_utc": datetime.fromtimestamp(min(all_times), tz=timezone.utc).isoformat(),
            "latest_utc":   datetime.fromtimestamp(max(all_times), tz=timezone.utc).isoformat(),
        },
        "shards": shard_manifest_entries,
    }

    manifest_path = manifests_dir / "python-manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(python_manifest, f, indent=2, ensure_ascii=False)

    print(f"\nDone.")
    print(f"  Shards written  : {len(sharded)} → {shards_dir}/")
    print(f"  Conv index      : {conv_index_path}")
    print(f"  Python manifest : {manifest_path}")
    print(f"\nNext: pwsh scripts/Invoke-ExportIngest.ps1 -WorkspaceRoot {out_root} -DetectionReportPath <detection-report.json>")


if __name__ == "__main__":
    main()
