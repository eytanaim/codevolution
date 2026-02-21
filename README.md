# codevolution

Evolutionary code optimization engine built on git.

A git repository is a policy store. Code changes are actions. Evaluators produce reward signals.
The system searches for better code states through structured exploration - like a robotic engineer
in a test chamber that tries changes, measures outcomes, and learns what works.

## Core idea

```
pick parent commit -> generate candidate patches -> evaluate (tiered) -> score -> archive -> repeat
```

This is evolutionary search over code states, not "AI writing code."
It's closer to best-first search with bandit-style exploration than end-to-end RL.

## Design docs

- [High Level Design](docs/design/HLD.md) - Mental model, core entities, architecture
- Specs:
  - [Action Policy](docs/design/specs/action-policy.md) - What the system can change
  - [Evaluation Tiers](docs/design/specs/evaluation-tiers.md) - How candidates are measured
  - [Reward Model](docs/design/specs/reward-model.md) - Gates + scalar scoring
  - [Archive](docs/design/specs/archive.md) - System memory and data model
  - [Selection](docs/design/specs/selection.md) - How the system decides what to try next
  - [Safety](docs/design/specs/safety.md) - Anti-cheating, isolation, human gates

## Status

Design phase. No code yet.
