# Selection Spec

The selector decides what to try next. It's the system's "brain stem" -
not fancy, but critical for making progress.

## Core concept: Frontier

The frontier is the set of top K candidates that are alive for further exploration.
Think of it as a beam in beam search.

```
All attempts ──> Archive (everything stored)
                    │
                    ▼
              Gate-passing ──> Ranked by reward
                                    │
                                    ▼
                              Top K = Frontier
```

**Frontier size K**: 8 (default)

Why not just keep the single best? Because one wrong reward signal can trap
the entire search. A frontier of K gives resilience to noise.

## Parent selection

Each iteration, the selector picks parents from the frontier to generate candidates from.

### v1: Epsilon-greedy over frontier

```
with probability (1 - epsilon):
    pick from top 3 by reward (exploit)
with probability epsilon:
    pick uniformly from frontier (explore)

epsilon = 0.15
```

### Diversity enforcement

To prevent the search from collapsing:
- Same parent can't be picked more than 3 consecutive times
- Same intent can't be more than 60% of a batch
- At least 2 distinct parents per iteration (if frontier size allows)

## Candidate generation per iteration

Per iteration, generate N candidates:

```
N = 8 (default)
```

Distributed across:
- Multiple parents (2-4 from frontier)
- Multiple strategies (from the portfolio)
- Multiple granularities (XS through L)

This ensures diversity of exploration per iteration.

## Frontier update

After evaluation:

1. New gate-passing candidates are scored
2. Combined with existing frontier
3. Re-ranked by reward
4. Top K survive
5. Evicted candidates stay in archive but leave the frontier

**No candidate re-enters the frontier once evicted** (prevents oscillation).

## Convergence mechanics

### Problem: Getting stuck in local optima

Small patches exploit well but can't escape local optima.
Large patches explore but are noisy and often fail gates.

### Solution: Mixed granularity per iteration

| Granularity | Share | Purpose |
|-------------|-------|---------|
| XS/S        | 50%   | Exploit current best |
| M           | 35%   | Escape shallow optima |
| L           | 15%   | Occasional larger jumps |

### Problem: Reward plateau

When the frontier stops improving for multiple iterations.

### Solution: Plateau detection + response

If no frontier improvement for 3 consecutive iterations:
1. Increase exploration rate (epsilon → 0.3)
2. Shift granularity mix toward larger patches
3. Try strategies not recently used
4. If plateau persists for 5 more iterations: flag for human review

## Budget enforcement

The selector respects hard budgets:

```yaml
budget:
  max_iterations: 25
  max_wall_clock_hours: 4
  max_api_cost_usd: 50.0
  max_total_tokens: 2_000_000
```

When any budget is hit, the run stops gracefully:
- Current iteration completes
- Final frontier is archived
- Summary report generated

## v2 upgrade: Contextual bandit

Once the archive has enough data, the selector can learn:
- Which strategies work best for the current goal type
- Which granularities produce frontier candidates
- Which parents are "fertile" (produce successful children)
- Expected improvement per eval dollar spent

This turns the selector from a static policy into an adaptive one.
But v1 works without it.
