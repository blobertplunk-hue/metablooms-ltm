MIPS_HEADER:
  artifact_id: MB__PATCH__WATCHER_ISDELTA_RECOGNIZER__2025-12-14_v1
  parent_bundle: MB__LOOP_MVP_LTM_PIPELINE__2025-12-14_v1
  version: v1
  councils: [Auditor, Fixer, Recorder]
  sha256: 1a639d0d6526aa52f279210a4a22d706a4745d13f69d9539eb027ab21213372f
  timestamp_utc: 2025-12-14T20:28:28Z
  content_type: text/markdown
BODY:

# Fix: watcher is skipping real deltas (is_delta too strict or not matching)

## What your selftest_v3 proved (conclusive)
- `mv` from `/sdcard/Download` -> `/sdcard/Download/MB_INTAKE` **works**.
- Watcher did **not** move the file.
- Therefore: watcher is **skipping** the candidate before the move step.
  The most likely gate is `is_delta`.

## Patch strategy
Replace `is_delta()` with a recognizer that matches your actual operational reality:
- Only considers filenames that look like deltas: `MB__*` or `*__DELTA__*`
- Only considers delta-like extensions: `*.mips.json|*.json|*.mips.md|*.mips.txt`
- Requires quick content markers in first 16KB: `MIPS_HEADER` or `DELTA`
This is strict enough to avoid touching normal downloads, while not rejecting your own deltas.

Also adds log line:
- `[SKIP] not delta: <file>` for delta-looking files that fail recognition

## Apply patch (one paste)
```bash
cat > ~/bin/mb_patch_watch_isdelta.sh <<'EOF'
\
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SRC="$HOME/bin/mb_watch_daemon.sh"
BK="$HOME/bin/mb_watch_daemon.sh.bak.isdelta.$(date -u +%Y%m%dT%H%M%SZ)"

if [ ! -f "$SRC" ]; then
  echo "[FAIL] watcher not found at $SRC"
  exit 1
fi

cp "$SRC" "$BK"
echo "[OK] backup -> $BK"

# Replace (or add) a robust is_delta() that matches YOUR actual workflow:
# - You download MB__* deltas to /sdcard/Download
# - We only treat files as deltas if:
#   a) filename matches MB__* or contains __DELTA__
#   b) and file content contains "MIPS_HEADER" OR "DELTA" (within first 16KB)
# This prevents the earlier skip where your test delta was not recognized.

perl -0777 -i -pe '
  if (s/is_delta\(\)\s*\{.*?\n\}\n/is_delta() {\n  local f=\"$1\"\n  local base\n  base=\"$(basename \"$f\")\"\n\n  # Fast filename gate\n  case \"$base\" in\n    MB__*|*__DELTA__*|*_DELTA_*) ;; \n    *) return 1 ;; \n  esac\n\n  # Extension gate (keep narrow)\n  case \"$base\" in\n    *.mips.json|*.json|*.mips.md|*.mips.txt) ;;\n    *) return 1 ;;\n  esac\n\n  # Content gate: look for markers quickly (first 16KB)\n  if head -c 16384 \"$f\" 2>/dev/null | grep -qE \"MIPS_HEADER|\\\"MIPS_HEADER\\\"|\\\"DELTA\\\"|\\bDELTA\\b\"; then\n    return 0\n  fi\n\n  return 1\n}\n/sms) {\n    $_\n  } else {\n    # If no is_delta() exists, prepend it near the top (after set -u line)\n    s/^(set -u[^\n]*\n)/$1\nis_delta() {\n  local f=\"$1\"\n  local base\n  base=\"$(basename \"$f\")\"\n\n  case \"$base\" in\n    MB__*|*__DELTA__*|*_DELTA_*) ;; \n    *) return 1 ;; \n  esac\n\n  case \"$base\" in\n    *.mips.json|*.json|*.mips.md|*.mips.txt) ;;\n    *) return 1 ;;\n  esac\n\n  if head -c 16384 \"$f\" 2>/dev/null | grep -qE \"MIPS_HEADER|\\\"MIPS_HEADER\\\"|\\\"DELTA\\\"|\\bDELTA\\b\"; then\n    return 0\n  fi\n  return 1\n}\n\n/sm;\n  }\n' "$SRC"

# Add explicit skip logging for delta-looking filenames (optional but makes debugging sane)
if ! grep -q 'SKIP not delta' "$SRC"; then
  perl -0777 -i -pe 's/is_delta \"\$f\" \|\| continue/is_delta \"\$f\" || { log \"[SKIP] not delta: \$f\"; continue; }/s' "$SRC"
fi

chmod +x "$SRC"
echo "[OK] is_delta patched."
EOF
chmod +x ~/bin/mb_patch_watch_isdelta.sh
~/bin/mb_patch_watch_isdelta.sh
```

## Re-run proof
```bash
pkill -f mb_watch_daemon.sh 2>/dev/null || true
: > ~/log/mb_watch.log
nohup ~/bin/mb_watch_daemon.sh >> ~/log/mb_watch.log 2>&1 &

# re-run the v3 test (or just create any real delta file in Downloads)
bash ~/bin/mb_watch_selftest_v3.sh
```

Expected:
- The test delta should be **auto-moved** into MB_INTAKE within ~15 seconds.
- If it still fails, the watcher log will now show `[SKIP] not delta:` lines that tell us exactly what file path is being rejected.

## Rollback
```bash
ls -1 ~/bin/mb_watch_daemon.sh.bak.isdelta.* | tail -n 1
# then cp that file back onto ~/bin/mb_watch_daemon.sh
```

## Burndown
Patch `is_delta` to recognize real MetaBlooms delta files reliably, so the watcher stops skipping and begins auto-routing+processing from Downloads without manual moves.
