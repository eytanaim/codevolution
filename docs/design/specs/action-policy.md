# Action Policy Spec

What the system is allowed to change, and the constraints around it.

## v1 scope: Patches only

In v1, the only action type is **code patches** - diffs applied to repository files.
Test changes, config changes, and meta-actions (changing generation strategy)
are deferred to v2+. This keeps the action space simple and auditable.

## Scope constraints

Every experiment defines what's in bounds:

```yaml
scope:
  allowed_paths:
    - "src/service/foo/**"
    - "tests/service/foo/**"
  forbidden_paths:
    - "src/core/auth/**"
    - ".github/**"
    - "*.lock"
  max_files_changed: 5
  max_loc_delta: 400
```

Forbidden paths are hard stops - patches touching them are rejected before evaluation.

## Patch validation (pre-evaluation)

Before any evaluator runs, patches must pass static checks:

- Patch applies cleanly to base commit
- No forbidden paths touched
- Within file count and LOC limits
- No tests disabled or assertions weakened
- No swallowed exceptions (`except: pass`, `|| true`)
- No edits to evaluation infrastructure

These are cheap regex/AST checks. Failures cost near-zero compute.

## What we don't prescribe in v1

The original design specified granularity distributions (XS/S/M/L mix),
intent tags (bugfix/perf/refactor), and a portfolio of 5 generation strategies.

We cut these because:
- **Granularity**: Let Claude decide patch size naturally based on the goal.
  Track size in the archive for later analysis, but don't prescribe distributions.
- **Intent tags**: Nice for post-hoc analysis but not load-bearing.
  Add when archive analysis becomes valuable.
- **Strategy portfolio**: Start with one good prompt. Add strategies only when
  data shows the single strategy plateaus. The "Simple Baselines" research
  shows problem formulation matters more than strategy diversity.

## v2+ action types

When data justifies it:
- **Test changes**: Improving the evaluation surface itself
- **Config changes**: Compiler flags, runtime parameters
- **Meta-actions**: Changing the generation prompt/strategy (requires isolation from reward gaming)
