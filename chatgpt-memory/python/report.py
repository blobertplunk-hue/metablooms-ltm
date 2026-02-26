#!/usr/bin/env python3
"""
Phase 5: report.py
Generates telemetry reports from the memory index (memory.db).
Outputs CSV + JSON for all 5 dashboards.

Run: python report.py --db workspace/index/memory.db --out workspace/reports/
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


QUERIES = {
    "dashboard_1_reliability_over_time": """
        SELECT
            strftime('%Y-%W', datetime(c.create_time, 'unixepoch')) AS week,
            COUNT(*) AS conv_count,
            ROUND(AVG(
                1.0 - CAST(
                    COALESCE(f.refusal_detected, 0) +
                    COALESCE(f.conversation_abandoned, 0)
                AS REAL) / MAX(COALESCE(f.turn_count, 1), 1)
            ), 4) AS reliability_score,
            SUM(COALESCE(f.refusal_detected, 0)) AS refusals,
            SUM(COALESCE(f.conversation_abandoned, 0)) AS abandoned
        FROM conversations c
        LEFT JOIN features f USING (conv_id)
        GROUP BY week
        ORDER BY week
    """,

    "dashboard_2_archetype_performance": """
        SELECT
            COALESCE(f.prompt_archetype, 'unknown') AS archetype,
            COUNT(*) AS n,
            ROUND(AVG(COALESCE(f.rework_loop_count, 0)), 3) AS avg_rework,
            ROUND(AVG(f.time_to_resolution), 2) AS avg_resolution_min,
            SUM(COALESCE(f.success_signal, 0)) AS successes,
            ROUND(100.0 * SUM(COALESCE(f.success_signal, 0)) / COUNT(*), 1) AS success_rate_pct
        FROM features f
        GROUP BY archetype
        ORDER BY avg_rework ASC
    """,

    "dashboard_3_regression_hotspots": """
        SELECT
            c.conv_id,
            c.title,
            c.model,
            strftime('%Y-%m-%d', datetime(c.create_time, 'unixepoch')) AS date,
            f.regression_count,
            f.rework_loop_count,
            f.conversation_abandoned,
            f.refusal_detected
        FROM features f
        JOIN conversations c USING (conv_id)
        WHERE f.regression_count > 1 OR f.rework_loop_count > 2
        ORDER BY f.regression_count DESC, f.rework_loop_count DESC
        LIMIT 100
    """,

    "dashboard_4_tool_usage": """
        SELECT
            CASE WHEN f.tool_call_count > 0 THEN 'with_tools' ELSE 'no_tools' END AS tool_usage,
            COUNT(*) AS n,
            ROUND(AVG(COALESCE(f.rework_loop_count, 0)), 3) AS avg_rework,
            ROUND(AVG(f.time_to_resolution), 2) AS avg_resolution_min,
            SUM(COALESCE(f.success_signal, 0)) AS successes
        FROM features f
        GROUP BY tool_usage
    """,

    "dashboard_5_sentiment_vs_productivity": """
        SELECT
            CASE
                WHEN f.prompt_sentiment < -0.3 THEN 'negative'
                WHEN f.prompt_sentiment > 0.3  THEN 'positive'
                WHEN f.prompt_sentiment IS NULL THEN 'unknown'
                ELSE 'neutral'
            END AS sentiment_bucket,
            COUNT(*) AS n,
            ROUND(AVG(COALESCE(f.rework_loop_count, 0)), 3) AS avg_rework,
            ROUND(AVG(f.time_to_resolution), 2) AS avg_resolution_min,
            SUM(COALESCE(f.success_signal, 0)) AS successes
        FROM features f
        GROUP BY sentiment_bucket
        ORDER BY avg_rework ASC
    """,

    "summary_by_model": """
        SELECT
            COALESCE(c.model, 'unknown') AS model,
            COUNT(*) AS conv_count,
            ROUND(AVG(COALESCE(f.turn_count, 0)), 1) AS avg_turns,
            ROUND(AVG(COALESCE(f.prompt_token_est, 0)), 0) AS avg_prompt_tokens,
            ROUND(AVG(COALESCE(f.response_token_est, 0)), 0) AS avg_response_tokens,
            SUM(COALESCE(f.refusal_detected, 0)) AS total_refusals,
            SUM(COALESCE(f.code_block_count, 0)) AS total_code_blocks
        FROM conversations c
        LEFT JOIN features f USING (conv_id)
        GROUP BY model
        ORDER BY conv_count DESC
    """,

    "safety_friction_overview": """
        SELECT
            SUM(COALESCE(refusal_detected, 0)) AS total_refusals,
            SUM(COALESCE(policy_boundary_hit, 0)) AS total_policy_hits,
            SUM(COALESCE(content_warning_present, 0)) AS total_content_warnings,
            COUNT(*) AS total_conversations,
            ROUND(100.0 * SUM(COALESCE(refusal_detected, 0)) / COUNT(*), 2) AS refusal_rate_pct
        FROM features
    """,
}


def run_report(db_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    generated_at = datetime.now(tz=timezone.utc).isoformat()
    summary: dict[str, object] = {
        "generated_at": generated_at,
        "db_path": str(db_path),
        "dashboards": {},
    }

    for name, sql in QUERIES.items():
        try:
            df = pd.read_sql_query(sql.strip(), db)
            csv_path  = out_dir / f"{name}.csv"
            json_path = out_dir / f"{name}.json"

            df.to_csv(csv_path, index=False)
            records = df.to_dict(orient="records")

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "report":       name,
                    "generated_at": generated_at,
                    "artifact_sources": [str(db_path)],
                    "row_count":    len(records),
                    "grounded":     True,
                    "data":         records,
                }, f, indent=2, ensure_ascii=False, default=str)

            summary["dashboards"][name] = {
                "rows": len(records),
                "csv":  str(csv_path),
                "json": str(json_path),
            }

            print(f"  {name}: {len(records)} rows → {csv_path.name}")

        except Exception as exc:
            print(f"  [WARN] {name}: {exc}")
            summary["dashboards"][name] = {"error": str(exc)}

    db.close()

    summary_path = out_dir / "report-summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nReport summary: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5: Generate telemetry reports")
    parser.add_argument("--db",  required=True)
    parser.add_argument("--out", default="workspace/reports/")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    out_dir = Path(args.out).resolve()

    if not db_path.exists():
        print(f"ERROR: DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Generating reports from {db_path}…")
    run_report(db_path, out_dir)
    print(f"\nDone. Upload workspace/reports/ to LLM for analysis.")


if __name__ == "__main__":
    main()
