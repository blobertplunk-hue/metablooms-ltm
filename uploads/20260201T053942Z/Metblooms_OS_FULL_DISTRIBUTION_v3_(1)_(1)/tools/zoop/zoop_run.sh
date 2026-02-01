#!/usr/bin/env bash
set -euo pipefail
ZIP_PATH="${1:-}"
if [[ -z "$ZIP_PATH" ]]; then
  echo "usage: tools/zoop/zoop_run.sh /path/to/MetaBlooms_OS.zip"
  exit 2
fi
python3 tools/zoop/zoop_guard.py --zip "$ZIP_PATH" --target /mnt/data/Metblooms_OS
