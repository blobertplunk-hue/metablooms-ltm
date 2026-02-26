# ChatGPT Export → Governed Memory System
## End-to-End Pipeline Specification

**Version:** 1.0.0 | **Audience:** Local operator + LLM assistant
**Constraint:** 3.8 GB corpus stays local. Only derived artifacts (≤ a few MB each) are uploaded to the LLM.

---

## Assumptions

| # | Assumption | Verification step | If false |
|---|-----------|------------------|----------|
| A1 | Export is a `.zip` from Settings → Data controls → Export | `Invoke-ExportDetect.ps1` checks structure | Adjust Phase 0 detection map |
| A2 | `conversations.json` is the primary payload | File detection in Phase 0 | Rebuild schema for alternate format |
| A3 | Windows 11 with PowerShell 7.4+ and Python 3.11+ available | `pwsh --version`, `python --version` | Install from aka.ms/install-powershell and python.org |
| A4 | Corpus fits on local disk (need ~2× for working files) | `(Get-Item export.zip).Length` | Shard directly from zip stream |
| A5 | No GPU required (CPU embeddings acceptable for MVP) | Assumed; `sentence-transformers` runs on CPU | Add GPU path in Phase 3 if needed |
| A6 | User controls redaction scope | Reviewed in `config/redaction-patterns.json` | Adjust patterns before processing |

---

## Folder Layout

```
chatgpt-memory/
├── PIPELINE-SPEC.md          ← this file
├── RUNBOOK.md                ← step-by-step operator runbook
│
├── config/
│   ├── redaction-patterns.json   ← PII / sensitive term patterns
│   └── feature-config.json       ← feature engineering parameters
│
├── schemas/
│   ├── conversation.schema.json
│   ├── message.schema.json
│   ├── shard-manifest.schema.json
│   └── feature-table.schema.json
│
├── scripts/                  ← PowerShell 7.4+ (competency-compliant)
│   ├── Invoke-ExportDetect.ps1
│   ├── Invoke-ExportIngest.ps1
│   └── Invoke-Redact.ps1
│
├── python/                   ← Python 3.11+ data pipeline
│   ├── requirements.txt
│   ├── parse_export.py       ← Phase 1: streaming parse → JSONL shards
│   ├── feature_engineer.py   ← Phase 2: feature extraction
│   ├── build_index.py        ← Phase 3: SQLite + embeddings index
│   └── report.py             ← Phase 5: telemetry reports
│
└── workspace/                ← gitignored; local working files only
    ├── shards/               ← JSONL conversation shards
    ├── features/             ← Parquet feature tables
    ├── index/                ← SQLite + embeddings
    ├── manifests/            ← uploadable shard manifests
    ├── reports/              ← generated reports (HTML/CSV)
    └── redacted/             ← redacted versions safe to upload
```

**`.gitignore` must exclude `workspace/`** — corpus data never commits.

---

## PHASE 0 — Ground Truth & Format Detection

### What a ChatGPT export contains

Verified against OpenAI's help docs and community reverse engineering (2023-2024):

```
export-<date>.zip
├── conversations.json       ← PRIMARY: array of conversation objects
├── user.json                ← account metadata
├── message_feedback.json    ← thumbs up/down on messages
├── model_comparisons.json   ← A/B test data (if any)
├── shared_conversations.json
└── dalle_generations/       ← image generation outputs (if any)
    └── *.webp / *.png
```

### Detection step

Run `Invoke-ExportDetect.ps1 -ZipPath <path>`. It outputs a structured detection report:

```json
{
  "zip_sha256": "...",
  "zip_size_bytes": 4080218931,
  "detected_files": ["conversations.json", "user.json", ...],
  "conversations_json_size_bytes": 3801000000,
  "format_version_guess": "2024-Q1",
  "warnings": []
}
```

Acceptance criteria: `conversations_json_size_bytes > 0`, no warnings.

### Canonical normalized record schemas

See `schemas/` directory. Summary:

| Entity | Key fields | ID pattern |
|--------|-----------|------------|
| Conversation | id, title, create_time, update_time, message_count, model | `conv_{sha8}_{epoch}` |
| Message | id, conv_id, role, content_type, text, token_est, create_time | `msg_{conv_sha8}_{idx}_{role3}` |
| Tool Event | id, msg_id, tool_name, input_summary, output_summary | `tool_{msg_id}_{seq}` |
| Attachment | id, msg_id, filename, mime_type, size_bytes, local_path | `att_{msg_id}_{seq}` |

---

## PHASE 1 — Local Ingestion & Deterministic Sharding

### Workflow

```
export.zip
    ↓  [Invoke-ExportDetect.ps1]  integrity check + structure map
    ↓  [parse_export.py]           streaming JSON parse (ijson)
    ↓  shard by conversation       deterministic, stable across re-runs
    ↓  workspace/shards/*.jsonl    one conversation per line
    ↓  [Invoke-ExportIngest.ps1]   produce manifests + upload artifacts
    ↓  workspace/manifests/        uploadable to LLM
```

### Sharding rules (determinism guaranteed)

1. Sort conversations by `create_time ASC`, then by `id` as tiebreaker.
2. Pack conversations into shards, target ≤ 8 MB uncompressed JSONL.
3. Never split a conversation across shards.
4. Shard filename: `shard_{shard_idx:04d}_{first_conv_date}_{last_conv_date}.jsonl`
5. Each shard has a companion `.sha256` file.

### Artifacts produced (uploadable)

| Artifact | Size estimate | Purpose |
|----------|--------------|---------|
| `manifests/global-manifest.json` | ~50 KB | All shard hashes, conversation index |
| `manifests/conv-index.jsonl` | ~5 MB | One line per conversation: id, title, date, message count, model |
| `features/feature-table.parquet` | ~20 MB | All computed features |
| `redacted/sample-shards/` | ~1 MB | 10 anonymized sample conversations |

### Validation gate

- SHA-256 of every shard matches manifest entry.
- `sum(messages across all shards) == original count in conversations.json`.
- No conversation appears in more than one shard.

---

## PHASE 2 — Feature Engineering (Telemetry Variables)

### Feature taxonomy

#### 2.1 Prompt attributes

| Feature | Type | Method |
|---------|------|--------|
| `prompt_token_est` | int | `len(text.split()) * 1.3` (GPT approximation) |
| `prompt_word_count` | int | Algorithmic |
| `has_system_instruction` | bool | Role == 'system' in mapping |
| `has_explicit_constraints` | bool | Regex: `"do not", "must", "only", "never"` |
| `has_numbered_steps` | bool | Regex: `^\d+[.)]\s` |
| `has_role_assignment` | bool | Regex: `"you are", "act as", "pretend"` |
| `question_count` | int | Count `?` at sentence boundaries |
| `specificity_score` | float | Unique nouns / total words (NLP) |
| `prompt_archetype` | enum | LLM-assisted: instruction/question/creative/code/chat |

#### 2.2 Complexity proxies

| Feature | Type | Method |
|---------|------|--------|
| `response_token_est` | int | Algorithmic |
| `code_block_count` | int | Count ` ``` ` pairs |
| `code_line_count` | int | Count lines inside code blocks |
| `tool_call_count` | int | Count tool-role messages in conversation |
| `multi_step_plan_detected` | bool | Regex: numbered list in response ≥ 3 items |
| `branching_depth` | int | Max depth in conversation mapping tree |
| `conversation_turn_count` | int | Count user+assistant pairs |
| `avg_response_length` | float | Mean assistant token_est |

#### 2.3 Emotional / interpersonal signals

| Feature | Type | Method | Caveat |
|---------|------|--------|--------|
| `prompt_sentiment` | float [-1,1] | VADER (local, fast) | Measures surface tone, not intent |
| `urgency_signal` | bool | Regex: `"urgent", "asap", "immediately", "critical"` | Low recall |
| `frustration_signal` | bool | Regex + sentiment threshold | High false positive rate; use as signal only |
| `gratitude_signal` | bool | Regex: `"thank", "great job", "perfect"` | Reliable |
| `conflict_signal` | bool | Negative sentiment + correction verbs | Use with caution |

**Measurement limit:** Local NLP (VADER, regex) is shallow. LLM-assisted labeling on a sample (200-500 conversations) yields much higher quality but must be explicitly requested and cited.

#### 2.4 Performance outcomes

| Feature | Type | Method |
|---------|------|--------|
| `rework_loop_count` | int | Consecutive user corrections after assistant response |
| `correction_phrases` | int | Regex: `"that's wrong", "not what I meant", "try again"` |
| `success_signal` | bool | LLM-assisted OR regex: `"perfect", "exactly", "works"` |
| `conversation_abandoned` | bool | Last message is user (no final assistant response) |
| `regression_count` | int | Re-asking a question from an earlier turn |
| `time_to_resolution` | float | Minutes from first user message to success_signal |

#### 2.5 Governance integrity

| Feature | Type | Method |
|---------|------|--------|
| `has_citations` | bool | Regex: URL patterns, `[1]`, footnote markers |
| `explicit_assumptions` | bool | Regex: `"assuming", "I'll assume"` |
| `fail_closed_language` | bool | Regex: `"I don't have", "I cannot", "I need more"` |
| `confidence_qualifier` | bool | Regex: `"I think", "likely", "approximately"` |

#### 2.6 Safety / policy friction

| Feature | Type | Method |
|---------|------|--------|
| `refusal_detected` | bool | Regex: `"I'm not able to", "I can't help with"` |
| `policy_boundary_hit` | bool | Regex: `"against my guidelines", "harmful content"` |
| `content_warning_present` | bool | Regex: `"I should note", "caution"` |

### Computation split

| Method | Features | Tool |
|--------|----------|------|
| Purely algorithmic | All token counts, code counts, turn counts, regex flags | `feature_engineer.py` |
| NLP library (local) | Sentiment, specificity_score | VADER + spaCy |
| LLM-assisted (on sample) | prompt_archetype, success_signal, rework intent | Upload redacted sample shard + feature table to LLM |

---

## PHASE 3 — Indexing & Retrieval ("Memory")

### Architecture

```
workspace/index/
├── memory.db              ← SQLite: all metadata, features, episodic objects
├── embeddings.bin         ← FAISS or ChromaDB: semantic vectors
├── episodic/              ← JSONL: compact citeable memory objects
│   └── episodic-{date}.jsonl
└── graph/
    └── graph.jsonl        ← edge list: entity → entity with relation type
```

### SQLite schema (key tables)

```sql
-- Core entities
CREATE TABLE conversations (
    conv_id TEXT PRIMARY KEY,     -- conv_{sha8}_{epoch}
    title TEXT,
    create_time INTEGER,          -- Unix epoch
    update_time INTEGER,
    model TEXT,
    turn_count INTEGER,
    shard_file TEXT,              -- provenance pointer
    shard_line INTEGER
);

CREATE TABLE messages (
    msg_id TEXT PRIMARY KEY,      -- msg_{conv_sha8}_{idx}_{role3}
    conv_id TEXT REFERENCES conversations(conv_id),
    role TEXT,                    -- user/assistant/tool/system
    content_type TEXT,
    text TEXT,
    token_est INTEGER,
    create_time INTEGER,
    shard_file TEXT,
    shard_line INTEGER
);

CREATE TABLE features (
    conv_id TEXT REFERENCES conversations(conv_id),
    -- all Phase 2 features as columns
    prompt_token_est INTEGER,
    code_block_count INTEGER,
    sentiment REAL,
    refusal_detected INTEGER,
    -- ... all other features
    computed_at INTEGER
);

CREATE TABLE episodic_memory (
    episode_id TEXT PRIMARY KEY,  -- ep_{sha8}_{epoch}
    title TEXT,
    summary TEXT,
    tags TEXT,                    -- JSON array
    source_conv_ids TEXT,         -- JSON array of conv_ids
    source_spans TEXT,            -- JSON array of {conv_id, turn_start, turn_end}
    created_at INTEGER,
    updated_at INTEGER,
    version INTEGER
);
```

### ID strategy (deterministic, stable)

- `conv_{sha256(conv.id)[:8]}_{int(create_time)}` — stable across re-ingest
- `msg_{sha256(conv.id)[:8]}_{message_index:04d}_{role[:3]}` — position-stable
- `ep_{sha256(summary_text)[:8]}_{created_at}` — content-addressed

### Citation / provenance rule

**Every episodic memory object and every LLM-generated insight MUST include:**
```json
{
  "source_spans": [
    {
      "conv_id": "conv_a3f8b2c1_1706745600",
      "shard_file": "shard_0042_2024-01-15_2024-01-31.jsonl",
      "turn_start": 3,
      "turn_end": 7,
      "quote": "first 120 chars of the relevant message..."
    }
  ]
}
```

If a claim cannot be grounded to a source span, it is marked `"grounded": false` and must not be treated as fact.

### Retrieval modes

| Mode | Tool | Query example |
|------|------|--------------|
| Keyword + filter | SQLite FTS5 | `SELECT * FROM messages_fts WHERE messages_fts MATCH 'authentication error'` |
| Semantic | FAISS/Chroma | Embed query → top-k nearest neighbors |
| Faceted | SQLite WHERE | `WHERE model='gpt-4' AND refusal_detected=1 AND create_time > epoch` |
| Graph traversal | SQLite self-join on graph table | Topic → related decisions → artifacts |
| Episode lookup | episodic_memory table | `SELECT * FROM episodic_memory WHERE tags LIKE '%powershell%'` |

### Minimum viable tools

| Tool | Purpose | Install |
|------|---------|---------|
| SQLite (built-in) | Metadata, features, FTS | Included in Python |
| DuckDB | Analytical queries on parquet | `pip install duckdb` |
| sentence-transformers | Local CPU embeddings | `pip install sentence-transformers` |
| FAISS-cpu | Vector search | `pip install faiss-cpu` |
| VADER | Sentiment | `pip install vaderSentiment` |
| ijson | Streaming JSON parse | `pip install ijson` |

---

## PHASE 4 — LLM-in-the-Loop Analysis Workflow

### What to upload to the LLM (never the full corpus)

```
Upload per session (total < 5 MB):
├── manifests/global-manifest.json      ← orientation
├── manifests/conv-index.jsonl           ← conversation list
├── features/feature-table.parquet       ← all computed features
├── redacted/sample-shards/shard_NNN.jsonl  ← representative sample
└── [optional] specific conv JSONL by ID  ← when asking about a specific conversation
```

### LLM analysis rules

1. **Retrieve first.** Before answering any question about the corpus, query the index or identify the relevant shard.
2. **Cite always.** Every claim must reference a `conv_id` and `turn_start:turn_end`.
3. **Fail-closed.** If the relevant shard or feature data is not in the uploaded artifacts, respond: *"Required artifact not present. Upload [specific file] to proceed."*
4. **No interpolation.** Do not infer content that isn't in the provided artifacts.
5. **Structured output.** All analysis outputs are JSON or Markdown tables, not prose summaries.

### Question-answering over memory (retrieval loop)

```
User question
    ↓
1. Parse question → extract entities, time range, feature filters
2. Query SQLite for matching conv_ids
3. Check: are those conv shards uploaded? If not → STOP, request upload
4. Retrieve message spans from shard JSONL
5. Formulate answer WITH citations (conv_id + turn range + quote)
6. Write episodic_memory object if the answer reveals a durable insight
7. Return answer + citations + new episode ID
```

### Structured output formats

```json
{
  "analysis_type": "refusal_rate_by_model",
  "generated_at": "2026-02-26T00:00:00Z",
  "artifact_sources": ["feature-table.parquet"],
  "findings": [...],
  "citations": [...],
  "grounded": true,
  "unsupported_claims": []
}
```

---

## PHASE 5 — Reporting & Dashboards

### Dashboard 1: Reliability score over time

**Definition:** `reliability_score = 1 - (refusal_count + rework_loop_count + abandoned_count) / total_conversations`

```sql
SELECT
    strftime('%Y-%W', datetime(create_time, 'unixepoch')) AS week,
    COUNT(*) AS conv_count,
    AVG(1.0 - CAST(refusal_detected + conversation_abandoned AS REAL) / turn_count) AS reliability_score
FROM conversations c JOIN features f USING (conv_id)
GROUP BY week ORDER BY week;
```

### Dashboard 2: Prompt archetype performance

```sql
SELECT
    f.prompt_archetype,
    COUNT(*) AS n,
    AVG(f.rework_loop_count) AS avg_rework,
    AVG(f.time_to_resolution) AS avg_resolution_min,
    SUM(f.success_signal) AS successes
FROM features f
GROUP BY f.prompt_archetype
ORDER BY avg_rework ASC;
```

### Dashboard 3: Regression hotspots

```sql
SELECT
    c.title,
    c.conv_id,
    f.regression_count,
    f.rework_loop_count,
    f.conversation_abandoned
FROM features f JOIN conversations c USING (conv_id)
WHERE f.regression_count > 2 OR f.rework_loop_count > 3
ORDER BY f.regression_count DESC LIMIT 50;
```

### Dashboard 4: Tool-usage effectiveness

```sql
SELECT
    f.tool_call_count > 0 AS used_tools,
    AVG(f.rework_loop_count) AS avg_rework,
    AVG(f.time_to_resolution) AS avg_resolution_min,
    COUNT(*) AS n
FROM features f
GROUP BY used_tools;
```

### Dashboard 5: Emotional state vs. productivity

```sql
SELECT
    CASE
        WHEN f.prompt_sentiment < -0.3 THEN 'negative'
        WHEN f.prompt_sentiment > 0.3 THEN 'positive'
        ELSE 'neutral'
    END AS sentiment_bucket,
    AVG(f.rework_loop_count) AS avg_rework,
    AVG(f.time_to_resolution) AS avg_resolution_min,
    COUNT(*) AS n
FROM features f
GROUP BY sentiment_bucket;
```

**Caution:** Correlation ≠ causation. Frustration may follow failure rather than cause it. Do not use these numbers for decisions without manual spot-check.

### Telemetry schema (feature-table.parquet)

```
conv_id                 STRING
create_time             INT64   (unix epoch)
model                   STRING
turn_count              INT32
prompt_token_est        INT32
response_token_est      INT32
code_block_count        INT32
tool_call_count         INT32
has_system_instruction  BOOL
has_explicit_constraints BOOL
prompt_archetype        STRING  (LLM-labeled on sample)
prompt_sentiment        FLOAT32
urgency_signal          BOOL
frustration_signal      BOOL
gratitude_signal        BOOL
rework_loop_count       INT32
correction_count        INT32
success_signal          BOOL
conversation_abandoned  BOOL
regression_count        INT32
time_to_resolution      FLOAT32 (minutes; null if no success signal)
has_citations           BOOL
refusal_detected        BOOL
policy_boundary_hit     BOOL
```

---

## PHASE 6 — Execution Kit

### Minimal viable path ("First 60 minutes")

```
Step 1  [5 min]   pwsh scripts/Invoke-ExportDetect.ps1 -ZipPath .\export.zip
                   → Produces: detection-report.json
                   → Validates: format, files present

Step 2  [10 min]  python python/parse_export.py --zip .\export.zip --out workspace/
                   → Produces: workspace/shards/*.jsonl, workspace/manifests/conv-index.jsonl
                   → Validates: message count checksum

Step 3  [5 min]   python python/feature_engineer.py --shards workspace/shards/ --out workspace/features/
                   → Produces: workspace/features/feature-table.parquet
                   → No LLM needed for this step

Step 4  [5 min]   python python/build_index.py --shards workspace/shards/ --features workspace/features/
                   → Produces: workspace/index/memory.db

Step 5  [35 min]  Upload to LLM:
                   - workspace/manifests/global-manifest.json
                   - workspace/manifests/conv-index.jsonl
                   - workspace/features/feature-table.parquet
                   → Ask: "Generate Dashboard 1-5 from these artifacts"
```

### Enterprise-grade additions

- Replace FAISS with a managed vector DB (Qdrant local, Weaviate local).
- Add spaCy NER for entity extraction (people, projects, orgs).
- Add LLM-assisted labeling loop: sample 500 conversations, label archetypes, train a local classifier.
- Add scheduled re-ingestion: new exports delta-merge with `prev_sha256` chain.
- Add DuckDB for analytical workloads over parquet (faster than SQLite for aggregations).
- Expose a local REST API (FastAPI) for the retrieval layer.

### Redaction strategy

Before uploading any artifact:
1. Run `Invoke-Redact.ps1 -InputPath <file> -OutputPath <redacted-file>`
2. Patterns in `config/redaction-patterns.json` cover: email, phone, SSN, credit card, IP address, proper names (configurable).
3. Replacement token: `[REDACTED_{type}_{sequence}]` — preserves token count, maintains readability.
4. Redaction map is saved locally (never uploaded) for reverse lookup.

### Incremental update strategy

On each new export:
1. Run `Invoke-ExportDetect.ps1` on new zip → get new manifest.
2. Compare `conv_id` set against `workspace/manifests/global-manifest.json`.
3. Only process new/updated conversations (delta shards).
4. Append new ledger entry with delta shard hashes.
5. Re-run `feature_engineer.py --delta` on new shards only.
6. Merge into `memory.db` without touching existing rows.

### What to upload to the LLM — checklist

```
✅ workspace/manifests/global-manifest.json    (~50 KB)
✅ workspace/manifests/conv-index.jsonl         (~5 MB)
✅ workspace/features/feature-table.parquet     (~20 MB)
✅ workspace/redacted/sample-shards/*.jsonl     (~1 MB, 10 conversations)
✅ [on demand] specific conv JSONL by conv_id
❌ NEVER upload: workspace/shards/ (full corpus)
❌ NEVER upload: workspace/index/ (contains raw message text)
❌ NEVER upload: anything without running Invoke-Redact.ps1 first
```

---

## Proposed Additional Metrics (prioritized by ROI)

| Priority | Metric | Value | Effort |
|----------|--------|-------|--------|
| P0 | Prompt archetype (LLM-labeled) | Highest: drives all archetype dashboards | Medium |
| P0 | Rework loop count | Direct productivity signal | Low |
| P1 | Model version per conversation | Enables before/after GPT-4 comparisons | Low |
| P1 | Time-to-resolution | Real productivity measure | Low |
| P1 | Topic clustering (BERTopic) | Reveals project/domain breakdown | Medium |
| P2 | Semantic drift within conversation | Measures context loss | High |
| P2 | Instruction adherence score | Measures how well LLM followed constraints | High |
| P3 | Cross-conversation topic chains | Episodic memory quality | High |
| P3 | Knowledge decay detection | Spots when LLM forgot prior context | Very high |
