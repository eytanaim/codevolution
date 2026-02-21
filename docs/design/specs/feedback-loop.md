# Feedback Loop Spec

How evaluation results flow back to generation.
This is the highest-impact mechanism in the system.

## Why this matters most

Every successful system feeds evaluation results back to the generator:
- OpenEvolve: failed solutions' execution logs become prompt context
- CodeEvolve: error traces feed subsequent generations
- Eureka: "reward reflection" feeds metrics back as LLM context
- LLMLOOP: five iterative loops for compilation errors, test failures, etc.

Without feedback, each generation is independent. With feedback,
the system learns from its mistakes within a single experiment run.

## Feedback types

### On gate failure (most valuable)

When a candidate fails a gate (build breaks, tests fail):

```yaml
feedback:
  type: "gate_failure"
  tier: 1
  gate: "all_tests_pass"
  summary: "3 unit tests failed in test_engine.py"
  error_output: |
    FAILED test_engine.py::test_cache_invalidation - AssertionError: expected 0, got 3
    FAILED test_engine.py::test_concurrent_access - TimeoutError after 5s
    FAILED test_engine.py::test_edge_case_empty - KeyError: 'result'
  files_involved: ["src/engine.py", "tests/test_engine.py"]
```

This tells the LLM exactly what went wrong and where.

### On gate pass but low reward

When a candidate passes all gates but doesn't improve the target metric:

```yaml
feedback:
  type: "low_reward"
  reward: 0.3
  best_reward_so_far: 4.2
  metrics:
    candidate: { throughput_rps: 1210 }
    baseline: { throughput_rps: 1200 }
    best_so_far: { throughput_rps: 1250 }
  hint: "Change passed tests but only marginally improved throughput"
```

### On success (best so far)

When a candidate becomes the new best:

```yaml
feedback:
  type: "new_best"
  reward: 5.1
  previous_best_reward: 4.2
  diff_ref: "archive/exp-001/diffs/iter-7-cand-3.patch"
  metrics:
    candidate: { throughput_rps: 1310 }
    baseline: { throughput_rps: 1200 }
  what_improved: "throughput increased 9.2% over baseline"
```

This diff becomes the conditioning context for the next iteration.

## How feedback enters the prompt

The context builder assembles feedback into the Claude Code prompt:

```
## Previous Results

### Best result so far (iteration 5, candidate 2):
- Throughput: 1250 rps (+4.2% over baseline)
- Patch: [included as diff]

### Recent failure (iteration 6, candidate 1):
- Failed: unit tests in test_engine.py
- Error: TimeoutError in test_concurrent_access
- Avoid: the concurrent access pattern used in this attempt

### Recent failure (iteration 6, candidate 3):
- Passed tests but no improvement (+0.1%)
- The caching approach in this diff didn't help
```

See [Context Engineering spec](context-engineering.md) for the full prompt structure.

## Feedback budget

Not all history fits in the context window. Priority order:

1. **Best candidate diff + metrics** (always included)
2. **Most recent gate failure** (1-2, with error output)
3. **Most recent low-reward attempt** (1, summary only)
4. **Older successes** (only if context budget allows)

Total feedback context should be **< 30% of the prompt**. The rest is
goal description, repo context, and constraints.

## What we explicitly do NOT do

- Don't include all historical failures (context window pollution)
- Don't include raw logs (too verbose - summarize to relevant lines)
- Don't give the LLM the reward formula (prevents meta-gaming)
- Don't feed back evaluation infrastructure details (anti-cheating)

## Feedback as the convergence mechanism

In SCS, feedback IS the selection mechanism:
- Successes tell the LLM "more like this"
- Failures tell the LLM "not like this"
- Metrics tell the LLM "this much better/worse"

This replaces the need for formal population genetics.
The LLM's in-context learning does the selection implicitly.
