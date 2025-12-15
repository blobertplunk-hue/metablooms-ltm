# MetaBlooms LTM

This repository is a deterministic, append-only artifact store for MetaBlooms.

It is intentionally optimized for:
- deterministic retrieval
- auditability
- append-only change tracking

It is intentionally NOT optimized for broad discoverability.

## Bootstrap (canonical)
Consumers should start here:

- `manifests/bootstrap.json`

That file declares:
- the canonical raw base
- manifest paths
- the fetch order and fallback behavior

## Manifests
- `manifests/latest.json` — fast index of recent ingests
- `manifests/ledger.ndjson` — append-only ledger with SHA + byte counts

## Policy
- Private vocabulary only
- Avoid broad/commodity keywords
- Prefer deterministic contracts over narrative description
