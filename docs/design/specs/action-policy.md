# Action Policy Spec

What the system is allowed to change, how, and with what constraints.

## Action types

### Type 1: Patch (primary)
Direct code changes via diff/patch to repository files.
This is 90%+ of what the system does.

### Type 2: Test
Add or modify tests and benchmarks.
Improves observability and evaluation quality.
Must be clearly tagged - test changes affect the measurement system itself.

### Type 3: Config
Compiler flags, runtime parameters, lint settings.
Lower risk but can have large impact.
Tightly constrained per experiment.

### Type 4: Meta (v2+)
Changes to the generation strategy or prompt templates.
The system optimizing its own approach.
Requires careful isolation from reward gaming.

## Scope constraints

Every experiment defines:

```yaml
scope:
  allowed_paths:
    - "src/service/foo/**"
    - "tests/service/foo/**"
  forbidden_paths:
    - "src/core/auth/**"
    - ".github/**"
    - "*.lock"
  allowed_file_types:
    - "*.py"
    - "*.ts"
    - "*.yaml"  # config only if action type permits
  max_files_changed: 5
  max_loc_delta: 400
```

Forbidden paths are hard stops - patches touching them are rejected before evaluation.

## Patch granularity

Each attempt is tagged by size:

| Class | Changed lines | Notes |
|-------|--------------|-------|
| XS    | < 10         | Surgical fixes |
| S     | 10-50        | Targeted changes |
| M     | 50-200       | Feature-level changes |
| L     | 200-500      | Significant refactors |
| XL    | > 500        | Disabled by default in v1 |

The generation step targets a **mix** of granularities per iteration
to balance exploitation (small precise) with exploration (larger jumps).

Default mix: XS 20% / S 30% / M 35% / L 15%

## Patch intent tags

Each attempt is tagged by intent:
- `bugfix` - fix a defect
- `perf` - performance improvement
- `refactor` - structural change, same behavior
- `test` - test coverage or quality
- `reliability` - error handling, resilience
- `cleanup` - dead code, style
- `config-tuning` - parameter adjustment

Intent tags feed the selector - over time, the system learns which
intents pay off for a given optimization goal.

## Generation strategies

The agent doesn't use one prompt. It uses a portfolio of strategies:

- **safe_incremental** - small, conservative, low-risk changes
- **aggressive_perf** - willing to restructure for performance
- **test_first** - write/improve tests, then patch based on findings
- **refactor_then_optimize** - clean up, then improve
- **diagnose_then_patch** - analyze metrics/logs, then targeted fix

Each iteration samples from this portfolio.
Strategy effectiveness is tracked in the archive.

## Validation checks (pre-evaluation)

Before any evaluator runs, patches must pass static checks:

- [ ] Patch applies cleanly to base commit
- [ ] No forbidden paths touched
- [ ] Within file count and LOC limits
- [ ] No tests disabled or assertions weakened
- [ ] No benchmark-specific conditionals added
- [ ] No swallowed exceptions or `|| true` patterns
- [ ] No edits to evaluation/reward infrastructure
- [ ] Action type matches experiment's allowed types

Failures here are cheap and fast - no compute wasted.
