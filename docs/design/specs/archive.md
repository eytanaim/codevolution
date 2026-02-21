# Archive Spec

The archive is the system's memory. Every attempt is recorded.
It serves three purposes:
1. **Feed the context builder** with history for SCS-style conditioning
2. **Enable analysis** of what works and what doesn't
3. **Provide audit trail** for human review

## Attempt record (simplified)

One JSONL record per candidate:

```json
{
  "attempt_id": "uuid",
  "experiment_id": "exp-001",
  "iteration": 7,
  "timestamp": "2025-02-21T10:23:00Z",

  "parent_attempt_id": "uuid-of-best-so-far",
  "base_commit": "abc123",
  "candidate_branch": "evo/exp-001/iter-7/cand-3",

  "files_changed": ["src/engine.py", "src/cache.py"],
  "loc_added": 45,
  "loc_removed": 12,
  "diff_ref": "archive/exp-001/diffs/iter-7-cand-3.patch",

  "tier_results": [
    {"tier": 0, "status": "pass", "duration_s": 2.1},
    {"tier": 1, "status": "pass", "duration_s": 18.4,
     "metrics": {"tests_passed": 142, "tests_failed": 0}},
    {"tier": 2, "status": "pass", "duration_s": 120.0,
     "metrics": {"throughput_rps": 1250, "p95_ms": 42.1}}
  ],

  "gates_passed": true,
  "reward": 4.2,
  "failure_reason": null,

  "cost": {
    "tokens_input": 15000,
    "tokens_output": 3200,
    "api_cost_usd": 0.08,
    "eval_duration_s": 140.5
  }
}
```

## What we cut from the original schema

- `agent_strategy`, `patch_intent`, `patch_granularity` - not prescribed in v1
- `prompt_version`, `constraints_version` - tracked via experiment config, not per-attempt
- `promotion_status` - replaced by simple `gates_passed` + `reward`
- `novelty_features` - v2+ concern (MAP-Elites)
- Separate `reward_breakdown` - single reward number is enough for v1

## Storage

### v1: Files on disk

```
archive/
  exp-001/
    config.yaml          # experiment configuration (frozen at start)
    baseline.json        # baseline calibration results
    attempts.jsonl       # one line per attempt
    diffs/               # patch files
      iter-1-cand-1.patch
      iter-1-cand-2.patch
      ...
    logs/                # evaluation logs (optional, prunable)
      iter-1-cand-1/
        tier0.log
        tier1.log
        tier2.log
```

JSONL is grep-friendly, append-only, and trivially debuggable.
No database needed until you have thousands of attempts.

## Reproducibility

Every experiment pins:

```yaml
reproducibility:
  base_commit: "abc123"
  dependency_lockfile_hash: "sha256:..."
  eval_script_hash: "sha256:..."
```

Stored once in `config.yaml`, not per-attempt.

## Key queries the archive should support

- "What's the best reward so far?" → sort attempts.jsonl by reward
- "What failed and why?" → filter by failure_reason != null
- "How is reward trending?" → plot reward over iterations
- "What files get changed most?" → aggregate files_changed
- "What's the total cost?" → sum cost fields

In v1, these are `jq` one-liners over the JSONL file.
