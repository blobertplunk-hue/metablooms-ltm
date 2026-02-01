#!/usr/bin/env bash
# MetaBlooms Boot Entrypoint (fail-closed with receipts; never "refuses" to boot)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")"/.. && pwd)"
UTC="$(date -u +%Y%m%dT%H%M%SZ)"
BOOT_DIR="$ROOT/boot"
BTS_DIR="$ROOT/_bts"
mkdir -p "$BOOT_DIR" "$BTS_DIR"

BOOT_REC="$BOOT_DIR/boot_receipt_${UTC}.json"
BTS_REC="$BTS_DIR/bts_tick_receipt_${UTC}.json"

# Always emit an attempt receipt first
python3 - << 'PY'
import json, os, time, platform
utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
attempt={
  "utc": utc,
  "status": "BOOT_ATTEMPT",
  "root": os.environ.get("ROOT",""),
  "platform": platform.platform()
}
open(os.environ["BOOT_REC"],"w",encoding="utf-8").write(json.dumps(attempt,indent=2))
PY

# Then attempt to emit BTS tick; if anything fails, emit BOOT_FAIL receipts and exit nonzero.
set +e
python3 - << 'PY'
import json, os, time, traceback
utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
try:
    tick={"utc":utc,"status":"BTS_OK"}
    open(os.environ["BTS_REC"],"w",encoding="utf-8").write(json.dumps(tick,indent=2))
    ok={"utc":utc,"status":"BOOT_OK"}
    open(os.environ["BOOT_REC"],"w",encoding="utf-8").write(json.dumps(ok,indent=2))
except Exception as e:
    fail={"utc":utc,"status":"BOOT_FAIL","error":repr(e),"trace":traceback.format_exc()[:4000]}
    open(os.environ["BOOT_REC"],"w",encoding="utf-8").write(json.dumps(fail,indent=2))
    open(os.environ["BTS_REC"],"w",encoding="utf-8").write(json.dumps({"utc":utc,"status":"BTS_FAIL"},indent=2))
    raise
PY
rc=$?
set -e

if [ $rc -ne 0 ]; then
  echo "BOOT_FAIL"
  exit $rc
fi

echo "BOOT_OK"
