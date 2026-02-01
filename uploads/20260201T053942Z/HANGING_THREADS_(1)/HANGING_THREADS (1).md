# Hanging Threads (Ship-Ready Notes)

## 1) Chat index update for this chat (PENDING)
- This chat's full transcript has **not** been harvested into the canonical chat index store.
- MODE_A automated harvester is still required to capture assistant/user turns at scale (no manual copy/paste).
- Until harvested `assistant_responses.ndjson` / conversation NDJSON exists, full-transcript linting remains deferred.

## 2) MODE_B active: prompt-only linting (DEFERRED FULL TRANSCRIPT)
- Current enforcement is limited to linting the **NEW FULL PROMPT** blocks.
- `FULL_TRANSCRIPT_LINT_DEFERRED=true` must remain set until MODE_A NDJSON capture exists.

## 3) Export pipeline hardening (RECOMMENDED)
- Add deterministic zip building (normalized mtimes/ordering) to reduce diff noise between exports.
- Add automated contamination test: prove no chat-index paths appear in MAIN_OS_BUNDLE inventory.

## 4) Ledger coverage gap
- `chat_ledger.ndjson` includes only the governed subset of turns recorded since ledgering was enabled.
- A post-session ingestion pass should reconcile full chat history into the index.
