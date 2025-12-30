# metabloom-ltm (MetaBlooms Long-Term Memory Repo)

This repository is a **source-of-truth, append-only** long-term memory store for MetaBlooms.

## Core contract (fail-closed)
- MetaBlooms reads **manifests** from GitHub (raw) and ingests only **hash-verified** payloads.
- The repo is **append-only** for `ledger/ledger.ndjson`.
- `manifests/latest.json` points to the most recent approved snapshot and/or delta packs.

## Repository layout
- `manifests/bootstrap.json` : minimal bootstrap pointers used by the OS at first-run
- `manifests/latest.json`    : rolling pointer to the current approved state
- `ledger/ledger.ndjson`     : append-only event log (one JSON object per line)
- `schemas/*.json`           : JSON Schemas for manifests + ledger events
- `examples/`                : example entries and test vectors

## Branching
Use `main` for production. Use `staging` for trial runs; promote to `main` by PR once validated.

## Raw URLs
MetaBlooms should fetch via:
`https://raw.githubusercontent.com/<OWNER>/metabloom-ltm/<BRANCH>/manifests/bootstrap.json`

If the repo is private, prefer the GitHub REST API contents endpoint with an auth token rather than raw.
