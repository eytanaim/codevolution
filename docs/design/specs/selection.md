# Selection Spec

How the system decides what to try next.

## v1: Sequential Conditioned Sampling (SCS)

The selector in v1 is deliberately simple:

1. Look at archive: find the **best gate-passing candidate so far**
2. Include its diff and metrics as context for the next generation
3. Include recent failures and their reasons as anti-patterns
4. Generate the next batch

That's it. No frontier, no population, no epsilon-greedy.

### Why this works

The ["Simple Baselines" paper](https://arxiv.org/html/2602.16805) (Feb 2025) showed
that SCS matches or beats sophisticated evolutionary systems (AlphaEvolve, AIDE)
on most tasks. The key insight: **conditioning on prior successes via the LLM's
context window is already a powerful form of selection.**

The LLM doesn't need a formal selection algorithm - it needs good context.

## What goes into "conditioning"

Each iteration, the context builder provides:

```
1. The goal (what we're optimizing for)
2. The best candidate so far (diff + metrics)
3. The 2-3 most recent failures (what went wrong)
4. Constraints (what's allowed, what's forbidden)
```

This is the SCS "selection" mechanism. It works because the LLM can
synthesize patterns from successful attempts and avoid patterns from failures.

See [Context Engineering spec](context-engineering.md) for full details.

## Budget enforcement

The selector respects hard budgets:

```yaml
budget:
  max_iterations: 20
  max_candidates_per_iteration: 4
  max_wall_clock_hours: 4
  max_api_cost_usd: 50.0
```

When any budget is hit, the run stops:
- Current iteration completes
- Final archive state is preserved
- Best candidate is flagged for human review

## Baseline comparison (always)

Every experiment should compare against:

- **Baseline 0**: Current code, no changes (the zero point)
- **Baseline 1**: Ask Claude N times independently, pick best (IID Random Sampling)
- **Your system's result**: SCS with feedback

If SCS can't beat IID RS consistently, the feedback loop isn't working
and you should debug your context builder, not add more search machinery.

## When to upgrade to evolutionary selection (v2+)

Add frontier/population-based selection when you observe:

1. **Plateau**: Reward stops improving for 5+ iterations despite good feedback
2. **Diversity collapse**: All candidates converge to similar patches
3. **Noisy rewards**: Single-best selection is unstable due to metric variance

Upgrade path:
- v2: Keep top K=3 candidates instead of just best (mini-frontier)
- v3: Add diversity enforcement (don't use same parent consecutively)
- v4: Full population-based selection with MAP-Elites

Each step is justified by data, not speculation.
