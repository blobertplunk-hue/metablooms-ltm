MIPS_HEADER:
  artifact_id: MB__TERMUX_WATCHER_FIXPACK__ONEPASTE__2025-12-14_v1
  parent_bundle: MB__LOOP_MVP_LTM_PIPELINE__2025-12-14_v1
  version: v1
  councils: [Auditor, Fixer, Recorder]
  sha256: b3092cc81009c700e1628df51a0d178f55201df28677de8617a062ffa41de84d
  timestamp_utc: 2025-12-14T20:26:07Z
  content_type: text/markdown
BODY:

# One‑paste fixpack: make the self‑test valid and non‑ambiguous

## Why your “FAIL not moved” happened (and why it was my fault)
- The v2 self-test used an **invalid delta payload** (`{"selftest":true}`) that many `is_delta` filters will rightly reject.
- The v2 self-test also used `/tmp/...` for stderr capture; Termux typically does **not** provide `/tmp` by default, so the “manual mv failed” conclusion was **not valid evidence**.

## What this fixpack does
1) Forces exactly **one** watcher instance.
2) Drops a **minimal MIPS‑shaped delta** that should pass most `is_delta` checks.
3) Uses a **real Termux path** for temp (`$HOME/tmp`).
4) Produces a single PASS/FAIL outcome with the exact log tail.

## Copy/paste (single block)
```bash
mkdir -p ~/bin ~/log ~/tmp /sdcard/Download/MB_INTAKE

cat > ~/bin/mb_watch_selftest_v3.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

WATCH="$HOME/bin/mb_watch_daemon.sh"
WATCH_LOG="$HOME/log/mb_watch.log"
REPO="$HOME/metablooms-ltm"

INTAKE="/sdcard/Download/MB_INTAKE"
TEST="/sdcard/Download/MB__03_DELTA__SELFTEST_v3.mips.json"
ERR="$HOME/tmp/mb_mv_err.txt"

say(){ echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }

say "== selftest_v3 starting =="

# One watcher only
pkill -f mb_watch_daemon.sh 2>/dev/null || true
sleep 1

# Show watcher config
say "-- watcher dir config --"
grep -nE '^(WATCH_DIR|INTAKE_DIR)=' "$WATCH" || true

# Write a minimal VALID delta (MIPS_HEADER + DELTA)
rm -f "$TEST" "$INTAKE/$(basename "$TEST")" 2>/dev/null || true
cat > "$TEST" <<'JSON'
{
  "MIPS_HEADER": {
    "artifact_id": "MB__03_DELTA__SELFTEST_v3",
    "version": "v1",
    "timestamp_utc": "2025-12-15T00:00:00Z",
    "content_type": "application/json",
    "sha256": "selftest"
  },
  "DELTA": {
    "id": "selftest_v3",
    "status": "STAGED",
    "summary": "Self-test delta for watcher move+process",
    "changes": []
  }
}
JSON

say "[OK] wrote test delta: $TEST"
ls -la "$TEST" || true

# Start watcher clean
: > "$WATCH_LOG"
nohup "$WATCH" >> "$WATCH_LOG" 2>&1 &
sleep 2

# Wait for move
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if [ -e "$INTAKE/$(basename "$TEST")" ]; then
    say "[PASS] moved into MB_INTAKE on second $i"
    break
  fi
  sleep 1
done

# If not moved, manual mv test (valid temp path)
if [ ! -e "$INTAKE/$(basename "$TEST")" ]; then
  say "[FAIL] watcher did NOT move delta"
  : > "$ERR"
  if mv "$TEST" "$INTAKE/" 2>>"$ERR"; then
    say "[DIAG] manual mv succeeded -> watcher is skipping file (is_delta or move-shim not reached)"
  else
    say "[DIAG] manual mv FAILED -> storage permission/SAF issue is real"
    cat "$ERR" || true
  fi
  say "-- tail watcher log --"
  tail -n 200 "$WATCH_LOG" || true
  exit 1
fi

# Repo evidence (best effort)
say "-- repo status --"
cd "$REPO" 2>/dev/null || true
git log -n 5 --oneline 2>/dev/null || true
git status 2>/dev/null || true

say "-- tail watcher log --"
tail -n 200 "$WATCH_LOG" || true
say "== selftest_v3 done =="
EOF

chmod +x ~/bin/mb_watch_selftest_v3.sh
bash ~/bin/mb_watch_selftest_v3.sh
```

## Interpreting results
- **PASS moved into MB_INTAKE** → watcher routing is working; earlier “FAIL not moved” was test design error.
- **FAIL + manual mv succeeds** → watcher is skipping file (update `is_delta` rules or insert move-shim where your script actually processes files).
- **FAIL + manual mv fails** → Android storage permission/SAF is blocking moves; switch to a copy+delete fallback.

