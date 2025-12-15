<!--MIPS_HEADER
{
  "artifact_id": "MB__DOC__README_MetaBloomsLTM_v1",
  "parent_bundle": null,
  "version": "v1",
  "timestamp_utc": "2025-12-15T00:52:30Z",
  "councils": [
    "Facilitator",
    "Auditor",
    "Archivist",
    "Synthesizer"
  ],
  "sha256": "e4ea18b267132e0ba3c41bc4ec29d2cf29de944aad24539dccc7ac555d7dc54b",
  "content_type": "text/markdown",
  "links": [],
  "evidence_chain": []
}
MIPS_HEADER-->

# MetaBlooms LTM Bootstrap (Public, Low-Discovery)

This repository is the canonical store for **MetaBlooms** immutable artifacts:
- **MIPS**-wrapped deltas (append-only)
- Deterministic **manifests** for cold-start bootstrapping
- SHA-based deduplication and auditability

Design intent: **machine addressability** for MetaBlooms components with **human obscurity by default**.

## Canonical Raw Fetch URLs

Raw base:
- https://raw.githubusercontent.com/blobertplunk-hue/metablooms-ltm/main

Primary fetch targets:
- https://raw.githubusercontent.com/blobertplunk-hue/metablooms-ltm/main/manifests/bootstrap.json
- https://raw.githubusercontent.com/blobertplunk-hue/metablooms-ltm/main/manifests/latest.json
- https://raw.githubusercontent.com/blobertplunk-hue/metablooms-ltm/main/manifests/ledger.ndjson

## Manifests

- `manifests/bootstrap.json` — discovery bootstrap (repo + raw_base + canonical paths)
- `manifests/latest.json` — fast “what’s newest” index for consumers
- `manifests/ledger.ndjson` — append-only ingest ledger (authoritative audit trail)

## Delta Layout

- `deltas/YYYY-MM/*.mips.*` — immutable, append-only artifacts grouped by month

## Operational Notes

- This repo is optimized for **MetaBlooms-specific lexicon** and deterministic paths.
- Avoid broad, commodity discovery keywords in README/metadata by design.
- Consumers should resolve: `bootstrap.json` → `latest.json` → `ledger.ndjson` and validate JSON parsing.

## Quick Verify

```bash
curl -s https://raw.githubusercontent.com/blobertplunk-hue/metablooms-ltm/main/manifests/bootstrap.json | head
```
