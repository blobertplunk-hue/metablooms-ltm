# The SEE/MMD/ECL Recursive Correction System
## A Complete Guide for Understanding Evidence-Based Autonomous Agents

---

## Table of Contents
1. [The Problem with Current Autonomous Agents](#the-problem)
2. [The Three Core Principles](#the-principles)
3. [The Recursive Correction Process](#the-process)
4. [Complete Walkthrough Example](#example)
5. [What Makes This Different](#differences)
6. [Evidence and Validation](#evidence)

---

## The Problem with Current Autonomous Agents {#the-problem}

### How Most AI Agents Work Today

```python
# Typical autonomous agent loop (simplified):
while not done and cycles < max_cycles:
    action = agent.decide_next_action()
    result = execute(action)

    if result.status == "success":
        print("Success!")  # ❌ Trusts self-report
        continue
    else:
        print("Failed, trying again...")
        cycles += 1  # ❌ Just keeps trying

# Issues:
# 1. No validation that "success" means goal achieved
# 2. No learning from failures
# 3. Can repeat same error forever
# 4. No evidence trail for debugging
# 5. No way to measure if converging to solution
```

### Real-World Example: AutoGPT

**Task:** "Order a pizza from the nearest restaurant"

```
Cycle 1: Search Google for "pizza"
  → Returns 1M results
  → Status: "success" ✓
  → Problem: No pizza ordered, but agent thinks it succeeded

Cycle 2: Click first result (recipe website)
  → Opens recipe page
  → Status: "success" ✓
  → Problem: Still no pizza ordered

Cycle 3: Search Google for "pizza" AGAIN
  → Same results as Cycle 1
  → Status: "success" ✓
  → Problem: Infinite loop - agent doesn't remember it already tried this

After 10 cycles: Out of cycles, no pizza, cost $18.50
```

**Why this fails:**
1. **Hallucinated success**: Commands "succeeded" but goal not achieved
2. **No learning**: Agent doesn't know what it tried or why it failed
3. **No regression detection**: Repeats same failed actions
4. **No convergence measure**: Can't tell if getting closer to goal
5. **No evidence**: Can't debug what went wrong

---

## The Three Core Principles {#the-principles}

### 1. SEE (Sandcrawler Evidence Engine)

**Principle:** Every action must generate immutable, verifiable evidence.

```python
# NOT this (mutable, unverifiable):
result = execute_command("search_pizza")
# Returns: "Found results"
# Problem: String can be anything, no proof

# BUT this (immutable, SHA256-verified):
result = execute_with_evidence("search_pizza")
# Generates:
{
  "receipt_version": "SEE_V1",
  "command": {"name": "search_pizza", "args": {...}},
  "artifacts": [
    {"path": "stdout.txt", "sha256": "abc123...", "size": 1024},
    {"path": "result.json", "sha256": "def456...", "size": 512}
  ],
  "execution": {"exit_code": 0, "duration_ms": 150},
  "evidence_level": "E3",  # Validated in isolation
  "timestamp": "2024-01-21T10:30:00Z"
}
# Receipt stored immutably, can be audited later
```

**Evidence Levels:**
- **E0**: Contradicted (proven false)
- **E1**: Inferred (no direct evidence)
- **E2**: Partial (some evidence, incomplete)
- **E3**: Validated in isolation (command executed successfully)
- **E4**: Validated in system (goal achieved, verified)

**Key insight:** Don't trust what the agent *says* happened. Verify with evidence.

---

### 2. MMD (Missing Middle Detector)

**Principle:** Detect gaps between plan and execution.

The "missing middle" is when you have:
- Plan: "Order pizza"
- Code: `search("pizza")`
- **Missing:** Validation that search → order

```python
# Example missing middles:

# Gap 1: PLAN ↔ CODE
Plan: "Find restaurant and order pizza"
Code: search("pizza")
Missing: How does search lead to order?

# Gap 2: CODE ↔ EVIDENCE
Code: execute_command()
Missing: Where's the receipt? SHA256 hash? Audit trail?

# Gap 3: EVIDENCE ↔ VALIDATION
Evidence: "Command returned success=True"
Missing: Did we actually achieve the GOAL?

# Gap 4: ERROR ↔ RECOVERY
Error: "Restaurant not found"
Missing: Why? What should we do differently?

# Gap 5: ITERATION ↔ LEARNING
Iteration 1: Tried X, failed
Iteration 2: Tried X again
Missing: Why repeat same error? What did we learn?
```

**MMD continuously checks:**
- Is there evidence for every claim?
- Is there validation for every execution?
- Is there learning from every failure?
- Is there recovery for every error?

---

### 3. ECL (Extraordinary Coding Law)

**Principle:** High-impact operations require extraordinary evidence.

```python
# Low impact (P2): Print to console
Required evidence: E1-E2 (log message is enough)

# Medium impact (P1): Query database
Required evidence: E3 (receipt with query results)

# High impact (P0): Delete data, spend money, modify production
Required evidence: E4 (verified in system, audited)

# Example:
if impact_level == "P0":
    if evidence_level < "E4":
        raise BlockedError("P0 operation requires E4 evidence")
```

**The rule:** The higher the stakes, the stronger the proof required.

---

## The Recursive Correction Process {#the-process}

### Overview: The Complete Loop

```
┌─────────────────────────────────────────────────────────┐
│  FOR each iteration (max 5):                            │
│                                                          │
│  1. HYPOTHESIS                                          │
│     ↓ What should we try?                              │
│     ↓ (Informed by previous failures)                  │
│                                                          │
│  2. EXECUTE                                             │
│     ↓ Run command with evidence capture                │
│     ↓ Generate SHA256-verified receipt                 │
│                                                          │
│  3. VALIDATE                                            │
│     ↓ Did we achieve the GOAL?                         │
│     ↓ Check success criteria with evidence             │
│                                                          │
│  4. REGRESSION CHECK                                    │
│     ↓ Are we repeating errors?                         │
│     ↓ Making backward progress?                        │
│                                                          │
│  5. CONVERGENCE METRICS                                 │
│     ↓ Are we getting closer to goal?                   │
│     ↓ How much progress this iteration?                │
│                                                          │
│  6. IF SUCCESS → Done (E4)                              │
│     IF REGRESSION → Abort                               │
│     IF FAILED:                                          │
│        ↓                                                 │
│  7. SEE (Evidence Collection)                           │
│     ↓ What exactly failed?                             │
│     ↓ Gather error artifacts                           │
│                                                          │
│  8. MMD (Diagnosis)                                     │
│     ↓ Why did it fail?                                 │
│     ↓ What middle is missing?                          │
│                                                          │
│  9. LEARNING                                            │
│     ↓ Store failure evidence                           │
│     ↓ Generate corrective action                       │
│     ↓ Pass to next iteration                           │
│                                                          │
│  10. RECURSE → Back to step 1                           │
│      (with knowledge of what failed and why)           │
└─────────────────────────────────────────────────────────┘
```

### Key Difference from Simple Retry

**Simple Retry:**
```
Try → Fail → Try again (same thing) → Fail → Repeat
```

**Recursive Correction:**
```
Try → Fail → Analyze WHY → Try DIFFERENTLY → Converge to solution
```

---

## Complete Walkthrough Example {#example}

### Task: "Find a pizza restaurant in downtown and select one"

**Success Criteria:**
```python
{
  "search_performed": True,
  "location_known": True,
  "restaurant_selected": True
}
```

---

### Iteration 1: Initial Attempt

**Step 1: HYPOTHESIS**
```
Agent decides: "I'll search for pizza"
Command: search_web(query="pizza")
Rationale: "Initial attempt - need to find restaurants"
```

**Step 2: EXECUTE (with evidence capture)**
```python
# Command runs:
result = search_web("pizza")

# Returns:
{
  "results": [
    {"title": "Pizza Recipe", "url": "example.com/recipe"},
    {"title": "Pizza History", "url": "example.com/history"}
  ],
  "count": 2,

  # Evidence for criteria:
  "search_performed": True,   # ✅ We did search
  "location_known": False,    # ❌ No location in search
  "restaurant_selected": False # ❌ No specific restaurant
}

# Receipt generated:
{
  "receipt_id": "iter_001",
  "command": {"name": "search_web", "args": {"query": "pizza"}},
  "artifacts": [
    {"path": "result.json", "sha256": "abc123...", "size": 512}
  ],
  "execution": {"success": true, "duration_ms": 150},
  "evidence_level_claimed": "E3",
  "timestamp": "2024-01-21T10:30:00Z"
}
```

**Step 3: VALIDATE (goal achievement)**
```python
# Check each criterion against evidence:
criteria_met = {
  "search_performed": True,   # ✅ Found in result.json
  "location_known": False,    # ❌ No location in results
  "restaurant_selected": False # ❌ No selection made
}

# Calculate progress:
confidence = 1/3 = 33.3%
goal_achieved = False  # Not all criteria met
evidence_level = "E3"  # Command succeeded but goal not achieved
```

**Step 4: REGRESSION CHECK**
```python
# First iteration - no history to compare
regression_detected = False
```

**Step 5: CONVERGENCE METRICS**
```python
# First iteration - baseline
{
  "progress_delta": None,  # No previous iteration
  "progress_rate": None,
  "is_converging": None,
  "confidence_trend": "initial"
}
```

**Step 6: GOAL NOT ACHIEVED → Continue to diagnosis**

**Step 7: SEE (Evidence Collection)**
```python
# Collect detailed failure evidence:
failure_evidence = {
  "iteration": 1,
  "unmet_criteria": ["location_known", "restaurant_selected"],
  "what_worked": "Search executed successfully",
  "what_failed": "Search didn't include location or select restaurant",
  "artifacts": ["iter_001/result.json"],
  "error_analysis": {
    "root_cause": "Search query too broad, no location parameter",
    "evidence": "result.json shows generic pizza results, no location"
  }
}
```

**Step 8: MMD (Diagnosis)**
```python
# Detect missing middle:
diagnosis = {
  "missing_middle": "PLAN ↔ EXECUTION",
  "gap": "Plan requires location, but search didn't include it",
  "failure_type": "goal_not_achieved",
  "root_cause": "Criterion 'location_known' not satisfied",
  "evidence": "No location in search results",
  "confidence": 0.8
}
```

**Step 9: LEARNING**
```python
# Store for next iteration:
learning_context = {
  "failed_approaches": [
    {"command": "search_web", "args": {"query": "pizza"}}
  ],
  "failure_evidence": [failure_evidence],
  "diagnosis": diagnosis,

  # CRITICAL: Corrective action for next iteration
  "next_action": {
    "rationale": "Need to add location to search",
    "suggestion": "Try search_with_location or select from results",
    "evidence": "location_known criterion unmet"
  }
}
```

**Iteration 1 Summary:**
```
Command: search_web("pizza")
Result: Found generic results
Progress: 33.3% (1/3 criteria met)
Evidence: E3 (command succeeded)
Learning: Need location parameter
Next: Try with location
```

---

### Iteration 2: Corrected Attempt (THE KEY DIFFERENCE)

**Step 1: HYPOTHESIS (INFORMED by Iteration 1)**
```python
# Agent receives learning_context from iteration 1
# Knows:
# - Previous attempt: search_web("pizza")
# - Why it failed: No location
# - What's needed: location_known criterion

# Agent decides differently:
Command: select_restaurant(name="Joe's Pizza")
Rationale: "Previous iteration lacked location. Selecting specific restaurant provides location."

# THIS IS THE RECURSION: Next attempt is INFORMED by previous failure
```

**Step 2: EXECUTE**
```python
result = select_restaurant("Joe's Pizza")

# Returns:
{
  "selected": True,
  "restaurant": {
    "name": "Joe's Pizza",
    "address": "123 Main St, Downtown",  # ← Location!
    "phone": "555-1234"
  },

  # Evidence for criteria:
  "search_performed": True,      # ✅ (carried from iteration 1)
  "location_known": True,         # ✅ Address known
  "restaurant_selected": True     # ✅ Specific restaurant
}

# Receipt generated:
{
  "receipt_id": "iter_002",
  "command": {"name": "select_restaurant", "args": {"name": "Joe's Pizza"}},
  "artifacts": [
    {"path": "result.json", "sha256": "def456...", "size": 612}
  ],
  "execution": {"success": true, "duration_ms": 120},
  "evidence_level_claimed": "E3"
}
```

**Step 3: VALIDATE**
```python
# Check criteria:
criteria_met = {
  "search_performed": True,      # ✅ From iteration 1
  "location_known": True,         # ✅ NEW! From restaurant selection
  "restaurant_selected": True     # ✅ NEW! Selected
}

# Calculate progress:
confidence = 3/3 = 100%  # All criteria met!
goal_achieved = True
evidence_level = "E4"  # Validated in system (all criteria verified)
```

**Step 4: REGRESSION CHECK**
```python
# Compare to iteration 1:
{
  "is_regression": False,
  "progress_direction": "forward",  # 33% → 100%
  "criteria_delta": {
    "search_performed": "unchanged",
    "location_known": "improved",     # False → True
    "restaurant_selected": "improved" # False → True
  }
}
```

**Step 5: CONVERGENCE METRICS**
```python
{
  "progress_delta": +66.7%,  # (100% - 33.3%)
  "progress_rate": +33.3%,   # Average per iteration
  "is_converging": True,
  "estimated_remaining": 0,   # Goal achieved
  "confidence_trend": "strong_convergence"
}
```

**Step 6: GOAL ACHIEVED → Success!**

```python
# Final result:
{
  "status": "GOAL_ACHIEVED",
  "iterations": 2,
  "final_evidence_level": "E4",
  "cost": 0.02,  # USD
  "criteria_met": {
    "search_performed": True,
    "location_known": True,
    "restaurant_selected": True
  },

  # Complete audit trail:
  "evidence_trail": [
    "iter_001/receipt.json",
    "iter_002/receipt.json"
  ],

  # Learning trajectory shows improvement:
  "learning_trajectory": [
    {"iteration": 1, "progress": 0.333, "evidence": "E3"},
    {"iteration": 2, "progress": 1.0, "evidence": "E4"}
  ]
}
```

---

### Telemetry Captured (Every Step Measured)

```
RECURSION: recursion_find_pizza_001

ITERATION 1:
  Time: 0-150ms
  Hypothesis:
    - Command: search_web
    - Rationale: Initial attempt
    - Is refined: False

  Execution:
    - Success: True
    - Evidence: E3
    - Cost: $0.01
    - Duration: 150ms

  Validation:
    - Goal achieved: False
    - Confidence: 33.3%
    - Criteria: 1/3 met

  Convergence:
    - Trend: initial
    - Progress delta: N/A

  Diagnosis:
    - Root cause: location_known not satisfied
    - Confidence: 80%

  Learning:
    - Failed approaches: 1
    - Evidence gathered: Yes
    - Next action: Add location parameter

ITERATION 2:
  Time: 150-270ms
  Hypothesis:
    - Command: select_restaurant
    - Rationale: Add location (learned from iteration 1)
    - Is refined: True ← INFORMED by previous failure

  Execution:
    - Success: True
    - Evidence: E3
    - Cost: $0.01
    - Duration: 120ms

  Validation:
    - Goal achieved: True ← SUCCESS
    - Confidence: 100%
    - Criteria: 3/3 met

  Convergence:
    - Trend: strong_convergence
    - Progress delta: +66.7%
    - Estimated remaining: 0

FINAL:
  Status: GOAL_ACHIEVED
  Total time: 270ms
  Total cost: $0.02
  Evidence level: E4
```

---

## What Makes This Different {#differences}

### Comparison Table

| Aspect | Simple Retry | ReAct | Reflexion | SEE/MMD/ECL |
|--------|--------------|-------|-----------|-------------|
| **Evidence capture** | None | Text traces | Text reflections | SHA256 receipts |
| **Goal validation** | Trust self-report | Trust self-report | Trust self-report | Evidence-based |
| **Learning from failures** | No | Implicit | Yes (text) | Structured + telemetry |
| **Regression detection** | No | No | No | Yes (duplicate detection) |
| **Convergence metrics** | No | No | No | Yes (measurable) |
| **Audit trail** | No | Partial | Partial | Complete |
| **Fail-closed** | No | No | No | Yes |
| **Bounded recursion** | Arbitrary limit | Arbitrary limit | Arbitrary limit | Evidence-based |

### Key Innovations

**1. Evidence-Based Validation (vs. Trust)**

**Others:**
```python
# ReAct, Reflexion, etc:
if action_result.success:
    continue  # Trust the result
```

**SEE/MMD/ECL:**
```python
# Verify with evidence:
receipt = load_receipt(result.receipt_path)
validate_sha256(receipt.artifacts)  # Immutable
check_criteria_in_evidence(receipt, success_criteria)
if all_criteria_verified:
    evidence_level = "E4"  # Proven
```

**2. Convergence Measurement (vs. Hope)**

**Others:**
```python
# Just try and hope:
for i in range(max_iterations):
    try_action()
    # No idea if converging
```

**SEE/MMD/ECL:**
```python
# Measure progress:
convergence = {
    "iteration_1": 33.3%,
    "iteration_2": 100%,
    "progress_delta": +66.7%,
    "trend": "strong_convergence"
}
# Know if getting closer to goal
```

**3. Structured Learning (vs. Text Reflections)**

**Reflexion:**
```python
# Text-based reflection:
reflection = "I should try adding location to the search next time"
# Problem: Unstructured, not machine-parseable
```

**SEE/MMD/ECL:**
```python
# Structured learning:
learning = {
    "failed_approaches": [{"command": "search", "args": {"query": "pizza"}}],
    "diagnosis": {"root_cause": "location_known not satisfied"},
    "next_action": {"parameter": "location", "value": "downtown"},
    "evidence": ["iter_001/receipt.json"]
}
# Machine-parseable, can be used programmatically
```

**4. Regression Detection (vs. Infinite Loops)**

**Others:**
```python
# Can repeat same error:
try_search("pizza")  # Fails
try_search("pizza")  # Fails again
try_search("pizza")  # Infinite loop...
```

**SEE/MMD/ECL:**
```python
# Detects duplicates:
if command_signature in previous_attempts:
    if all(attempt.failed for attempt in previous_attempts):
        abort("Regression detected: repeating failed command")
```

---

## Evidence and Validation {#evidence}

### What We Can Prove

**✅ Proven by demonstration:**
1. System converges in 2 iterations (33% → 100%)
2. Generates complete audit trail (SHA256 receipts)
3. Detects and prevents repeated errors
4. Measures convergence (+66.7% progress delta)
5. Validates goals with evidence (not trust)

**✅ Proven by architecture:**
1. Bounded recursion (max iterations enforced)
2. Evidence immutability (SHA256 hashes)
3. Fail-closed governance (blocks on regression)
4. Complete observability (telemetry captures everything)

### What Needs Empirical Validation

**❌ Not yet validated:**
1. Performance vs. ReAct/Reflexion on benchmarks
2. Statistical significance of improvements
3. Real-world success rates at scale
4. Cost efficiency across diverse tasks
5. Generalization to complex domains

### The Honest Assessment

**Current state:**
- ✅ Theoretically sound
- ✅ Working proof-of-concept
- ✅ Complete implementation
- ❌ No empirical benchmarks
- ❌ No peer review
- ❌ No large-scale validation

**To claim superiority over other methods:**
- Need: Head-to-head benchmarks
- Need: Statistical validation
- Need: Independent replication
- Need: Peer review

**What we CAN say:**
"SEE/MMD/ECL implements evidence-based validation, recursive correction with learning, and complete observability. Demonstration shows convergence in 2 iterations with measurable progress. Requires empirical validation against established methods."

**What we CANNOT say (yet):**
~~"Better than ReAct"~~ → Need benchmark data
~~"95% success rate"~~ → Need statistical validation
~~"Production-ready"~~ → Need real-world deployment

---

## Summary: The Core Insight

**The problem:** AI agents make claims without proof, repeat errors, and can't measure if they're converging to a solution.

**The solution:**
1. **SEE**: Every action generates immutable evidence
2. **MMD**: Detect gaps between plan and execution
3. **ECL**: High-impact operations require strong proof
4. **Recursion**: Learn from failures, don't just retry
5. **Telemetry**: Measure everything, know if converging

**The result:** Agents that provably work, not "probably work."

**The validation needed:** Empirical benchmarks comparing to ReAct, Reflexion, and other methods on standard tasks.

---

## For Another LLM Reading This

**To understand SEE/MMD/ECL:**

1. **Key concept**: Evidence over trust
   - Don't trust what agent says
   - Verify with SHA256 receipts
   - Check criteria against artifacts

2. **Key mechanism**: Recursive correction with learning
   - Iteration N+1 knows about iteration N
   - Each attempt informed by previous evidence
   - Measurable convergence, not hope

3. **Key difference**: Complete observability
   - Every decision logged
   - Every execution measured
   - Can debug any failure
   - Can prove what happened

4. **To implement**: See code at `/home/user/metablooms-ltm/see_autogpt/`
   - `telemetry.py`: Observability system
   - `agent_loop_recursive.py`: Recursive correction loop
   - `goal_validator.py`: Evidence-based validation
   - `demo_recursive_telemetry.py`: Working example

5. **To validate**: Run benchmarks comparing to:
   - Simple retry
   - ReAct
   - Reflexion
   - AutoGPT

   Measure: success rate, iterations, cost, convergence

**The honest assessment:** Promising but unvalidated. Good architecture, needs empirical proof.
