# High Level Design

## Mental model

A robotic engineer in a test chamber:
1. It tries a code change
2. The chamber measures behavior
3. Results feed back as context for the next attempt
4. Good results survive and inform future tries

This is **search over code states with evaluation feedback** - specifically,
Sequential Conditioned Sampling (SCS): generate candidates, evaluate, feed
successful results as context to the next batch.

Research shows (["Simple Baselines are Competitive with Code Evolution", Feb 2025](https://arxiv.org/html/2602.16805))
that SCS matches or beats sophisticated evolutionary systems on most tasks.
The real leverage is in **problem formulation, prompt context, and evaluation rigor** -
not search sophistication.

## Core loop (v1)

```
┌──────────────────────────────────────────────────────┐
│                   EXPERIMENT RUN                      │
│                                                       │
│  ┌───────────┐    ┌───────────────┐                  │
│  │  Context   │───>│  Claude Code   │                 │
│  │  Builder   │    │  (claude -p)   │                 │
│  │            │    │  N candidates  │                 │
│  └─────▲──────┘    └───────┬───────┘                  │
│        │                   │                          │
│        │  feedback    ┌────▼──────────┐               │
│        │  loop        │ Eval Pipeline  │              │
│  ┌─────┴──────┐ ◄────│ (git worktree  │              │
│  │  Archive    │      │  + 3 tiers)    │              │
│  │  (JSONL)    │      └────────────────┘              │
│  └─────────────┘                                      │
│                                                       │
│  Each iteration:                                      │
│  1. Pick best from archive                            │
│  2. Build context with evaluation feedback            │
│  3. Generate next batch of candidates                 │
│  4. Evaluate, archive, repeat                         │
└──────────────────────────────────────────────────────┘
                        │
                        ▼
                 Human-gated merge
```

Each iteration:
1. **Build context** from archive: best candidate so far, its diff, evaluation feedback
2. **Generate** N candidates via `claude -p` (parallel via git worktrees)
3. **Evaluate** each through tiered pipeline (lint/build → tests → benchmark)
4. **Archive** everything (metrics, diffs, costs, failure reasons)
5. **Feed back**: successes become context, failures become warnings
6. **Repeat** until budget exhausted or goal met
7. **Human reviews** best candidate for merge

The selector is just "pick the best so far + include its context."
That's SCS. It works.

## Core entities

### Artifact
The thing being optimized - a git repository with a bounded scope.
A subset of files/paths, not the whole repo.

### Action
What changes the state. In v1: **code patches only.**
Test changes and config changes are deferred to v2.

### Evaluator
Runs checks, emits metrics. Three tiers (cheap → expensive).
Each tier produces: metrics, pass/fail, duration, logs.

### Reward model
Converts evaluator output into:
- **Hard gates** (must pass, binary) - correctness, security, non-regression
- **Scalar reward** (ranking signal) - only among gate-passing candidates

### Archive
The system's memory. Every attempt is recorded with full context.
Feeds the context builder for future iterations.

### Context builder
**The highest-leverage component.** Constructs the prompt for Claude Code
from: goal description, repo state, constraints, archive history, evaluation feedback.
See [Context Engineering spec](specs/context-engineering.md).

### Feedback loop
How evaluation results flow back to generation.
See [Feedback Loop spec](specs/feedback-loop.md).

## Key design decisions

### Why SCS over evolutionary search?
Recent research shows SCS matches sophisticated evolutionary systems on most tasks.
The complexity of frontier management, population genetics, and selection policies
doesn't pay for itself until you have evidence it's needed.
See [ADR-002](decisions/ADR-002-scs-over-evolution-v1.md).

### Why tiered evaluation?
Most candidates fail early. Running expensive benchmarks on everything wastes compute.
Tier 0 (lint/build) catches ~60% of bad candidates in seconds.
Only survivors advance to costly tiers. This pattern is validated across
AlphaEvolve, OpenEvolve, CodeEvolve, and LLMLOOP.

### Why separate gates from reward?
Gates are non-negotiable (tests pass, no security regressions).
Reward is for ranking among acceptable candidates.
Mixing them creates perverse incentives.

### Why feedback loops matter most?
Every successful system (OpenEvolve, CodeEvolve, Eureka, LLMLOOP) feeds
evaluation results back to the generator. This is more important than
selection sophistication. Error traces, success patterns, and metric
feedback are what drive real improvement.

### Why human-gated merge?
Auto-promotion within the experiment is fine.
Auto-merging to the main branch is not (in v1).
Trust is earned incrementally.

## What this is NOT

- Not a CI/CD system (though it uses similar infrastructure)
- Not "AI writes all the code" (it's search over code states)
- Not autonomous (human stays in the loop for promotion)

## Upgrade path

Each version is useful on its own:

- **v1**: SCS with feedback loops (current design)
- **v2**: Frontier-based selection with population (when plateau data justifies it)
- **v3**: MAP-Elites quality-diversity (when you need diverse solution types)
- **v4**: Contextual bandit / RL controller (when archive has enough data)

**Always maintain baseline comparison**: if your system can't beat
"ask Claude N times independently and pick the best" (IID RS),
the added machinery isn't paying for itself.

## Implementation stack (boring on purpose)

- **Orchestrator**: Python script. Not a framework.
- **Patch generator**: `claude -p` with `--allowedTools` and `--output-format json`
- **Isolation**: `git worktree` per candidate
- **Evaluation**: Shell scripts per tier, run in worktree
- **Storage**: JSONL + patch files on disk
- **Config**: Single YAML file per experiment
