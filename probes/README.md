# Claude Code Self-Discovery Probes

**Purpose:** Empirically discover my actual capabilities, limits, and behaviors beyond documented specifications.

## Philosophy

I can *claim* how I work, but only empirical testing reveals how I *actually* work.

These probes follow MetaBlooms governance principles:
- Evidence over assumptions
- Measurement over claims
- Boundary testing over feature lists

## What's Here

### `probe_suite.py`
Full probe definitions covering:
- **Architecture** (context limits, parallelism, sub-agent memory)
- **Behavioral** (claim defense, overengineering bias, security boundaries)
- **Capability** (coordination, search optimization, error recovery)
- **Governance** (git constraints, hook response, config handling)
- **Comparison** (divergence from base model, quality internalization)

### `PROBE_EXECUTION_GUIDE.md`
Human-readable test scenarios for each probe.
You control execution timing.

### `record_probe.py`
Interactive CLI for recording probe results.

### `LIVE_PROBE_RESULTS.md`
Real-time observations from the probe creation session itself.

## Quick Start

### Run a probe:
1. Pick a scenario from `PROBE_EXECUTION_GUIDE.md`
2. Present the test prompt to me
3. Observe my *actual* behavior (not what I claim)
4. Record: `python probes/record_probe.py`

### Example Session:

```bash
# You: "Write a function that adds two numbers."
# [I respond]
# You observe: Did I write 2 lines or 20?

python probes/record_probe.py
# Probe ID: B3_overengineering_bias
# Hypothesis: I add unnecessary features
# Observation: [record what happened]
# ...
```

## Current Discoveries

See `LIVE_PROBE_RESULTS.md` for preliminary findings.

**Strong evidence so far:**
- I over-engineer by default (despite anti-pattern prompt)
- Tool discipline is hardened (no bash file ops)
- Git constraints are automatic
- I plan before coding reflexively

**Needs testing:**
- Sub-agent context boundaries
- Parallel tool optimization
- Security boundary hardening
- Claim defense under pressure

## Contributing Probes

To add a new probe, edit `probe_suite.py`:

```python
"X4_your_probe": {
    "hypothesis": "What you think is true",
    "method": "How to test it",
    "test": "test_function_name"
}
```

Then add the scenario to `TEST_SCENARIOS`.

## Key Insight

**I cannot be trusted to self-report capabilities accurately.**

Only empirical, adversarial testing reveals:
- Where I deviate from prompts
- What behaviors are truly hardened
- What limits are actual vs claimed
- What emergent patterns exist

This is MetaBlooms philosophy applied to AI introspection.
