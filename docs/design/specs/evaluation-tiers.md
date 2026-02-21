# Evaluation Tiers Spec

Candidates are evaluated through a tiered pipeline.
Cheap checks run first. Only survivors advance to expensive tiers.
This is the system's cost firewall.

## Tier overview

```
Candidate
    │
    ▼
┌─ Tier 0 ─┐  seconds     ~60% filtered out
│  Sanity   │─── fail ──> archive (rejected)
└─────┬─────┘
      │ pass
      ▼
┌─ Tier 1 ─┐  seconds-minutes  ~25% more filtered
│ Correct.  │─── fail ──> archive (rejected)
└─────┬─────┘
      │ pass
      ▼
┌─ Tier 2 ─┐  minutes     signal extraction
│ Objective │─── below threshold ──> archive (marginal)
└─────┬─────┘
      │ promising
      ▼
┌─ Tier 3 ─┐  minutes-hours   confirmation
│ Confirm.  │──> archive (finalist)
└───────────┘
```

## Tier 0 - Sanity (seconds)

**Purpose**: Reject obviously broken candidates before spending compute.

Checks:
- Patch applies cleanly
- Syntax valid (parse/compile)
- Formatting/lint passes
- Forbidden file check
- Patch policy check (no disabled tests, no weakened asserts)

**Output**: pass/fail + list of violations
**Cost**: near zero
**Expected filter rate**: ~60% of candidates

## Tier 1 - Correctness (seconds to minutes)

**Purpose**: Verify the candidate doesn't break existing functionality.

Checks:
- Targeted unit tests (test files related to changed code)
- Type checking (if applicable)
- Static analysis (security, complexity)
- Fast smoke tests

**Output**: pass/fail per check + coverage delta
**Cost**: low
**Expected filter rate**: ~25% of Tier 0 survivors

## Tier 2 - Objective signal (minutes)

**Purpose**: Measure whether the candidate actually improves the target metric.

Checks:
- Benchmark on target workload
- Integration tests
- Memory/runtime profiling
- Small-N reliability runs

**Output**: metric values + statistical summary
**Cost**: moderate (this is where real compute happens)
**Promotion rule**: must show improvement above `baseline + margin`

## Tier 3 - Confirmation (expensive, selective)

**Purpose**: High-confidence validation of top candidates before promotion.

Checks:
- Repeated benchmark runs (3-5x) for variance reduction
- Larger/different datasets
- Holdout evaluation set (anti-overfitting)
- Full CI pipeline (optional)

**Output**: mean + stddev + confidence interval per metric
**Cost**: high - only run on finalists
**Trigger**: top 2-3 candidates from Tier 2

## Evaluator output contract

Every evaluator at every tier emits a structured result:

```yaml
tier: 1
evaluator: "unit_tests"
status: "pass" | "fail" | "error" | "timeout"
metrics:
  tests_passed: 142
  tests_failed: 0
  coverage_delta: +0.3
duration_seconds: 23.5
cost_estimate: 0.0  # compute cost if relevant
logs_ref: "s3://archive/run-42/tier1/unit_tests.log"
```

## Tier promotion rules

Candidates advance only if:

| From | To | Condition |
|------|----|-----------|
| T0   | T1 | All T0 checks pass |
| T1   | T2 | All T1 checks pass |
| T2   | T3 | Metric improvement > baseline + margin |
| T3   | Frontier | Confirmed improvement with low variance |

**Early stop rules** (save compute):
- If Tier 1 score below baseline minus margin: stop
- If no metric improvement and patch is large (M+): stop
- If test coverage drops: stop

## Baseline management

Baselines are not static. They must be:
- **Measured at experiment start** (not assumed)
- **Re-measured periodically** (environment drift)
- **Stored with variance** (mean + stddev from multiple runs)

Without baseline variance data, you can't distinguish real improvement from noise.

**Pre-experiment calibration step**: run baseline N times (5-10) to establish
mean and variance for all target metrics. This is non-negotiable.
