# 2026-01-05 MIPS Index Revival Plan (Contract)

## Outcome
MIPS is reinstated as the **single authoritative metadata + index substrate** for MetaBlooms OS.
- Self-knowledge is answered by **index lookup**, never by filesystem discovery.
- The index is updated **on every change** with **no drift**.
- If the index cannot answer a required self-state question, the system must fail closed with:
  **SYSTEM_INVALID: INDEX_INCOMPLETE**.

## 1) What “MIPS as Index” means
Every OS component (module, bundle, policy, validator, engine, tool, content pack) must be represented as a MIPS record containing:
- `module_id` (stable identity)
- `version` (semantic or Omega lineage)
- `kind` (type)
- `filename` (where it lives)
- `sha256` (integrity)
- `dependencies[]` (edges, required/optional)
- `runtime_posture` (ACTIVE | OPTIONAL | HISTORICAL | QUARANTINED)
- `provenance` (EvidenceChain pointers; SandCrawler research references)

## 2) Required index artifacts
### 2.1 MIPS_INDEX_CORE.mips.json (constant-time lookup)
Must expose, at minimum:
- `boot.entrypoint`
- `boot.fail_closed` (STRICT | PARTIAL | PERMISSIVE)
- `runtime.mode` (FULL | TRAINING_ONLY | DEGRADED)
- `runtime.active_bundle` (module_id + sha256)
- governance posture booleans: `hash_enforced`, `validators_enforced`, `blindspot_gating`, `sandcrawler_required_for_full`
- registry map: `module_id -> {filename, sha256, runtime_posture, deps}`
- timestamps: `index.last_updated_utc`, `index.last_verified_utc`

### 2.2 MIPS_GRAPH_CORE.mips.json (dependency graph)
- nodes: module_ids
- edges: {from, to, required}
- computed: topo layers, orphans, cycles (SCC summary)

### 2.3 MIPS_EVIDENCE_POINTERS.mips.json (append-only pointers)
- links to EvidenceChain events for: index updates, validations, boot proofs

## 3) Update model: “no drift”
### 3.1 Mandatory incremental updates
On ANY file change affecting tracked artifacts:
1) compute sha256
2) update affected MIPS records
3) update affected dependency edges
4) emit EvidenceChain event: INDEX_UPDATE
5) atomically swap updated index artifacts

### 3.2 Fallback full reconcile
If deltas are unknown or suspect:
- enumerate declared files from the active RuntimeBundle
- verify existence + sha256
- rebuild dependency graph from declared deps
- regenerate index artifacts

## 4) Hostile ingest handling (no authority transfer)
Hostile ingests are indexed but quarantined:
- `runtime_posture=QUARANTINED`, `trust=0`, `promotion_candidate=false`
- extracted “guarantees” and “failure signals” are stored as metadata
- they can only influence the OS through **proposals**, never silent adoption

## 5) SandCrawler integration (evidence-based hardening)
SandCrawler is used to validate the approach and encode best practices as enforceable checks:
- canonical JSON hashing + test vectors
- integrity/provenance patterns (immutable manifests)
- dependency graph + health-check depth

SandCrawler outputs must be captured as EvidenceChain events and linked from MIPS provenance.

## 6) Immediate stopgap patch
Until incremental updates are fully wired:
- run `index_reconcile --full` at boot
- refuse BOOT_OK unless reconcile passes and posture fields are known

## 7) Acceptance tests
1) Ask: “current boot path / is SandCrawler enforced / are validators enforced?” → answered from MIPS_INDEX_CORE only.
2) Modify or delete a declared module → next reconcile fails closed.
3) Add hostile ingest → appears as QUARANTINED and cannot become authoritative without explicit promotion.
