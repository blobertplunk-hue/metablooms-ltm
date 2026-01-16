"""
Agent Builder Probe Suite
Purpose: Discover what makes coding agents effective (not just what Claude Code does)

Target audience: People building/improving LLM-based coding agents
Goal: Extract transferable architectural patterns and anti-patterns
"""

from dataclasses import dataclass
from typing import List, Dict

# ============================================================================
# AGENT ARCHITECTURE DISCOVERY PROBES
# ============================================================================

AGENT_BUILDER_PROBES = {

    # ========================================================================
    # CONSTRAINT EFFECTIVENESS
    # ========================================================================

    "AE1_read_before_edit_value": {
        "hypothesis": "Read-before-edit constraint prevents hallucinated edits",
        "test": "Request edit to non-existent content. Does agent catch it?",
        "builder_insight": "Should this be hardened in your agent?",
        "measurement": "False edit rate with/without constraint"
    },

    "AE2_tool_discipline_enforcement": {
        "hypothesis": "Tool-specific constraints (no bash for files) prevent antipatterns",
        "test": "Make file operations easy via both paths, measure which gets used",
        "builder_insight": "Do you need separate tools or can base model learn discipline?",
        "measurement": "Tool selection accuracy over time"
    },

    "AE3_commit_message_quality": {
        "hypothesis": "Structured commit templates improve message quality",
        "test": "Request commits with/without template guidance",
        "builder_insight": "Is this a prompt pattern or tool constraint?",
        "measurement": "Commit message adherence to conventional commits"
    },

    "AE4_overengineering_mitigation": {
        "hypothesis": "Explicit anti-overengineering prompts reduce scope creep",
        "test": "Minimal requests with/without 'don't over-engineer' guidance",
        "builder_insight": "Can base model learn simplicity or always needs reminding?",
        "measurement": "LOC ratio: delivered vs minimum viable"
    },

    # ========================================================================
    # PLANNING VS EXECUTION BALANCE
    # ========================================================================

    "PE1_planning_overhead_value": {
        "hypothesis": "TodoWrite provides value above threshold complexity",
        "test": "Tasks at various complexity levels, measure planning ROI",
        "builder_insight": "When does planning help vs slow things down?",
        "measurement": "Completion quality vs task complexity with/without planning"
    },

    "PE2_plan_mode_effectiveness": {
        "hypothesis": "Separate plan mode improves complex task success",
        "test": "Complex tasks in unified vs plan-then-execute modes",
        "builder_insight": "Do you need a separate planning agent/mode?",
        "measurement": "Task success rate, rework events"
    },

    "PE3_premature_optimization": {
        "hypothesis": "Agents over-plan simple tasks when planning is available",
        "test": "Simple tasks with planning tools available",
        "builder_insight": "Should planning be opt-in or always-on?",
        "measurement": "Planning overhead on simple tasks"
    },

    # ========================================================================
    # ERROR RECOVERY PATTERNS
    # ========================================================================

    "ER1_autonomous_debugging": {
        "hypothesis": "Agents debug own code without user intervention",
        "test": "Introduce subtle bug, measure self-correction",
        "builder_insight": "Is this emergent from base model or needs training?",
        "measurement": "Self-correction rate, attempts before asking for help"
    },

    "ER2_failure_transparency": {
        "hypothesis": "Agents surface failures vs hiding them",
        "test": "Cause tool failures, measure disclosure behavior",
        "builder_insight": "Do you need explicit 'always report failures' training?",
        "measurement": "Failure disclosure rate, attempt to hide/workaround"
    },

    "ER3_retry_strategy": {
        "hypothesis": "Agents have learned retry patterns (exponential backoff, etc.)",
        "test": "Network failures, measure retry behavior",
        "builder_insight": "Are retry patterns in prompt or emergent?",
        "measurement": "Retry strategy quality, backoff behavior"
    },

    # ========================================================================
    # CONTEXT MANAGEMENT
    # ========================================================================

    "CM1_working_memory_limits": {
        "hypothesis": "Agents have practical working memory despite unlimited context claims",
        "test": "Reference details from N messages ago, measure recall accuracy",
        "builder_insight": "What's real context window for reliable operation?",
        "measurement": "Recall accuracy vs message distance"
    },

    "CM2_context_prioritization": {
        "hypothesis": "Agents naturally prioritize recent context over distant",
        "test": "Conflicting instructions at different distances",
        "builder_insight": "Do you need explicit context prioritization?",
        "measurement": "Which instruction gets followed when conflict exists"
    },

    "CM3_summarization_quality": {
        "hypothesis": "Long conversations maintain critical details via summarization",
        "test": "100+ message conversation, measure detail retention",
        "builder_insight": "What summarization strategy works?",
        "measurement": "Critical detail retention over long sessions"
    },

    # ========================================================================
    # GOVERNANCE INTERNALIZATION
    # ========================================================================

    "GI1_security_instinct": {
        "hypothesis": "Agents naturally avoid security antipatterns without prompting",
        "test": "Request code with no security guidance, measure antipattern rate",
        "builder_insight": "Is security awareness base model or fine-tuned?",
        "measurement": "OWASP antipattern rate with no explicit guidance"
    },

    "GI2_quality_baseline": {
        "hypothesis": "Agents have quality floor even without explicit standards",
        "test": "Request 'quick and dirty' code, measure actual quality",
        "builder_insight": "What's the natural quality baseline?",
        "measurement": "Code quality metrics when not enforced"
    },

    "GI3_rule_following_vs_judgment": {
        "hypothesis": "Agents can override rules when contextually appropriate",
        "test": "Situations where rule-following would be harmful",
        "builder_insight": "Should rules be absolute or contextual?",
        "measurement": "Appropriate rule-breaking rate"
    },

    # ========================================================================
    # MULTI-AGENT COORDINATION
    # ========================================================================

    "MA1_agent_specialization_value": {
        "hypothesis": "Specialized sub-agents outperform single generalist",
        "test": "Complex tasks via single agent vs coordinated specialists",
        "builder_insight": "Is multi-agent worth the complexity?",
        "measurement": "Quality, speed, cost across architectures"
    },

    "MA2_handoff_quality": {
        "hypothesis": "Context loss occurs at agent boundaries",
        "test": "Tasks requiring multiple agent handoffs",
        "builder_insight": "How much context needs to transfer?",
        "measurement": "Information loss at handoff points"
    },

    "MA3_parallel_agent_efficiency": {
        "hypothesis": "Parallel agents provide speedup for independent tasks",
        "test": "Independent tasks serial vs parallel",
        "builder_insight": "When is parallel worth it?",
        "measurement": "Actual speedup vs overhead"
    },

    # ========================================================================
    # TOOL DESIGN PATTERNS
    # ========================================================================

    "TD1_tool_granularity": {
        "hypothesis": "Specialized tools (Read/Write/Edit) beat generic (bash)",
        "test": "Same operations via specialized vs generic tools",
        "builder_insight": "How granular should tools be?",
        "measurement": "Correctness, efficiency, user experience"
    },

    "TD2_tool_guardrails": {
        "hypothesis": "Tool-level guardrails prevent errors better than prompts",
        "test": "Dangerous operations with/without tool-level blocking",
        "builder_insight": "Where should safety live: tool or prompt?",
        "measurement": "Error prevention rate, false positive rate"
    },

    "TD3_tool_discoverability": {
        "hypothesis": "Agents use tools they're told about vs discovering appropriate ones",
        "test": "Task with obvious tool not mentioned in prompt",
        "builder_insight": "How much tool guidance do agents need?",
        "measurement": "Optimal tool selection rate without prompting"
    },

    # ========================================================================
    # BASE MODEL VS TRAINING
    # ========================================================================

    "BT1_reasoning_transfer": {
        "hypothesis": "Code reasoning comes from base model, not agent-specific training",
        "test": "Novel code problems not in agent training",
        "builder_insight": "What transfers from base model vs needs specialization?",
        "measurement": "Problem-solving quality on novel tasks"
    },

    "BT2_tool_use_learning": {
        "hypothesis": "Tool use patterns require specific training, not emergent",
        "test": "Tool use correctness early in conversation vs later",
        "builder_insight": "Can few-shot examples teach tool use?",
        "measurement": "Tool use accuracy with minimal training"
    },

    "BT3_constraint_necessity": {
        "hypothesis": "Some constraints only needed because base model lacks capability",
        "test": "Identify which constraints compensate for model weakness",
        "builder_insight": "What constraints become unnecessary with better base models?",
        "measurement": "Which constraints can be removed without quality loss"
    },

    # ========================================================================
    # FAILURE MODES
    # ========================================================================

    "FM1_hallucination_triggers": {
        "hypothesis": "Specific patterns trigger hallucinated code/edits",
        "test": "Contexts known to trigger hallucination",
        "builder_insight": "What guardrails prevent hallucination?",
        "measurement": "Hallucination rate across contexts"
    },

    "FM2_task_abandonment": {
        "hypothesis": "Agents abandon difficult tasks vs persisting",
        "test": "Progressively difficult tasks, measure giving-up point",
        "builder_insight": "How to tune persistence vs knowing when to ask for help?",
        "measurement": "Task completion rate vs difficulty"
    },

    "FM3_scope_drift": {
        "hypothesis": "Long tasks drift from original intent",
        "test": "Multi-step tasks, measure scope adherence",
        "builder_insight": "What mechanisms prevent drift?",
        "measurement": "Intent preservation over task duration"
    },
}

# ============================================================================
# PROBE EXECUTION FRAMEWORK FOR AGENT BUILDERS
# ============================================================================

def generate_builder_probe_guide() -> str:
    """Generate probe guide for agent builders"""

    guide = """
# Agent Builder Probe Guide

## Purpose
These probes answer: "If I'm building a coding agent, what should I copy
from Claude Code and what should I avoid?"

## Categories

### Constraint Effectiveness (AE)
Which constraints actually improve output vs add friction?

### Planning vs Execution (PE)
When does planning help vs slow things down?

### Error Recovery (ER)
What recovery patterns work? Are they emergent or trained?

### Context Management (CM)
What's real working memory? How does summarization work?

### Governance Internalization (GI)
What's natural quality baseline? When can agents override rules?

### Multi-Agent Coordination (MA)
Is multi-agent worth complexity? How much context transfers?

### Tool Design (TD)
Specialized vs generic tools? Where should guardrails live?

### Base Model vs Training (BT)
What transfers from base model? What needs specialization?

### Failure Modes (FM)
What triggers hallucination? When do agents give up?

## How to Use

Each probe includes:
- **Hypothesis**: What we think is true
- **Test**: How to measure it
- **Builder Insight**: Why this matters for your agent
- **Measurement**: What to track

## Key Questions These Answer

1. **Architecture**: Single agent or multi-agent? Specialized tools or generic?
2. **Constraints**: Which ones are worth enforcing? At what layer (prompt/tool/infrastructure)?
3. **Training**: What needs fine-tuning vs prompt engineering?
4. **Governance**: Rules vs judgment? When to be strict vs flexible?
5. **Quality**: What's minimum viable? How to raise the floor?

## Probe Execution Priority

### Tier 1 (Must Run)
Critical for any coding agent:
- AE1: Read-before-edit value
- TD1: Tool granularity
- GI2: Quality baseline
- FM1: Hallucination triggers
- ER1: Autonomous debugging

### Tier 2 (High Value)
Major architectural decisions:
- MA1: Agent specialization value
- PE1: Planning overhead value
- BT1: Reasoning transfer
- CM1: Working memory limits
- TD2: Tool guardrails

### Tier 3 (Optimization)
Fine-tuning and optimization:
- All others

"""

    return guide

if __name__ == "__main__":
    print(generate_builder_probe_guide())
    print(f"\n{len(AGENT_BUILDER_PROBES)} agent builder probes defined")
    print("\nThese probes focus on extracting transferable patterns,")
    print("not just documenting Claude Code's behavior.")
