# codevolution

Evolutionary code optimization engine built on git.

A git repository is a policy store. Code changes are actions. Evaluators produce reward signals.
The system searches for better code states through structured exploration with feedback loops.

## Core idea

```
build context (goal + best so far + failures) → claude -p → evaluate (tiered) → archive → repeat
```

v1 uses Sequential Conditioned Sampling (SCS): generate candidates, evaluate them,
feed successful results as context to the next batch. Research shows this matches
sophisticated evolutionary systems on most tasks. The leverage is in problem formulation,
feedback loops, and evaluation rigor - not search sophistication.

## Design docs

- [High Level Design](docs/design/HLD.md) - Mental model, core loop, architecture
- Specs:
  - [Context Engineering](docs/design/specs/context-engineering.md) - What goes into each LLM prompt (highest leverage)
  - [Feedback Loop](docs/design/specs/feedback-loop.md) - How evaluation results flow back to generation
  - [Evaluation Tiers](docs/design/specs/evaluation-tiers.md) - 3-tier pipeline (lint → tests → benchmark)
  - [Reward Model](docs/design/specs/reward-model.md) - Gates + scalar scoring
  - [Action Policy](docs/design/specs/action-policy.md) - What the system can change
  - [Archive](docs/design/specs/archive.md) - System memory (JSONL)
  - [Selection](docs/design/specs/selection.md) - SCS in v1, evolutionary upgrade path
  - [Safety](docs/design/specs/safety.md) - Anti-cheating, isolation, human gates
- Decisions:
  - [ADR-001](docs/design/decisions/ADR-001-evolutionary-search-over-rl.md) - Why search before RL
  - [ADR-002](docs/design/decisions/ADR-002-scs-over-evolution-v1.md) - Why SCS before evolution in v1

## Build order (what to implement first)

1. Baseline calibration tool
2. Single candidate pipeline (context → claude -p → patch → evaluate → archive)
3. Loop wrapper with SCS conditioning
4. Budget enforcement
5. Feedback builder

## Status

Design phase. No code yet.
