# Evaluation Tiers Spec

Candidates are evaluated through a tiered pipeline.
Cheap checks first. Only survivors advance. This is the cost firewall.

## Three tiers (not four)

The original design had 4 tiers. We collapse to 3 for v1.
Tier 3 (confirmation with repeated runs) is a v2 concern -
in v1, human review serves as the confirmation step.

```
Candidate
    │
    ▼
┌─ Tier 0 ─┐  seconds       ~60% filtered
│  Sanity   │─── fail ──> archive (rejected)
└─────┬─────┘
      │ pass
      ▼
┌─ Tier 1 ─┐  seconds-min   ~25% more filtered
│ Correct.  │─── fail ──> archive (rejected)
└─────┬─────┘
      │ pass
      ▼
┌─ Tier 2 ─┐  minutes       signal extraction
│ Objective │──> archive (scored)
└───────────┘
```

## Tier 0 - Sanity (seconds)

**Purpose**: Reject obviously broken candidates before spending compute.

Checks:
- Patch applies cleanly
- Syntax valid (parse/compile)
- Formatting/lint passes
- Patch validation checks (see action-policy.md)

**Output**: pass/fail + list of violations
**Cost**: near zero

## Tier 1 - Correctness (seconds to minutes)

**Purpose**: Verify the candidate doesn't break existing functionality.

Checks:
- Unit tests (related to changed code)
- Type checking (if applicable)
- Static analysis

**Output**: pass/fail per check + coverage delta
**Cost**: low

## Tier 2 - Objective (minutes)

**Purpose**: Measure whether the candidate improves the target metric.

Checks:
- Benchmark / target metric measurement
- Integration tests (if applicable)

**Output**: metric values
**Cost**: moderate - only gate-passing candidates reach here

## Evaluator output contract

Every evaluator emits a structured result:

```yaml
tier: 1
evaluator: "unit_tests"
status: "pass" | "fail" | "error" | "timeout"
metrics:
  tests_passed: 142
  tests_failed: 0
duration_seconds: 23.5
logs_ref: "archive/exp-001/iter-7/cand-3/tier1_unit_tests.log"
```

This contract is the same across all tiers. Evaluators are pluggable -
the experiment config specifies which evaluators run at each tier.

## Tier promotion rules

| From | To | Condition |
|------|----|-----------|
| T0   | T1 | All T0 checks pass |
| T1   | T2 | All T1 checks pass |
| T2   | Archive (scored) | Metrics recorded, reward computed |

**Early stop**: If Tier 1 fails, stop. Don't run Tier 2 on broken candidates.

## Baseline calibration (non-negotiable)

Before any experiment:
1. Run all evaluation tiers on the **unmodified baseline code**
2. Run the target metric **5-10 times** to establish mean + stddev
3. Store as the experiment's baseline record

Without this, you can't distinguish improvement from noise.

```yaml
baseline:
  commit: "abc123"
  runs: 10
  metrics:
    throughput_rps: { mean: 1200, stddev: 45 }
    p95_ms: { mean: 48.2, stddev: 3.1 }
```

## Evaluation isolation

Each candidate is evaluated in:
- **Fresh git worktree** (not the working directory)
- **Resource limits**: CPU, memory, time caps per tier
- **Deterministic seeds**: pinned where possible
- **No network**: unless explicitly required

## v2+ additions

- **Tier 3 (Confirmation)**: Repeated runs for variance reduction, holdout evaluation
- **Parallel evaluation**: Multiple candidates evaluated concurrently
- **Adaptive tier thresholds**: Tighten thresholds as the frontier improves
