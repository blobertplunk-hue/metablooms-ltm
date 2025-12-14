MIPS_HEADER:
  artifact_id: MB__LOOP_MVP_LTM_PIPELINE__2025-12-14_v1
  parent_bundle: MetaBlooms_Core
  version: v1
  councils: [Facilitator, Auditor, Synthesist, Recorder]
  sha256: 41f2763e97d438c9ce89580f3028de071b32e180871bfc9e464fbe4993d4224f
  timestamp_utc: 2025-12-14T18:50:08Z
  evidence_chain:
    - claim: "Defines MVP external LTM loop mechanics: ChatGPT -> Downloads -> Termux/PowerShell watcher -> GitHub -> Chat retrieval -> integration -> new deltas."
      evidence_weight: 0.72
      failure_signal: "Requires user to run scripts; GitHub auth/permissions may vary."
      owner: "assistant"
      next_review_date: "2026-01-14"
  content_type: text/markdown
  links:
    - rel: "runbook"
      href: "This document"
BODY:

# MetaBlooms — MVP External LTM Loop Mechanics (Chat → Downloads → Watcher → GitHub → Chat → Integrate)

## 0) Canonical loop (your idea, made executable)
1. **Chat produces deltas** (downloadable artifacts).
2. You **download** them to your device.
3. A **watcher** (Termux or PowerShell) monitors your Downloads folder.
4. When new deltas appear, watcher **pushes to GitHub** (static endpoint).
5. In future chats, **web.run** pulls the latest deltas (via a manifest).
6. LLM **ingests + stages/activates** per Phase 1.2 rules.
7. LLM writes updated consolidated OS / new deltas to `/mnt/data` for download.
8. Repeat.

---

## 1) Real mechanics: stable identifiers + folder conventions

### 1.1 Delta filename contract (minimum viable)
Watcher treats a file as a delta if:
- filename contains `__DELTA__` (recommended) OR starts with `MB__` and contains `DELTA`
- extension is `.json` / `.txt` / `.md`
- file size > 0

Recommended naming:
- `MB__03_DELTA__<Topic>_vN.mips.json`
- `MB__01_DELTA__<Topic>_vN.mips.json`

### 1.2 Intake staging (prevents partial upload)
- Android: `/sdcard/Download/MB_INTAKE/`
- Windows: `C:\Users\Hrothgar\Downloads\MB_INTAKE\`

---

## 2) GitHub as external LTM dropbox

### 2.1 Repo layout
```
metablooms-ltm/
  deltas/
    2025-12/
      MB__03_DELTA__InvariantFirstGate_v1.mips.json
  manifests/
    latest.json
    ledger.ndjson
```

### 2.2 Two files make the loop reliable
- **ledger.ndjson** (append-only): one line per upload with hash/size/path
- **latest.json** (overwrite OK): last N ledger items for easy retrieval

---

## 3) Watcher responsibilities

### 3.1 Atomicity
Only upload when stable:
- size unchanged for 2 consecutive checks
- ignore `*.crdownload`

### 3.2 Deduplication
Compute SHA-256 and skip if present in ledger.

### 3.3 Append-only evidence
Ledger line format:
```json
{"ts":"2025-12-14T23:00:00Z","path":"deltas/2025-12/MB__03_DELTA__X_v1.mips.json","sha256":"...","bytes":12345,"host":"android-termux"}
```

---

## 4) Chat-side retrieval mechanics

### 4.1 Retrieval target
Fetch `manifests/latest.json`, then fetch each referenced delta.

### 4.2 Ingestion rule
- Everything fetched is **INGESTED** (even malformed; those become QUARANTINED later).
- Activation is CSR + stewardship gated.

### 4.3 Consolidation rule
Consolidate only if:
- lossless / shrinkage-safe
- all ingested deltas remain addressable (archived, never deleted)

---

## 5) MVP scripts

### 5.1 Termux watcher (Android)

**Filename:** `mb_watch_and_push_termux.sh`

```bash
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

### PREFLIGHT
command -v git >/dev/null || { echo "[FAIL] git missing"; exit 1; }
command -v jq  >/dev/null || { echo "[FAIL] jq missing"; exit 1; }
command -v sha256sum >/dev/null || { echo "[FAIL] sha256sum missing"; exit 1; }

### CONFIG (EDIT THESE)
REPO_DIR="$HOME/metablooms-ltm"
WATCH_DIR="/sdcard/Download"
INTAKE_DIR="$WATCH_DIR/MB_INTAKE"
MONTH="$(date -u +%Y-%m)"
DELTA_DIR="$REPO_DIR/deltas/$MONTH"
LEDGER="$REPO_DIR/manifests/ledger.ndjson"
LATEST="$REPO_DIR/manifests/latest.json"
HOST_TAG="android-termux"

mkdir -p "$INTAKE_DIR" "$DELTA_DIR" "$(dirname "$LEDGER")"

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "[FAIL] Repo not found at $REPO_DIR. Clone it first."
  exit 1
fi

cd "$REPO_DIR"
git pull --rebase

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
  tail -n 25 "$LEDGER" | tac | jq -s '{generated_utc: (now|todateiso8601), items: .}' > "$LATEST"
}

process_file() {
  local src="$1"
  local base
  base="$(basename "$src")"

  echo "[OK] Intake $base"
  mv "$src" "$INTAKE_DIR/$base"

  local intake="$INTAKE_DIR/$base"
  until stable_file "$intake"; do sleep 1; done

  local sha bytes
  sha="$(sha_of "$intake")"
  bytes="$(stat -c%s "$intake")"

  if already_in_ledger "$sha"; then
    echo "[OK] Duplicate (sha=$sha) — skipping upload: $base"
    rm -f "$intake"
    return
  fi

  cp "$intake" "$DELTA_DIR/$base"
  rm -f "$intake"

  local rel="deltas/$MONTH/$base"
  printf '{"ts":"%s","path":"%s","sha256":"%s","bytes":%s,"host":"%s"}\n'     "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$rel" "$sha" "$bytes" "$HOST_TAG" >> "$LEDGER"

  emit_latest

  git add "$DELTA_DIR/$base" "$LEDGER" "$LATEST"
  git commit -m "ingest: $base" >/dev/null || true
  git push

  echo "[OK] Uploaded $base → $rel"
}

echo "[OK] Watching $WATCH_DIR for MB deltas..."
while true; do
  while IFS= read -r f; do
    [[ "$f" == *.crdownload ]] && continue
    is_delta "$f" || continue
    process_file "$f"
  done < <(find "$WATCH_DIR" -maxdepth 1 -type f 2>/dev/null)

  sleep 3
done
```

**Debug harness**
```bash
echo '{"test":true}' > /sdcard/Download/MB__03_DELTA__TEST_v1.mips.json
bash mb_watch_and_push_termux.sh
```

---

### 5.2 PowerShell watcher (Windows 10)

**Filename:** `mb_watch_and_push_windows.ps1`

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Assert-Command($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    Write-Host "[FAIL] Missing command: $name"
    exit 1
  }
}
Assert-Command git

# CONFIG (EDIT)
$RepoDir   = "C:\Users\Hrothgar\Downloads\MBProj\metablooms-ltm"
$WatchDir  = "C:\Users\Hrothgar\Downloads"
$IntakeDir = Join-Path $WatchDir "MB_INTAKE"
$Month     = (Get-Date).ToUniversalTime().ToString("yyyy-MM")
$DeltaDir  = Join-Path $RepoDir ("deltas\" + $Month)
$Ledger    = Join-Path $RepoDir "manifests\ledger.ndjson"
$Latest    = Join-Path $RepoDir "manifests\latest.json"
$HostTag   = "windows-ps5"

New-Item -ItemType Directory -Force -Path $IntakeDir, $DeltaDir, (Split-Path $Ledger) | Out-Null

if (-not (Test-Path (Join-Path $RepoDir ".git"))) {
  Write-Host "[FAIL] Repo not found at $RepoDir. Clone it first."
  exit 1
}

function Is-DeltaFile($path) {
  $name = [IO.Path]::GetFileName($path)
  return ($name -match "__DELTA__" -or ($name -match "^MB__" -and $name -match "DELTA")) -and ($name -match "\.json$|\.txt$|\.md$")
}

function Get-Sha256($path) {
  return (Get-FileHash -Algorithm SHA256 -Path $path).Hash.ToLower()
}

function Already-InLedger($sha) {
  if (-not (Test-Path $Ledger)) { return $false }
  return (Select-String -Path $Ledger -Pattern $sha -Quiet)
}

function Emit-Latest {
  if (-not (Test-Path $Ledger)) { return }
  $lines = Get-Content $Ledger -Tail 25
  $items = @()
  foreach ($ln in ($lines | [Array]::Reverse([string[]]$lines))) {
    try { $items += (ConvertFrom-Json $ln) } catch {}
  }
  $obj = [PSCustomObject]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString("o")
    items = $items
  }
  $obj | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $Latest
}

function Wait-StableFile($path) {
  $s1 = (Get-Item $path).Length
  Start-Sleep -Seconds 1
  $s2 = (Get-Item $path).Length
  return ($s1 -gt 0 -and $s1 -eq $s2)
}

function Process-Delta($src) {
  $base = [IO.Path]::GetFileName($src)
  Write-Host "[OK] Intake $base"

  $intake = Join-Path $IntakeDir $base
  Move-Item -Force $src $intake

  while (-not (Wait-StableFile $intake)) { Start-Sleep -Seconds 1 }

  $sha = Get-Sha256 $intake
  $bytes = (Get-Item $intake).Length

  if (Already-InLedger $sha) {
    Write-Host "[OK] Duplicate (sha=$sha) — skipping upload: $base"
    Remove-Item -Force $intake
    return
  }

  $dest = Join-Path $DeltaDir $base
  Copy-Item -Force $intake $dest
  Remove-Item -Force $intake

  $rel = ("deltas/{0}/{1}" -f $Month, $base)
  $ts  = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $line = (@{ ts=$ts; path=$rel; sha256=$sha; bytes=$bytes; host=$HostTag } | ConvertTo-Json -Compress)

  Add-Content -Encoding UTF8 -Path $Ledger -Value $line
  Emit-Latest

  Push-Location $RepoDir
  git pull --rebase | Out-Null
  git add $dest $Ledger $Latest | Out-Null
  git commit -m ("ingest: {0}" -f $base) | Out-Null
  git push | Out-Null
  Pop-Location

  Write-Host "[OK] Uploaded $base → $rel"
}

Write-Host "[OK] Watching $WatchDir for MB delta files..."
while ($true) {
  Get-ChildItem -Path $WatchDir -File | ForEach-Object {
    if ($_.Name -like "*.crdownload") { return }
    if (Is-DeltaFile $_.FullName) { Process-Delta $_.FullName }
  }
  Start-Sleep -Seconds 3
}
```

**Debug harness**
```powershell
'{"test":true}' | Set-Content -Encoding UTF8 "$env:USERPROFILE\Downloads\MB__03_DELTA__TEST_v1.mips.json"
powershell -ExecutionPolicy Bypass -File .\mb_watch_and_push_windows.ps1
```

---

## 6) Chat retrieval prompt (copy/paste)

```text
Sandcrawler Prime: fetch manifests/latest.json from my metablooms-ltm repo, then fetch all referenced deltas.
Ingest ALL of them (even malformed), classify, and run CSR + stewardship gates.
Output:
1) delta-state table (INGESTED/STAGED/ACTIVE/QUARANTINED/ARCHIVED + reason),
2) any newly generated deltas,
3) consolidated OS only if lossless and shrinkage-safe; otherwise refuse and explain.
```

---

## 7) One-line burndown
Implemented the end-to-end external LTM loop mechanics with stable manifest + ledger and provided Termux and PowerShell watcher scripts plus a retrieval prompt.
