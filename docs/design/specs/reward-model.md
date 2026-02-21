# Reward Model Spec

The reward model converts evaluator outputs into two things:
1. **Hard gates** - binary pass/fail, non-negotiable
2. **Scalar reward** - ranking signal among gate-passing candidates

This separation is the single most important design decision in the reward system.

## Why separate gates from reward?

If you penalize-but-allow critical failures, the optimizer will eventually
find candidates that score high reward while barely skirting failure boundaries.
Gates eliminate this: you either pass or you're out. No negotiation.

Reward only matters among candidates that already cleared all gates.

## Hard gates

Gates are defined per experiment. Template:

```yaml
gates:
  - name: build_succeeds
    tier: 0
    condition: "build.status == 'pass'"

  - name: all_tests_pass
    tier: 1
    condition: "tests.failed == 0"

  - name: no_security_regressions
    tier: 1
    condition: "security.new_high_severity == 0"

  - name: no_forbidden_edits
    tier: 0
    condition: "patch.forbidden_files_touched == 0"

  - name: no_perf_regression
    tier: 2
    condition: "perf.p95_delta_pct > -2.0"

  - name: no_memory_regression
    tier: 2
    condition: "memory.peak_delta_pct > -5.0"
```

A single gate failure = candidate rejected. Full stop.

## Scalar reward

Used only for ranking gate-passing candidates.

### Template formula

```
R = w_correct * correctness_score
  + w_perf    * perf_gain_normalized
  + w_rely    * reliability_gain_normalized
  + w_maint   * maintainability_gain_normalized
  - w_size    * patch_size_penalty
  - w_risk    * risk_penalty
  - w_cost    * eval_cost_penalty
```

Weights are set per experiment goal. The structure stays constant.

### Normalization

Raw metrics have different scales. Normalize before combining:
- **% improvement over baseline** for bounded metrics
- **z-score** for noisy metrics (using baseline variance)
- **Clipped deltas** to prevent outliers from dominating

### Penalties

Without penalties, the optimizer gravitates toward huge rewrites.

- **patch_size_penalty**: scales with LOC changed (encourages surgical changes)
- **risk_penalty**: flags for patterns like broad refactors, dependency changes
- **eval_cost_penalty**: tokens + compute used (encourages efficiency)

### Confidence adjustment

If a metric measurement is noisy (high variance across runs):
- Discount its contribution by confidence
- Or: use lower bound of confidence interval instead of point estimate

This prevents "lucky" candidates from ranking high on noise.

## Reward schema (per experiment config)

```yaml
reward:
  weights:
    correctness: 100
    performance: 30
    reliability: 10
    maintainability: 5
  penalties:
    patch_size: 10
    risk: 15
    eval_cost: 5
  normalization: "pct_improvement"  # or "z_score"
  confidence_adjustment: true
```

Weights are placeholders - tuned per goal. The schema is the invariant.

## Anti-Goodhart measures

> "When a measure becomes a target, it ceases to be a good measure."

- **Holdout evaluations** in Tier 3 that the agent doesn't see during optimization
- **Reward formula is frozen** during an experiment run (no mid-run tweaks)
- **Multiple independent metrics** prevent single-metric gaming
- **Patch policy checks** catch structural gaming (disabled tests, benchmark conditionals)
- **Human review** of promoted candidates catches semantic gaming

## Tie-breaking

When candidates have equal reward:
1. Prefer smaller patch (less risk)
2. Prefer higher confidence (lower variance)
3. Prefer newer (more recent parent = more context)
