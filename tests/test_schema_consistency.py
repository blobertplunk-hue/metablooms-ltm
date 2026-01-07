#!/usr/bin/env python3
"""
Test: Schema Consistency Across MIPS Deltas

Verifies that all MIPS deltas use consistent header format.
Expected failure: Multiple formats detected.
"""

import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DELTAS_DIR = ROOT / "deltas" / "2025-12"


def detect_header_format(delta_file):
    """Detect which header format a delta uses"""
    try:
        with open(delta_file) as f:
            data = json.load(f)

        formats = []

        if "MIPS_HEADER" in data:
            formats.append("MIPS_HEADER (uppercase)")
        if "mips_header" in data:
            formats.append("mips_header (lowercase)")
        if "mips" in data:
            formats.append("mips (short)")
        if "meta" in data:
            formats.append("meta (alternate)")

        return formats if formats else ["no_header"]

    except Exception as e:
        return [f"error: {e}"]


def main():
    print("=" * 70)
    print("TEST: MIPS Schema Consistency")
    print("=" * 70)

    deltas = list(DELTAS_DIR.glob("*.mips.json"))

    format_counts = Counter()
    examples = {}

    for delta_file in deltas:
        formats = detect_header_format(delta_file)

        for fmt in formats:
            format_counts[fmt] += 1

            if fmt not in examples:
                examples[fmt] = delta_file.name

    print(f"\nAnalyzed {len(deltas)} delta files\n")
    print("Header formats found:")

    for fmt, count in format_counts.most_common():
        print(f"  {fmt}: {count} files")
        print(f"    Example: {examples[fmt]}")

    unique_formats = len([f for f in format_counts if not f.startswith("error")])

    print("\n" + "=" * 70)

    if unique_formats == 1:
        print("✅ PASS: All deltas use consistent schema")
        return 0
    else:
        print(f"❌ FAIL: {unique_formats} different header formats detected")
        print("\nIMPACT: Cannot build universal validator")
        print("FIX: Canonicalize to one format")
        return 1


if __name__ == "__main__":
    sys.exit(main())
