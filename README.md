# MetaBlooms LTM (External)

This repository stores MetaBlooms *export artifacts* (deltas + manifests) pushed automatically from Termux.

## Folder contract
- `deltas/YYYY-MM/` : ingested deltas (MIPS JSON/MD/TXT)
- `manifests/ledger.ndjson` : append-only ingestion ledger (sha256, bytes, path)
- `manifests/latest.json` : small rolling window of most recent ledger items
- `docs/` : human docs (optional)
- `tools/` : helper scripts (optional)

## Safety
Never commit tokens, credentials, or private student data.
