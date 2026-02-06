# CLAUDE.md - AI Assistant Guide for metablooms-ltm

## Project Overview

MetaBlooms LTM (Long-Term Memory) is a **source-of-truth, append-only** long-term memory store for the MetaBlooms AI system. It is a **data repository**, not a traditional software project. Clients fetch manifests via raw GitHub URLs and ingest only hash-verified payloads.

### Core Invariants (fail-closed)

- `ledger/ledger.ndjson` is **append-only** — never overwrite or delete existing lines
- All payloads (snapshots, deltas) must be **SHA-256 hash-verified** before ingestion
- `manifests/latest.json` is the rolling pointer to the current approved state
- Missing or mismatched hashes cause **rejection** (fail-closed design)

## Repository Layout

```
manifests/
  bootstrap.json        # Immutable first-run pointers (schema v1.0)
  latest.json           # Mutable rolling pointer to current snapshot + deltas
  ledger.ndjson         # Manifest change history (95 entries)
  smoke_test.json       # Smoke test manifest
ledger/
  ledger.ndjson         # Main append-only event log (NDJSON)
schemas/
  manifest.bootstrap.schema.json
  manifest.latest.schema.json
  ledger.event.schema.json
snapshots/
  snapshot_0001.json    # Baseline memory snapshot
deltas/2025-12/         # Delta artifacts (~95 files, JSON + MD)
scripts/
  validate_ltm.py       # Python 3.11 fail-closed validator
examples/
  ledger_event_example.json
repo_scaffold/          # Template for new LTM repos
.github/workflows/
  ltm_validate.yml      # CI validation on push to main / PRs
```

## Validation & CI

### Running validation locally

```bash
pip install jsonschema
python scripts/validate_ltm.py
```

Success output: `OK: MetaBlooms LTM validation passed.`
Failure exits with code 1 and prints `FAIL: <message>` to stderr.

### What the validator checks

1. All 6 required files exist (`manifests/bootstrap.json`, `manifests/latest.json`, `ledger/ledger.ndjson`, and the 3 schema files)
2. `bootstrap.json` validates against `schemas/manifest.bootstrap.schema.json`
3. `latest.json` validates against `schemas/manifest.latest.schema.json`
4. If state type is `"snapshot"`: referenced file exists and SHA-256 matches
5. Each delta entry: referenced file exists and SHA-256 matches
6. `ledger/ledger.ndjson` contains valid JSON on every non-empty line

### CI pipeline

GitHub Actions (`.github/workflows/ltm_validate.yml`) runs on push to `main` and all PRs. It uses Python 3.11 + `jsonschema`.

## Key Conventions

### Data formats

- **NDJSON**: One JSON object per line for ledger files
- **MIPS** (Metadata-Integrated Payload Structure): Delta artifacts use this envelope format with `MIPS` metadata header and `body` payload
- **Timestamps**: ISO-8601 UTC (e.g., `2025-12-30T19:45:37Z`)
- **Hashes**: SHA-256, 64-character lowercase hex strings

### File naming

Delta files follow: `YYYY-MM-DD_MetaBlooms_<TYPE>_<Description>_vN.mips.<ext>`

Slot prefixes for mobile UX filename frontloading:
- `MB__00` — Active State / Sentinel
- `MB__01` — Active CorePack
- `MB__03` — External Intel / inputs
- `MB__90` — Archives / optional bundles
- `MB__99` — Indexes

### Branching strategy

- `main` — production, validated by CI
- `staging` — trial runs, promote to `main` via PR once validated

### Commit message convention

Delta ingestion commits use: `ingest: <delta_filename>`

## Making Changes

### Adding a new delta

1. Place the delta file in `deltas/YYYY-MM/` following the naming convention
2. Compute its SHA-256: `sha256sum deltas/YYYY-MM/your_file.mips.json`
3. If the delta should be active, add an entry to `manifests/latest.json` under `"deltas"` with `path` and `sha256`
4. Append a ledger entry to `manifests/ledger.ndjson` recording the change
5. Run `python scripts/validate_ltm.py` to verify

### Updating the snapshot

1. Place the new snapshot in `snapshots/`
2. Update `manifests/latest.json` — set `state.snapshot_path` and `state.snapshot_sha256`
3. Run the validator

### Modifying schemas

Schemas use JSON Schema Draft 2020-12. After changes, run the validator to confirm manifests still conform.

## Important Warnings

- **Never** delete or reorder lines in `ledger/ledger.ndjson` — append only
- **Never** reference a file in `latest.json` without a valid SHA-256 — the validator will reject it
- **Always** run `python scripts/validate_ltm.py` before pushing — CI will catch failures but local validation saves time
- The validator does **not** enforce append-only across git history; it only validates current repo contents
