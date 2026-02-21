# ADR-001: Evolutionary Search First, RL Later

## Status
Accepted

## Context
The original framing maps git repos to RL (state/action/reward/policy).
This is conceptually valid but implementing full RL on day 1 introduces
unnecessary complexity: policy gradients, value functions, replay buffers,
training stability.

## Decision
v1 uses **evolutionary search with beam-style selection**:
- Population of candidates (frontier)
- Tiered evaluation (cheap to expensive)
- Score + select + reproduce
- No gradient computation, no learned value function

This is equivalent to a mu+lambda evolution strategy with
tiered fitness evaluation and epsilon-greedy parent selection.

## Consequences
- Simpler to implement and debug
- Each iteration produces immediately interpretable results
- No training instability or reward shaping issues
- Clear upgrade path: contextual bandit (v2) then full RL (v3)
- May be slower to converge than learned approaches on well-shaped reward landscapes
- Acceptable tradeoff: correctness and simplicity over speed of convergence

## Upgrade path
- v2: Contextual bandit for strategy/parent selection (learns from archive)
- v3: Full RL controller for meta-decisions (budget allocation, exploration rate)
