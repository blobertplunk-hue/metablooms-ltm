# MetaBlooms LTM CI Pack (GitHub Actions)

## What this adds
- A GitHub Actions workflow that validates your LTM repo on push/PR.
- A Python validator that enforces:
  - required files exist
  - manifests validate against schemas
  - snapshot/delta referenced files exist and sha256 matches
  - ledger is valid NDJSON

## Install (one step)
Upload these paths into your GitHub repo root:
- `.github/workflows/ltm_validate.yml`
- `scripts/validate_ltm.py`

Commit to `main`.

## Success check
Go to the **Actions** tab and confirm the workflow **MetaBlooms LTM Validate** runs and passes.
