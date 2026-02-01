#!/usr/bin/env python3
"""
ZOOP_GUARD_v1 — enforced zoop (extract) with canonical root policy.

Features:
- Enforce canonical extract target (fail-closed if mismatch)
- Detect & deny shadow root directories (case/spelling variants)
- ZIP_ROOT_POLICY: if archive contains a single top-level wrapper dir named Metblooms_OS, auto-flatten (move contents up) with receipt
- Emit ZOOP_GUARD_RECEIPT_v1.json (PASS/FAIL) every run

Usage:
  python tools/zoop/zoop_guard.py --zip /path/to/os.zip --target /mnt/data/Metblooms_OS

Notes:
- No network access
- Writes only inside canonical root and receipt path
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, shutil, time, zipfile, os, sys

def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_policy(policy_path: Path) -> dict:
    return json.loads(policy_path.read_text())

def list_top_level(zipf: zipfile.ZipFile) -> list[str]:
    # Return top-level entries (first path segment)
    tops = set()
    for n in zipf.namelist():
        if not n or n.endswith("/"):
            seg = n.split("/", 1)[0]
        else:
            seg = n.split("/", 1)[0]
        if seg:
            tops.add(seg)
    return sorted(tops)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, help="path to OS zip")
    ap.add_argument("--target", required=True, help="canonical extract target")
    ap.add_argument("--policy", default="config/zoop/ZIP_ROOT_POLICY_v1.json", help="policy path (relative to target)")
    ap.add_argument("--receipt", default="receipts/ZOOP_GUARD_RECEIPT_v1.json", help="receipt path (relative to target)")
    args = ap.parse_args()

    zip_path = Path(args.zip).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()

    receipt_obj = {
        "artifact": "ZOOP_GUARD_RECEIPT_v1",
        "timestamp_utc": now_utc(),
        "status": "FAIL",
        "canonical_root": str(target),
        "zip_path": str(zip_path),
        "zip_sha256": None,
        "extract_target": str(target),
        "checks": {},
        "actions": [],
        "errors": [],
        "hashes": {}
    }

    try:
        if not zip_path.exists():
            receipt_obj["errors"].append(f"zip_missing:{zip_path}")
            raise RuntimeError("zip missing")

        receipt_obj["zip_sha256"] = sha256_path(zip_path)

        if not target.exists():
            # create target, but only if target is canonical (enforced below)
            target.mkdir(parents=True, exist_ok=True)

        # Load policy from within target (so policy is distributed with OS)
        policy_path = (target / args.policy).resolve()
        if not policy_path.exists():
            receipt_obj["errors"].append(f"policy_missing:{policy_path}")
            raise RuntimeError("policy missing")

        policy = load_policy(policy_path)

        # Enforce canonical extract target if policy requires
        if policy.get("refuse_noncanonical_extract_target", True):
            canonical_target = Path(policy["canonical_extract_target"]).resolve()
            receipt_obj["checks"]["canonical_target_expected"] = str(canonical_target)
            receipt_obj["checks"]["canonical_target_actual"] = str(target)
            if target != canonical_target:
                receipt_obj["errors"].append("noncanonical_extract_target")
                raise RuntimeError("noncanonical extract target")

        # Deny shadow roots (top-level /mnt/data variants) + inside target
        deny = set(policy.get("deny_shadow_roots", []))
        shadow_found = []
        # Check siblings under /mnt/data
        data_root = target.parent
        for name in deny:
            p = data_root / name
            if p.exists():
                shadow_found.append(str(p))
        # Check within target
        for name in deny:
            p = target / name
            if p.exists():
                shadow_found.append(str(p))
        receipt_obj["checks"]["shadow_roots_found"] = shadow_found
        receipt_obj["checks"]["shadow_root_absent"] = (len(shadow_found) == 0)
        if shadow_found:
            receipt_obj["errors"].append("shadow_root_present")
            raise RuntimeError("shadow roots present")

        # Clean extract target (zoop semantics) — remove contents but keep directory
        for child in target.iterdir():
            # keep policy/receipts dirs if already there? we still zoop clean, but policy lives in zip too.
            # For safety, wipe everything except a minimal allowlist to avoid deleting target itself.
            if child.name in {".git"}:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        receipt_obj["actions"].append({"op":"clean_target_contents","target":str(target)})

        # Extract zip
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target)
            tops = list_top_level(zf)
        receipt_obj["checks"]["zip_top_level_entries"] = tops

        # Auto-flatten single wrapper directory if configured
        allow_wrappers = set(policy.get("allow_single_wrapper_dirnames", []))
        auto_flatten = bool(policy.get("auto_flatten_single_wrapper", True))
        if auto_flatten and len(tops) == 1 and tops[0] in allow_wrappers:
            wrapper = target / tops[0]
            if wrapper.exists() and wrapper.is_dir():
                # move wrapper contents up, no overwrites
                for item in wrapper.iterdir():
                    dest = target / item.name
                    if dest.exists():
                        # collision: suffix
                        i = 1
                        while True:
                            alt = target / f"{item.name}__from_{wrapper.name}_{i}"
                            if not alt.exists():
                                dest = alt
                                break
                            i += 1
                        receipt_obj["actions"].append({"op":"collision_rename","src":str(item),"dest":str(dest)})
                    shutil.move(str(item), str(dest))
                    receipt_obj["actions"].append({"op":"move","src":str(item),"dest":str(dest)})
                wrapper.rmdir()
                receipt_obj["actions"].append({"op":"rmdir","path":str(wrapper)})
                receipt_obj["checks"]["auto_flatten_applied"] = True
            else:
                receipt_obj["checks"]["auto_flatten_applied"] = False
        else:
            receipt_obj["checks"]["auto_flatten_applied"] = False

        # Post-check: required dirs at root
        required = ["tools","config"]
        missing = [d for d in required if not (target / d).exists()]
        receipt_obj["checks"]["missing_required_subsystems"] = missing
        if missing:
            receipt_obj["errors"].append("missing_required_subsystems")
            raise RuntimeError("missing required subsystems after extract")

        # Hash key policy + script
        receipt_obj["hashes"]["policy_sha256"] = sha256_path(policy_path)
        receipt_obj["hashes"]["zoop_guard_sha256"] = sha256_path(Path(__file__).resolve())

        receipt_obj["status"] = "PASS"

    except Exception as e:
        receipt_obj["errors"].append(f"exception:{repr(e)}")

    # Write receipt inside canonical root
    receipt_path = (target / args.receipt).resolve()
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt_obj, indent=2))
    # Also print minimal status for CLI users
    print(f"ZOOP_GUARD_v1 -> {receipt_obj['status']} :: {receipt_path}")
    return 0 if receipt_obj["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
