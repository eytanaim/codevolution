# High Level Design

## Mental model

A robotic engineer in a test chamber:
1. It tries a code change
2. The chamber measures behavior
3. A scoreboard updates
4. A controller decides what to try next
5. Good variants survive and breed ideas

This is **evolutionary search over code states** - closer to population-based optimization
and best-first search than classical RL. The RL framing maps well conceptually (state/action/reward),
but the v1 implementation is deliberately simpler: search + evaluation + selection.

## Core loop

```
┌─────────────────────────────────────────────────────┐
│                    EXPERIMENT RUN                     │
│                                                       │
│  ┌──────────┐    ┌──────────────┐    ┌────────────┐  │
│  │ Selector  │───>│ Patch Agent  │───>│ Evaluators │  │
│  │ (pick     │    │ (generate N  │    │ (tiered    │  │
│  │  parent)  │    │  candidates) │    │  pipeline) │  │
│  └─────▲─────┘    └──────────────┘    └─────┬──────┘  │
│        │                                     │         │
│        │         ┌──────────────┐            │         │
│        └─────────│   Archive    │◄───────────┘         │
│                  │ (all results │                      │
│                  │  + frontier) │                      │
│                  └──────────────┘                      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
                  Human-gated merge
```

Each iteration:
1. **Select** a parent policy (commit) from the archive/frontier
2. **Generate** N candidate patches via Claude Code (or any LLM agent)
3. **Evaluate** each candidate through tiered pipeline (cheap to expensive)
4. **Score** using hard gates + scalar reward
5. **Archive** everything (metrics, diffs, costs, failure reasons)
6. **Update** the frontier (top K surviving candidates)
7. **Optionally promote** to main branch (human-gated in v1)

## Core entities

### Artifact
The thing being optimized - a git repository with a defined scope.
Not the whole repo necessarily: a bounded subset of files/paths.

### Policy
A specific code state + the agent configuration that produced it.
- `commit_sha` + `branch`
- agent prompt version
- generation strategy used
- constraints version

### Action
What changes the state. Four types:
- **Patch** - diff to repo files (the primary action)
- **Test** - add/modify tests or benchmarks
- **Config** - compiler flags, runtime params
- **Meta** - change the generation strategy itself (later)

### Evaluator
Runs checks, emits metrics. Organized in tiers (cheap to expensive).
Each tier produces: metrics, pass/fail, runtime, cost, logs.

### Reward model
Converts evaluator output into:
- **Hard gates** (must pass, binary) - correctness, security, non-regression
- **Scalar reward** (ranking signal) - only compared among gate-passing candidates

### Archive
The system's memory. Every attempt is recorded with full context:
parent, diff, metrics, reward, cost, failure reason.
Without this, the system is a goldfish.

### Selector
Decides what to try next. Maintains a frontier of top K candidates.
Balances exploitation (best parents) with exploration (diversity).

## Key design decisions

### Why tiered evaluation?
Most candidates fail early. Running expensive benchmarks on everything wastes compute.
Tier 0 (lint/build) catches ~60% of bad candidates in seconds.
Only survivors advance to costly tiers.

### Why separate gates from reward?
Gates are non-negotiable (tests pass, no security regressions).
Reward is for ranking among acceptable candidates.
Mixing them creates perverse incentives - the system could optimize reward
while barely passing gates.

### Why an archive?
- Prevents re-exploring failed paths
- Enables learning which strategies work
- Provides audit trail
- Makes experiments reproducible
- Feeds the selector with history

### Why human-gated merge?
Auto-promotion within the experiment frontier is fine.
Auto-merging to the main branch is not (in v1).
Trust is earned incrementally.

## What this is NOT

- Not a CI/CD system (though it uses similar infrastructure)
- Not "AI writes all the code" (it's search, not generation)
- Not reinforcement learning on day 1 (it's evolutionary search with optional RL later)
- Not autonomous (human stays in the loop for promotion decisions)

## Upgrade path

v1: Evolutionary search with beam-style selection
v2: Contextual bandit for strategy selection (which prompt/approach works best)
v3: Full RL controller for meta-decisions (exploration rate, budget allocation)

Each version is useful on its own. No need to build v3 to get value from v1.
