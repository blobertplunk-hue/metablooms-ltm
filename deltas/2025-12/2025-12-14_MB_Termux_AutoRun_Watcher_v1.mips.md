MIPS_HEADER:
  artifact_id: MB__TERMUX_AUTORUN_WATCHER__2025-12-14_v1
  parent_bundle: MB__LOOP_MVP_LTM_PIPELINE__2025-12-14_v1
  version: v1
  councils: [Auditor, Recorder]
  sha256: 6001fef126b7d24e33d8354a213853c6ae37a103ba8e5f01492a9ad220fdd571
  timestamp_utc: 2025-12-14T18:55:53Z
  content_type: text/markdown
BODY:

# Termux — Always-on Watcher (Automatic except downloads)

## Goal
Watcher runs **continuously** and survives reboots. Your only manual step is **downloading** deltas.

---

## 0) Requirements
- Termux installed
- Termux:API installed (for `termux-wake-lock`) — optional but recommended
- Termux:Boot installed (for auto-start on reboot)
- Battery optimization disabled for Termux + Termux:Boot (Android setting)

---

## 1) One-time install (copy/paste)
```bash
pkg update -y && pkg upgrade -y
pkg install -y git jq coreutils termux-api tmux
mkdir -p ~/bin ~/log ~/.termux/boot
```

---

## 2) Create the daemon runner
Create: `~/bin/mb_watch_daemon.sh`
```bash
cat > ~/bin/mb_watch_daemon.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# === PREFLIGHT (MetaBlooms SOP) ===
need() { command -v "$1" >/dev/null || { echo "[FAIL] missing $1"; exit 1; }; }
need git
need jq
need sha256sum
need stat

# keep CPU awake while running (requires termux-api)
if command -v termux-wake-lock >/dev/null; then termux-wake-lock || true; fi

# === CONFIG ===
REPO_DIR="$HOME/metablooms-ltm"
WATCH_DIR="/sdcard/Download"
INTAKE_DIR="$WATCH_DIR/MB_INTAKE"
MONTH="$(date -u +%Y-%m)"
DELTA_DIR="$REPO_DIR/deltas/$MONTH"
LEDGER="$REPO_DIR/manifests/ledger.ndjson"
LATEST="$REPO_DIR/manifests/latest.json"
HOST_TAG="android-termux"
LOG="$HOME/log/mb_watch.log"

mkdir -p "$INTAKE_DIR" "$DELTA_DIR" "$(dirname "$LEDGER")" "$(dirname "$LOG")"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "$(ts) $*" | tee -a "$LOG"; }

if [ ! -d "$REPO_DIR/.git" ]; then
  log "[FAIL] Repo not found at $REPO_DIR. Clone it first."
  exit 1
fi

cd "$REPO_DIR"
git pull --rebase || true

is_delta() {
  local f="$1"
  case "$f" in
    *"__DELTA__"*.json|MB__*DELTA*.json|MB__*.mips.json|MB__*.txt|MB__*.md) return 0 ;;
    *) return 1 ;;
  esac
}

stable_file() {
  local f="$1"
  local s1 s2
  s1=$(stat -c%s "$f" 2>/dev/null || echo 0)
  sleep 1
  s2=$(stat -c%s "$f" 2>/dev/null || echo 0)
  [ "$s1" -gt 0 ] && [ "$s1" = "$s2" ]
}

sha_of() { sha256sum "$1" | awk '{print $1}'; }

already_in_ledger() {
  local sha="$1"
  [ -f "$LEDGER" ] && grep -q "$sha" "$LEDGER"
}

emit_latest() {
  if [ -f "$LEDGER" ]; then
    tail -n 25 "$LEDGER" | tac | jq -s '{generated_utc: (now|todateiso8601), items: .}' > "$LATEST"
  else
    echo '{"generated_utc":null,"items":[]}' > "$LATEST"
  fi
}

process_file() {
  local src="$1"
  local base intake sha bytes rel
  base="$(basename "$src")"

  log "[OK] Intake $base"
  mv "$src" "$INTAKE_DIR/$base"
  intake="$INTAKE_DIR/$base"

  until stable_file "$intake"; do sleep 1; done

  sha="$(sha_of "$intake")"
  bytes="$(stat -c%s "$intake")"

  if already_in_ledger "$sha"; then
    log "[OK] Duplicate sha=$sha — skip $base"
    rm -f "$intake"
    return
  fi

  cp "$intake" "$DELTA_DIR/$base"
  rm -f "$intake"

  rel="deltas/$MONTH/$base"
  printf '{"ts":"%s","path":"%s","sha256":"%s","bytes":%s,"host":"%s"}\n'     "$(ts)" "$rel" "$sha" "$bytes" "$HOST_TAG" >> "$LEDGER"

  emit_latest

  cd "$REPO_DIR"
  git add "$DELTA_DIR/$base" "$LEDGER" "$LATEST"
  git commit -m "ingest: $base" >/dev/null || true
  git push && log "[OK] Uploaded $base → $rel" || log "[FAIL] git push failed (will retry on next loop)"
}

log "[OK] Watcher running. Monitoring: $WATCH_DIR"

while true; do
  while IFS= read -r f; do
    [[ "$f" == *.crdownload ]] && continue
    is_delta "$f" || continue
    process_file "$f"
  done < <(find "$WATCH_DIR" -maxdepth 1 -type f 2>/dev/null)

  sleep 3
done
EOF

chmod +x ~/bin/mb_watch_daemon.sh
```

---

## 3) Make it survive reboot (Termux:Boot)
Create: `~/.termux/boot/start-mb-watch.sh`
```bash
cat > ~/.termux/boot/start-mb-watch.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# run watcher inside tmux so it stays alive and you can attach later
SESSION="mb_watch"

if command -v termux-wake-lock >/dev/null; then termux-wake-lock || true; fi

# small delay lets Android finish mounting storage
sleep 8

if ! command -v tmux >/dev/null; then
  echo "[FAIL] tmux missing"
  exit 1
fi

tmux has-session -t "$SESSION" 2>/dev/null && exit 0
tmux new-session -d -s "$SESSION" "$HOME/bin/mb_watch_daemon.sh"
EOF

chmod +x ~/.termux/boot/start-mb-watch.sh
```

---

## 4) Manual start / status (no reboot needed)
```bash
# start
tmux new -d -s mb_watch "$HOME/bin/mb_watch_daemon.sh" || true

# view live logs
tail -f ~/log/mb_watch.log

# attach to session
tmux attach -t mb_watch
```

---

## 5) Debug harness (proves it works)
```bash
echo '{"test":true}' > /sdcard/Download/MB__03_DELTA__TEST_v1.mips.json
sleep 5
grep TEST ~/log/mb_watch.log || true
```

---

## 6) Debug log entry template (canonical)
```text
UTC:
CONTEXT:
ERROR:
CAUSE:
FIX:
VERIFIED:
STATUS: [OK]/[FAIL]
SHA256(artifact):
```

