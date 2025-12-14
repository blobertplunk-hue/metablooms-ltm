---
mips:
  artifact_id: "MB__90_TOOL__Termux_OneShot_Publish_v1"
  version: "v1"
  timestamp_utc: "2025-12-14T00:54:22Z"
  content_type: "text/markdown"
  councils: ["Auditor","Hacker","Recorder"]
  audit: "construct"
  links:
    spec_ref: "MB__SPEC__External_LTM_and_Shipping_Plan_v1.md"
---
# MetaBlooms Termux One‑Shot Publisher (paste once)

## Paste this whole block into Termux

```bash
set -euo pipefail

# ===== USER EDIT (3 lines) =====
SRC_DIR="/sdcard/Download/metablooms"        # folder containing the 3 MetaBlooms files
REPO_URL="https://github.com/YOURUSER/YOURREPO.git"
HOST_BASE_URL="https://YOURUSER.github.io/YOURREPO"
# ===============================

REPO_DIR="$HOME/metablooms_ltm"
ART_DIR="$REPO_DIR/artifacts"
DEL_DIR="$REPO_DIR/deltas"
IDX_DIR="$REPO_DIR/index"

pkg install -y git jq openssl >/dev/null

if [ ! -d "$REPO_DIR/.git" ]; then
  rm -rf "$REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
fi

mkdir -p "$ART_DIR" "$DEL_DIR" "$IDX_DIR"

# Copy (keep canonical publish names)
cp "$SRC_DIR/MB__OS__MetaBlooms_Core__ACTIVE.mips.json" "$ART_DIR/MB__OS__MetaBlooms_Core__ACTIVE.mips.json"
cp "$SRC_DIR/MB__01_COREPACK__GovHardening_v7__2025-12-13.mips.json" "$ART_DIR/MB__01_COREPACK__GovHardening_v7.mips.json"
cp "$SRC_DIR/MB__03_DELTA__ChatGPTNativeBrowser_Synthesis_v1.mips.json" "$DEL_DIR/MB__03_DELTA__ChatGPTNativeBrowser_Synthesis_v1.mips.json"

hash() { sha256sum "$1" | awk '{print $1}'; }

OS="$ART_DIR/MB__OS__MetaBlooms_Core__ACTIVE.mips.json"
CP="$ART_DIR/MB__01_COREPACK__GovHardening_v7.mips.json"
D1="$DEL_DIR/MB__03_DELTA__ChatGPTNativeBrowser_Synthesis_v1.mips.json"

OS_H="$(hash "$OS")"
CP_H="$(hash "$CP")"
D1_H="$(hash "$D1")"

TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

cat > "$IDX_DIR/Memory_Index.json" <<EOF
{
  "version": "$TS",
  "active": {
    "os": {
      "url": "$HOST_BASE_URL/artifacts/$(basename "$OS")",
      "sha256": "$OS_H"
    },
    "corepack": {
      "url": "$HOST_BASE_URL/artifacts/$(basename "$CP")",
      "sha256": "$CP_H"
    }
  },
  "delta_queue": [
    {
      "url": "$HOST_BASE_URL/deltas/$(basename "$D1")",
      "sha256": "$D1_H"
    }
  ]
}
EOF

cd "$REPO_DIR"
git add -A
git commit -m "Publish MetaBlooms $TS" >/dev/null || true
git push

echo "OK: $HOST_BASE_URL/index/Memory_Index.json"
```

Notes:
- You only edit **SRC_DIR**, **REPO_URL**, **HOST_BASE_URL**.
- No guessing paths; no “I looked at your phone”; this runs locally on-device.
