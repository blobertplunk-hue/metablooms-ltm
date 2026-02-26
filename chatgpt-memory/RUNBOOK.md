# ChatGPT Memory Pipeline — Operator Runbook

Step-by-step instructions for a Windows 11 operator. Run all commands from the repo root.

---

## Prerequisites

```powershell
# Verify PowerShell 7.4+
pwsh --version

# Verify Python 3.11+
python --version

# Install Python dependencies
pip install -r chatgpt-memory/python/requirements.txt

# Install git hooks (one-time)
bash .githooks/setup.sh
```

---

## First-Time Setup

```powershell
# Create workspace directories (gitignored — corpus stays local)
New-Item -ItemType Directory -Path workspace\shards, workspace\features, workspace\index, workspace\manifests, workspace\reports, workspace\redacted -Force
```

Add to `.gitignore` if not already present:
```
workspace/
```

---

## PHASE 0 — Detect export structure

**Input:** `C:\exports\export.zip` (your ChatGPT export)
**Output:** `workspace\manifests\detection-report.json`

```powershell
pwsh chatgpt-memory\scripts\Invoke-ExportDetect.ps1 `
    -ZipPath C:\exports\export.zip `
    -OutputPath workspace\manifests\
```

**Gate:** Script exits 0 on pass, 1 on fail. Fix any warnings before proceeding.

---

## PHASE 1 — Parse and shard

**Input:** Export zip
**Output:** `workspace\shards\*.jsonl`, `workspace\manifests\conv-index.jsonl`, `workspace\manifests\python-manifest.json`

```powershell
python chatgpt-memory\python\parse_export.py `
    --zip C:\exports\export.zip `
    --out workspace\
```

Expected runtime: 5–20 minutes depending on corpus size and disk speed.

Then validate shards and produce the uploadable global manifest:

```powershell
pwsh chatgpt-memory\scripts\Invoke-ExportIngest.ps1 `
    -WorkspaceRoot workspace\ `
    -DetectionReportPath workspace\manifests\detection-report.json
```

**Gate:** All shard SHA-256 must match. Total message count must match.

---

## PHASE 2 — Feature engineering

**Input:** `workspace\shards\*.jsonl`
**Output:** `workspace\features\feature-table.parquet`

```powershell
python chatgpt-memory\python\feature_engineer.py `
    --shards workspace\shards\ `
    --out workspace\features\
```

Expected runtime: 10–40 minutes.

---

## PHASE 3 — Build memory index

**Input:** Shards + feature table
**Output:** `workspace\index\memory.db`

```powershell
python chatgpt-memory\python\build_index.py `
    --shards workspace\shards\ `
    --features workspace\features\ `
    --db workspace\index\memory.db
```

---

## PHASE 5 — Generate reports

**Input:** `workspace\index\memory.db`
**Output:** `workspace\reports\*.csv` + `*.json`

```powershell
python chatgpt-memory\python\report.py `
    --db workspace\index\memory.db `
    --out workspace\reports\
```

---

## Redact before uploading (ALWAYS run this)

```powershell
# Redact conv-index before upload
pwsh chatgpt-memory\scripts\Invoke-Redact.ps1 `
    -InputPath workspace\manifests\conv-index.jsonl `
    -OutputPath workspace\redacted\conv-index-clean.jsonl

# Redact a specific shard for sample review
pwsh chatgpt-memory\scripts\Invoke-Redact.ps1 `
    -InputPath workspace\shards\shard_0001_2024-01-01_2024-01-31.jsonl `
    -OutputPath workspace\redacted\shard_0001-clean.jsonl
```

---

## What to upload to the LLM (after redaction)

```
workspace\manifests\global-manifest.json           ← always
workspace\redacted\conv-index-clean.jsonl          ← always
workspace\features\feature-table.parquet           ← always (no raw text)
workspace\reports\*.json                           ← always (aggregated only)
workspace\redacted\shard_NNNN-clean.jsonl          ← on demand per conversation
```

**Never upload:**
- `workspace\shards\` (raw corpus)
- `workspace\index\memory.db` (contains raw message text)
- `workspace\redaction-map.json` (reverse-lookup of redacted values)

---

## Incremental update (new export)

1. Run Phase 0 on the new zip.
2. Compare new `conv-index.jsonl` against existing `global-manifest.json` to find new conv_ids.
3. Run `parse_export.py --zip new.zip --out workspace-delta\` on the new zip.
4. Merge delta shards into the main index:
   ```powershell
   python chatgpt-memory\python\build_index.py `
       --shards workspace-delta\shards\ `
       --features workspace-delta\features\ `
       --db workspace\index\memory.db
   ```
   (The `INSERT OR REPLACE` strategy prevents duplicates.)

---

## Validation queries

```sql
-- Row counts
SELECT 'conversations' AS tbl, COUNT(*) FROM conversations
UNION ALL SELECT 'messages', COUNT(*) FROM messages
UNION ALL SELECT 'features', COUNT(*) FROM features;

-- Model breakdown
SELECT model, COUNT(*) FROM conversations GROUP BY model ORDER BY 2 DESC;

-- Refusal rate
SELECT
    ROUND(100.0 * SUM(refusal_detected) / COUNT(*), 2) AS refusal_rate_pct
FROM features;

-- FTS test
SELECT conv_id, role, substr(text, 1, 200)
FROM messages_fts
WHERE messages_fts MATCH 'PowerShell'
LIMIT 5;
```

Run with: `sqlite3 workspace\index\memory.db`
