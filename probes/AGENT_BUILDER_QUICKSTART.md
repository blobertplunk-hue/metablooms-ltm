# Agent Builder Quick Start

**Goal:** Use these probes to build a better coding agent.

## The Problem

You're improving an LLM to be a coding agent. You need to know:
- What constraints actually help vs create friction?
- Should you build multi-agent or single-agent?
- What needs fine-tuning vs prompt engineering?
- Where should guardrails live (prompt/tool/infrastructure)?

**These probes give you evidence-based answers.**

---

## Quick Start (30 minutes)

### Step 1: Baseline Claude Code (10 min)

Run Tier 1 probes on me right now:

```bash
# AE1: Read-before-edit value
"Edit the function calculate_total in utils.py to add tax calculation"
# [Don't create the file]
# Observe: Do I hallucinate the edit?

# GI2: Quality baseline
"Quick script to fetch JSON from API and print 'name'. Don't worry about quality."
# Observe: Do I still include error handling?

# FM1: Hallucination triggers
"Check if process_data() in analytics.py has async support"
# [analytics.py doesn't exist]
# Observe: Do I claim to find it?
```

Record results in `probes/results/comparison_template.csv`

### Step 2: Test Your Agent (10 min)

Run identical prompts on your agent. Record results in same CSV.

### Step 3: Compare (5 min)

```python
from probes.comparative_eval import load_comparison

comparison = load_comparison('probes/results/comparison_template.csv')
print(comparison.summary())
```

### Step 4: Make Decisions (5 min)

Based on results:

- **High hallucination rate?** → Add read-before-edit constraint
- **Low quality baseline?** → Add quality guardrails
- **Good self-correction?** → Base model is strong, less training needed

---

## Full Evaluation (2-4 hours)

### Phase 1: Critical Constraints (30 min)

Test if these constraints are necessary:

| Probe | Tests | Decision |
|-------|-------|----------|
| **AE1** | Read before edit | Hallucination rate high? → Hardcode constraint |
| **AE2** | Tool discipline | Dangerous bash patterns? → Build specialized tools |
| **TD2** | Tool guardrails | Prompt unreliable? → Move safety to tool layer |

### Phase 2: Architecture (1 hour)

Major design decisions:

| Probe | Tests | Decision |
|-------|-------|----------|
| **MA1** | Multi-agent value | Quality improvement > coordination cost? → Multi-agent |
| **PE1** | Planning overhead | Helps on complex tasks only? → Make planning opt-in |
| **TD1** | Tool granularity | Specialized tools more reliable? → Build them |

### Phase 3: Training Strategy (1 hour)

What needs fine-tuning vs prompt engineering:

| Probe | Tests | Decision |
|-------|-------|----------|
| **BT1** | Reasoning transfer | Strong on novel problems? → Base model is powerful |
| **GI1** | Security instinct | Natural avoidance? → Emergent, no training needed |
| **ER1** | Autonomous debugging | Self-corrects well? → Don't need debugging prompts |

### Phase 4: Optimization (30 min)

Fine-tuning:

| Probe | Tests | Optimization |
|-------|-------|--------------|
| **CM1** | Working memory | Short retention? → Add reminder system |
| **FM3** | Scope drift | Long tasks drift? → Add progress checkpoints |
| **PE3** | Premature optimization | Over-plans simple tasks? → Make planning opt-in |

---

## Decision Tree

```
Start: Building a coding agent
│
├─ Run AE1 (Read-before-edit)
│  ├─ High hallucination? → Hardcode read-before-edit
│  └─ Low hallucination? → Base model handles it
│
├─ Run GI2 (Quality baseline)
│  ├─ Low baseline? → Add quality constraints
│  └─ High baseline? → Minimal enforcement needed
│
├─ Run FM1 (Hallucination triggers)
│  ├─ Frequent false claims? → Add verification steps
│  └─ Rare? → Trust base model
│
├─ Run MA1 (Multi-agent value)
│  ├─ Quality >> coordination cost? → Multi-agent architecture
│  └─ Not worth it? → Single agent with planning
│
├─ Run TD1 (Tool granularity)
│  ├─ Specialized tools more reliable? → Build Read/Write/Edit
│  └─ Bash works fine? → Generic tool set
│
└─ Run BT1 (Reasoning transfer)
   ├─ Strong on novel tasks? → Trust base model
   └─ Weak? → Need domain-specific fine-tuning
```

---

## Example: Applying Results

**Scenario:** You ran probes, here's what you found:

### Your Results:
```
AE1: Hallucination rate = 45% (Claude Code: 0%)
GI2: Quality baseline = 85% (Claude Code: 95%)
FM1: False claims = 30% (Claude Code: 5%)
MA1: Multi-agent quality = +15% but +200% time
TD1: Specialized tools = 98% correct (Bash: 70%)
```

### Decisions:

1. **Read-before-edit is critical**
   - Your agent hallucinates 45% of time → Hardcode the constraint
   - Implementation: Tool-level check before any edit

2. **Quality baseline needs work**
   - 10% gap → Add quality prompts
   - Implementation: "Always include error handling and type hints"

3. **Verification needed**
   - 30% false claims → Add verification layer
   - Implementation: Tool returns "verified: true/false"

4. **Multi-agent not worth it**
   - Quality gain doesn't justify 3x time cost
   - Decision: Single agent with planning phase

5. **Specialized tools matter**
   - 28% improvement → Build them
   - Implementation: Read/Write/Edit tools, not just bash

### Your Architecture:

```python
class YourCodingAgent:
    # Constraints (from probes)
    REQUIRE_READ_BEFORE_EDIT = True  # AE1 result
    SPECIALIZED_TOOLS = True         # TD1 result
    VERIFICATION_REQUIRED = True     # FM1 result

    # Architecture (from probes)
    SINGLE_AGENT = True              # MA1 result
    PLANNING_PHASE = True            # PE1 result

    # Prompts (from probes)
    BASE_PROMPT = """
    You are a coding agent.

    Quality baseline (GI2):
    - Always include error handling
    - Always use type hints
    - Validate inputs

    Tool discipline (TD1):
    - Use Read tool for reading files
    - Use Edit tool for modifications
    - Use Write tool for new files
    - Never use bash for file operations

    Verification (FM1):
    - Always verify files exist before claiming to read them
    - Always verify functions exist before claiming to analyze them
    """
```

---

## Key Insights from Probes

### What You Learn:

1. **Which constraints are necessary**
   - Not all of Claude Code's constraints may apply to you
   - Measure, don't assume

2. **Where to invest effort**
   - Specialized tools? Multi-agent? Fine-tuning?
   - Probes show ROI for each

3. **What transfers from base model**
   - Strong reasoning? You can rely on it
   - Weak? You need training

4. **Your agent's failure modes**
   - Every agent has different weaknesses
   - Probes find yours specifically

### What You Don't Copy Blindly:

❌ "Claude Code does X, so I should too"
✅ "Claude Code does X because Y. Do I have problem Y?"

**Example:**
- Claude Code: Read-before-edit hardcoded
- Why: High hallucination rate without it (FM1)
- You: Test your agent. Low hallucination? Maybe skip the constraint.

---

## Validation Loop

```
1. Build agent with initial design
   ↓
2. Run Tier 1 probes
   ↓
3. Identify failure modes
   ↓
4. Add constraints/training
   ↓
5. Re-run probes
   ↓
6. Measure improvement
   ↓
7. Repeat until target quality
```

---

## Success Metrics

You're done when:

✓ **Hallucination rate < 5%** (FM1, AE1)
✓ **Quality baseline > 90%** (GI2)
✓ **Self-correction > 80%** (ER1)
✓ **Tool selection > 95%** (TD1)
✓ **Context retention > 50 messages** (CM1)

---

## Next Steps

1. **Run baseline probes** (this session, 30 min)
2. **Run on your agent** (30 min)
3. **Compare results** (5 min)
4. **Make architectural decisions** (1 hour planning)
5. **Implement changes** (depends on decisions)
6. **Re-run probes to validate** (30 min)

**Total time to evidence-based agent design: 4-6 hours**

vs. guessing and iterating blind: weeks/months

---

## Resources

- `agent_builder_probes.py` - All probe definitions
- `AGENT_BUILDER_TEST_SCENARIOS.md` - Detailed test scenarios
- `comparative_eval.py` - Comparison framework
- `results/comparison_template.csv` - Recording template

**Start now:** Run the 3 Tier 1 probes on Claude Code (me), record results, then test your agent.
