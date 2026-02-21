# Archive Spec

The archive is the system's memory. Every attempt is recorded with full context.
Without it, the system is a goldfish - unable to learn from history or avoid repeating failures.

## Purpose

1. **Prevent re-exploration** of failed paths
2. **Enable learning** which strategies/intents/granularities work
3. **Audit trail** for human review
4. **Reproducibility** for any result
5. **Feed the selector** with historical performance data

## Attempt record schema

One record per candidate attempt:

```yaml
# Identity
attempt_id: "uuid"
experiment_id: "exp-001"
iteration: 7
timestamp: "2024-01-15T10:23:00Z"

# Lineage
parent_attempt_id: "uuid-of-parent"
base_commit: "abc123"
candidate_commit: "def456"
branch: "evo/exp-001/iter-7/candidate-3"

# Generation context
agent_strategy: "aggressive_perf"
patch_intent: "perf"
patch_granularity: "M"
prompt_version: "v1.2"

# Patch stats
files_changed: ["src/engine.py", "src/cache.py"]
loc_added: 45
loc_removed: 12
diff_ref: "archive/exp-001/iter-7/cand-3.patch"

# Evaluation results (per tier)
tier_results:
  - tier: 0
    status: "pass"
    duration_seconds: 2.1
    checks: { lint: pass, build: pass, policy: pass }
  - tier: 1
    status: "pass"
    duration_seconds: 18.4
    checks: { unit_tests: pass, typecheck: pass }
    metrics: { tests_passed: 142, coverage_delta: +0.3 }
  - tier: 2
    status: "pass"
    duration_seconds: 120.0
    metrics: { throughput_rps: 1250, p95_ms: 42.1, memory_mb: 312 }

# Scoring
gates_passed: true
reward_breakdown:
  correctness: 100.0
  performance: 12.5
  patch_size_penalty: -3.2
  total: 109.3
failure_reason: null  # or "tier_1_unit_test_failure"

# Cost
cost:
  tokens_input: 15000
  tokens_output: 3200
  api_cost_usd: 0.08
  compute_seconds: 140.5

# Status
promotion_status: "frontier"  # or "rejected", "finalist", "promoted"
logs_ref: "archive/exp-001/iter-7/cand-3/logs/"
```

## Storage strategy

### v1: Simple file-based
- JSONL file per experiment (`archive/exp-001/attempts.jsonl`)
- Patch diffs stored as files (`archive/exp-001/diffs/`)
- Logs stored as files (`archive/exp-001/logs/`)
- SQLite index for queries

### v2: Structured DB
- PostgreSQL for attempt records
- Object storage for large artifacts (logs, diffs)
- Queryable metrics history

Start with v1. It's grep-friendly and debuggable.

## Reproducibility metadata

Every experiment run pins:

```yaml
reproducibility:
  base_commit: "abc123"
  dependency_lockfile_hash: "sha256:..."
  container_image: "codevolution/eval:v1.0@sha256:..."
  benchmark_dataset_version: "v2.1"
  hardware_class: "4cpu-8gb"  # if perf matters
  env_vars_hash: "sha256:..."  # sanitized, no secrets
```

Without this, comparing results across runs is meaningless.

## Retention policy

- **All attempt records**: kept indefinitely (they're small)
- **Diffs for frontier/promoted**: kept indefinitely
- **Diffs for rejected**: kept for N days, then prunable
- **Full logs**: kept for N days, summaries kept indefinitely
- **Evaluation artifacts**: kept for frontier, prunable for rejected

## Queryable dimensions

The archive should support queries like:
- "Show top 10 attempts by reward for experiment X"
- "Which strategies produced the most frontier candidates?"
- "What's the failure rate by patch granularity?"
- "Show all attempts that touched file Y"
- "What's the reward trend over iterations?"

These drive the selector and human understanding of the process.
