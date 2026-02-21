# Reward Model Spec

The reward model converts evaluator outputs into two things:
1. **Hard gates** - binary pass/fail, non-negotiable
2. **Scalar reward** - ranking signal among gate-passing candidates

This separation is the single most important design decision in the reward system.

## Why separate gates from reward?

If you penalize-but-allow critical failures, the optimizer will find candidates
that score high reward while barely skirting failure boundaries.
Gates eliminate this: you either pass or you're out.

## Hard gates

Gates are defined per experiment:

```yaml
gates:
  - name: build_succeeds
    tier: 0
    condition: "build.status == 'pass'"

  - name: all_tests_pass
    tier: 1
    condition: "tests.failed == 0"

  - name: no_forbidden_edits
    tier: 0
    condition: "patch.forbidden_files_touched == 0"
```

A single gate failure = candidate rejected. Full stop.

Gates map naturally to evaluation tiers:
- Tier 0 gates: build, lint, patch policy
- Tier 1 gates: tests pass, no security regressions
- Tier 2 gates: no regression on target metric beyond threshold

## Scalar reward

Used only for ranking gate-passing candidates. Keep it simple in v1.

### v1 formula

```
reward = metric_improvement_pct - patch_size_penalty
```

Where:
- `metric_improvement_pct` = % improvement over baseline on target metric
- `patch_size_penalty` = small multiplier on LOC changed (discourages bloat)

That's it. One metric, one penalty. Start here.

### Why not a weighted multi-metric formula?

The original design had 7 weighted components (correctness, perf, reliability,
maintainability, risk, cost penalties). This is premature:
- You need data to set weights
- Multi-metric formulas create unexpected interactions
- Debugging "why did this candidate rank higher" becomes hard

Start with one target metric. Add dimensions when you understand the landscape.

### When to add complexity

Add a second reward dimension when:
- You have 50+ archive entries and can analyze trade-offs
- The single metric is clearly insufficient (e.g., speed improves but memory regresses)
- You can justify each weight with data

## Anti-Goodhart measures

> "When a measure becomes a target, it ceases to be a good measure."

- **Patch policy checks** catch structural gaming (disabled tests, benchmark conditionals)
- **Reward formula is frozen** during an experiment run
- **Human review** of promoted candidates catches semantic gaming
- **Baseline comparison**: always compare against "ask Claude N times, pick best" (IID RS)

## Tie-breaking

When candidates have equal reward:
1. Prefer smaller patch (less risk)
2. Prefer newer (more recent iteration)
