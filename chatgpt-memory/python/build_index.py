#!/usr/bin/env python3
"""
Phase 3: build_index.py
Builds the SQLite memory index from JSONL shards and the feature table.
Optionally builds FAISS embeddings index if sentence-transformers is available.

Run: python build_index.py --shards workspace/shards/ --features workspace/features/ --db workspace/index/memory.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS conversations (
    conv_id         TEXT PRIMARY KEY,
    source_id       TEXT,
    title           TEXT,
    create_time     REAL,
    update_time     REAL,
    model           TEXT,
    turn_count      INTEGER,
    has_system_msg  INTEGER,
    shard_file      TEXT,
    shard_line      INTEGER
);

CREATE TABLE IF NOT EXISTS messages (
    msg_id          TEXT PRIMARY KEY,
    conv_id         TEXT REFERENCES conversations(conv_id),
    role            TEXT,
    content_type    TEXT,
    text            TEXT,
    token_est       INTEGER,
    create_time     REAL,
    turn_index      INTEGER
);

CREATE TABLE IF NOT EXISTS features (
    conv_id                     TEXT PRIMARY KEY REFERENCES conversations(conv_id),
    create_time                 REAL,
    model                       TEXT,
    computed_at                 REAL,
    prompt_token_est            INTEGER,
    response_token_est          INTEGER,
    turn_count                  INTEGER,
    avg_response_length         REAL,
    has_system_instruction      INTEGER,
    has_explicit_constraints    INTEGER,
    has_numbered_steps          INTEGER,
    has_role_assignment         INTEGER,
    question_count              INTEGER,
    specificity_score           REAL,
    prompt_archetype            TEXT,
    code_block_count            INTEGER,
    code_line_count             INTEGER,
    tool_call_count             INTEGER,
    multi_step_plan_detected    INTEGER,
    branching_depth             INTEGER,
    prompt_sentiment            REAL,
    urgency_signal              INTEGER,
    frustration_signal          INTEGER,
    gratitude_signal            INTEGER,
    conflict_signal             INTEGER,
    rework_loop_count           INTEGER,
    correction_count            INTEGER,
    success_signal              INTEGER,
    conversation_abandoned      INTEGER,
    regression_count            INTEGER,
    time_to_resolution          REAL,
    has_citations               INTEGER,
    explicit_assumptions        INTEGER,
    fail_closed_language        INTEGER,
    confidence_qualifier        INTEGER,
    refusal_detected            INTEGER,
    policy_boundary_hit         INTEGER,
    content_warning_present     INTEGER
);

CREATE TABLE IF NOT EXISTS episodic_memory (
    episode_id      TEXT PRIMARY KEY,
    title           TEXT,
    summary         TEXT,
    tags            TEXT,       -- JSON array
    source_conv_ids TEXT,       -- JSON array
    source_spans    TEXT,       -- JSON array of {conv_id, shard_file, turn_start, turn_end, quote}
    created_at      REAL,
    updated_at      REAL,
    version         INTEGER DEFAULT 1,
    grounded        INTEGER DEFAULT 1
);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    msg_id UNINDEXED,
    conv_id UNINDEXED,
    role,
    text,
    content=messages,
    content_rowid=rowid
);

CREATE INDEX IF NOT EXISTS idx_conv_create_time ON conversations(create_time);
CREATE INDEX IF NOT EXISTS idx_conv_model ON conversations(model);
CREATE INDEX IF NOT EXISTS idx_msg_conv_id ON messages(conv_id);
CREATE INDEX IF NOT EXISTS idx_feat_model ON features(model);
CREATE INDEX IF NOT EXISTS idx_feat_refusal ON features(refusal_detected);
"""


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_shards_into_db(db: sqlite3.Connection, shards_dir: Path) -> int:
    shard_files = sorted(shards_dir.glob("shard_*.jsonl"))
    total_convs = 0
    total_msgs  = 0

    for shard_path in tqdm(shard_files, desc="Indexing shards"):
        with open(shard_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                conv = json.loads(line)
                _insert_conversation(db, conv, shard_path.name)
                total_convs += 1
                total_msgs  += len(conv.get("messages") or [])

    print(f"  Indexed {total_convs:,} conversations, {total_msgs:,} messages.")
    return total_convs


def _insert_conversation(db: sqlite3.Connection, conv: dict, shard_filename: str) -> None:
    db.execute("""
        INSERT OR REPLACE INTO conversations
            (conv_id, source_id, title, create_time, update_time, model,
             turn_count, has_system_msg, shard_file, shard_line)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        conv.get("conv_id"),
        conv.get("source_id"),
        conv.get("title"),
        conv.get("create_time"),
        conv.get("update_time"),
        conv.get("model"),
        conv.get("turn_count"),
        1 if conv.get("has_system_message") else 0,
        shard_filename,
        conv.get("shard_line"),
    ))

    messages = conv.get("messages") or []
    conv_sha8 = (conv.get("conv_id") or "").replace("conv_", "").split("_")[0]

    for idx, msg in enumerate(messages):
        role  = msg.get("role") or "unk"
        mid   = f"msg_{conv_sha8}_{idx:04d}_{role[:3]}"

        db.execute("""
            INSERT OR REPLACE INTO messages
                (msg_id, conv_id, role, content_type, text, token_est, create_time, turn_index)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            mid,
            conv.get("conv_id"),
            role,
            msg.get("content_type"),
            msg.get("text"),
            msg.get("token_est"),
            msg.get("create_time"),
            idx,
        ))


def load_features_into_db(db: sqlite3.Connection, features_path: Path) -> None:
    df = pd.read_parquet(features_path)
    print(f"  Loading {len(df):,} feature rows…")

    bool_cols = [
        "has_system_instruction", "has_explicit_constraints", "has_numbered_steps",
        "has_role_assignment", "multi_step_plan_detected", "urgency_signal",
        "frustration_signal", "gratitude_signal", "conflict_signal", "success_signal",
        "conversation_abandoned", "has_citations", "explicit_assumptions",
        "fail_closed_language", "confidence_qualifier", "refusal_detected",
        "policy_boundary_hit", "content_warning_present",
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map(lambda x: 1 if x is True else (0 if x is False else None))

    df.to_sql("features", db, if_exists="replace", index=False, method="multi", chunksize=1000)
    print(f"  Features loaded.")


def rebuild_fts(db: sqlite3.Connection) -> None:
    print("  Rebuilding FTS index…")
    db.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3: Build SQLite memory index")
    parser.add_argument("--shards",   required=True)
    parser.add_argument("--features", required=True)
    parser.add_argument("--db",       default="workspace/index/memory.db")
    args = parser.parse_args()

    shards_dir    = Path(args.shards).resolve()
    features_path = Path(args.features).resolve() / "feature-table.parquet"
    db_path       = Path(args.db).resolve()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not shards_dir.exists():
        print(f"ERROR: Shards dir not found: {shards_dir}", file=sys.stderr)
        sys.exit(1)
    if not features_path.exists():
        print(f"ERROR: feature-table.parquet not found at {features_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Building index: {db_path}")
    t0 = time.time()

    db = sqlite3.connect(db_path)
    try:
        db.executescript(DDL)
        load_shards_into_db(db, shards_dir)
        load_features_into_db(db, features_path)
        rebuild_fts(db)
        db.commit()
    finally:
        db.close()

    elapsed = round(time.time() - t0, 1)
    size_mb = round(db_path.stat().st_size / 1e6, 1)

    print(f"\nIndex built in {elapsed}s  →  {db_path} ({size_mb} MB)")
    print(f"\nExample queries:")
    print(f"  sqlite3 {db_path} \"SELECT model, COUNT(*) FROM conversations GROUP BY model;\"")
    print(f"  sqlite3 {db_path} \"SELECT * FROM messages_fts WHERE messages_fts MATCH 'authentication error' LIMIT 10;\"")
    print(f"\nNext: python report.py --db {db_path} --out workspace/reports/")


if __name__ == "__main__":
    main()
