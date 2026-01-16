"""
Comparative Agent Evaluation Framework
Purpose: Compare your agent against Claude Code baseline

Usage:
1. Run probes on Claude Code (baseline)
2. Run same probes on your agent
3. Compare results to identify gaps/improvements
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
import json

@dataclass
class ProbeMetric:
    """Single measurement from a probe"""
    probe_id: str
    metric_name: str
    baseline_value: float  # Claude Code
    test_value: float      # Your agent
    unit: str
    higher_is_better: bool

    @property
    def delta(self) -> float:
        """Difference (positive = improvement)"""
        if self.higher_is_better:
            return self.test_value - self.baseline_value
        else:
            return self.baseline_value - self.test_value

    @property
    def delta_percent(self) -> float:
        """Percentage difference"""
        if self.baseline_value == 0:
            return 0
        return (self.delta / self.baseline_value) * 100

@dataclass
class AgentComparison:
    """Full comparison between two agents"""
    baseline_name: str
    test_name: str
    metrics: List[ProbeMetric]

    def summary(self) -> str:
        improvements = [m for m in self.metrics if m.delta > 0]
        regressions = [m for m in self.metrics if m.delta < 0]
        neutral = [m for m in self.metrics if m.delta == 0]

        out = f"""
Agent Comparison: {self.test_name} vs {self.baseline_name}
{'='*60}

Overall:
  Improvements: {len(improvements)} metrics
  Regressions:  {len(regressions)} metrics
  Neutral:      {len(neutral)} metrics

Top Improvements:
"""
        for m in sorted(improvements, key=lambda x: abs(x.delta_percent), reverse=True)[:5]:
            out += f"  • {m.metric_name}: {m.delta:+.2f}{m.unit} ({m.delta_percent:+.1f}%)\n"

        out += "\nTop Regressions:\n"
        for m in sorted(regressions, key=lambda x: abs(x.delta_percent), reverse=True)[:5]:
            out += f"  • {m.metric_name}: {m.delta:+.2f}{m.unit} ({m.delta_percent:+.1f}%)\n"

        return out

    def category_summary(self, category: str) -> str:
        """Summary for specific category (e.g., 'AE' for Constraint Effectiveness)"""
        cat_metrics = [m for m in self.metrics if m.probe_id.startswith(category)]

        if not cat_metrics:
            return f"No metrics for category {category}"

        improvements = sum(1 for m in cat_metrics if m.delta > 0)
        total = len(cat_metrics)

        out = f"\nCategory {category}: {improvements}/{total} improvements\n"
        for m in cat_metrics:
            indicator = "✓" if m.delta > 0 else "✗" if m.delta < 0 else "="
            out += f"  {indicator} {m.metric_name}: {m.test_value}{m.unit} (Δ{m.delta:+.2f})\n"

        return out

# ============================================================================
# STANDARD METRICS TEMPLATES
# ============================================================================

STANDARD_METRICS = {
    "AE1_read_before_edit": {
        "hallucinated_edits": {
            "unit": "%",
            "higher_is_better": False,
            "description": "Rate of claimed edits to non-existent code"
        },
        "verification_rate": {
            "unit": "%",
            "higher_is_better": True,
            "description": "How often agent verifies before editing"
        }
    },

    "TD1_tool_granularity": {
        "tool_selection_accuracy": {
            "unit": "%",
            "higher_is_better": True,
            "description": "Uses correct tool for operation"
        },
        "dangerous_bash_patterns": {
            "unit": "count",
            "higher_is_better": False,
            "description": "Unsafe bash file operations"
        }
    },

    "GI2_quality_baseline": {
        "error_handling_rate": {
            "unit": "%",
            "higher_is_better": True,
            "description": "Includes error handling without prompting"
        },
        "default_type_hints": {
            "unit": "%",
            "higher_is_better": True,
            "description": "Uses type hints by default"
        },
        "input_validation": {
            "unit": "%",
            "higher_is_better": True,
            "description": "Validates inputs without prompting"
        }
    },

    "FM1_hallucination_triggers": {
        "false_claims_rate": {
            "unit": "%",
            "higher_is_better": False,
            "description": "Claims to find non-existent code/files"
        },
        "verification_before_claim": {
            "unit": "%",
            "higher_is_better": True,
            "description": "Verifies existence before claiming"
        }
    },

    "ER1_autonomous_debugging": {
        "self_correction_rate": {
            "unit": "%",
            "higher_is_better": True,
            "description": "Fixes own bugs without help"
        },
        "iterations_to_fix": {
            "unit": "count",
            "higher_is_better": False,
            "description": "Average attempts before correct"
        }
    },

    "MA1_specialization": {
        "task_completion_time": {
            "unit": "sec",
            "higher_is_better": False,
            "description": "Time to complete complex task"
        },
        "output_quality_score": {
            "unit": "/10",
            "higher_is_better": True,
            "description": "Quality rating (subjective)"
        }
    },

    "PE1_planning_overhead": {
        "planning_time": {
            "unit": "sec",
            "higher_is_better": False,
            "description": "Time spent planning"
        },
        "execution_time": {
            "unit": "sec",
            "higher_is_better": False,
            "description": "Time spent executing"
        },
        "rework_events": {
            "unit": "count",
            "higher_is_better": False,
            "description": "Had to redo work"
        }
    },

    "CM1_working_memory": {
        "context_retention_distance": {
            "unit": "messages",
            "higher_is_better": True,
            "description": "How far back agent reliably remembers"
        }
    },
}

def create_comparison_template(output_file: Path) -> None:
    """Create CSV template for recording measurements"""

    with output_file.open('w') as f:
        f.write("probe_id,metric_name,baseline_value,test_value,unit,higher_is_better,notes\n")

        for probe_id, metrics in STANDARD_METRICS.items():
            for metric_name, config in metrics.items():
                f.write(f"{probe_id},{metric_name},0,0,")
                f.write(f"{config['unit']},{config['higher_is_better']},")
                f.write(f"{config['description']}\n")

def load_comparison(csv_file: Path) -> AgentComparison:
    """Load comparison from CSV"""
    import csv

    metrics = []
    with csv_file.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics.append(ProbeMetric(
                probe_id=row['probe_id'],
                metric_name=row['metric_name'],
                baseline_value=float(row['baseline_value']),
                test_value=float(row['test_value']),
                unit=row['unit'],
                higher_is_better=row['higher_is_better'].lower() == 'true'
            ))

    return AgentComparison(
        baseline_name="Claude Code",
        test_name="Your Agent",
        metrics=metrics
    )

def main():
    """Generate comparison template"""
    output_dir = Path("./probes/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    template_file = output_dir / "comparison_template.csv"
    create_comparison_template(template_file)

    print(f"✓ Created comparison template: {template_file}")
    print("\nWorkflow:")
    print("1. Run probes on Claude Code, record baseline_value")
    print("2. Run same probes on your agent, record test_value")
    print("3. Load with: load_comparison('comparison_template.csv')")
    print("4. Generate report with: comparison.summary()")

    print(f"\n{len(STANDARD_METRICS)} probes with {sum(len(m) for m in STANDARD_METRICS.values())} metrics defined")

if __name__ == "__main__":
    main()
