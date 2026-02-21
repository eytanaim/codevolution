# Safety Spec

A smart patch generator will find shortcuts if you leave doors open.
This spec defines the guardrails that keep the system honest.

## Threat model

The "adversary" is not malicious - it's an optimizer doing exactly what you
reward it for, which may not be what you intended. Classic Goodhart's Law.

Concrete risks:
- Disabling tests to avoid failures
- Adding benchmark-specific conditionals
- Swallowing exceptions to hide errors
- Gaming metrics without real improvement
- Huge rewrites that happen to score well but are unmaintainable
- Editing the evaluation infrastructure itself

## Patch policy checks (static, pre-evaluation)

Reject patches that:

| Check | What it catches |
|-------|----------------|
| Disabled tests | `@skip`, `@pytest.mark.skip`, `.only`, commented-out tests |
| Weakened assertions | Removed asserts, loosened thresholds |
| Benchmark conditionals | `if benchmark_mode:`, `if os.environ.get('BENCH')` |
| Swallowed exceptions | Bare `except: pass`, `|| true`, empty catch blocks |
| Eval infrastructure edits | Changes to evaluator code, reward config, CI scripts |
| Removed logging | Deleted log statements used by evaluators |
| Forbidden file edits | Anything outside experiment scope |

These are cheap regex/AST checks that run in Tier 0.

## Evaluation isolation

Every candidate is evaluated in an isolated environment:

- **Clean worktree**: fresh `git worktree` or clone, not the working directory
- **Container isolation**: Docker/OCI container with resource limits
- **No network**: unless explicitly required by the benchmark
- **Deterministic seeds**: random seeds pinned where possible
- **Resource limits**: CPU, memory, time caps per tier
- **Read-only source**: candidate code is read-only during evaluation

The candidate cannot influence the evaluation environment.

## Holdout evaluation (v2+ anti-overfitting)

When added, holdout includes checks the system doesn't see during optimization:

- Different test inputs
- Different benchmark scenarios
- Metrics computed differently

In v1, human review serves as the holdout function.

## Human-gated promotion

```
Experiment best ──── Human review required ────> Merge to main
```

In v1, promotion to main requires human approval:
- Review the diff
- Review the metrics
- Review the archive history (how did we get here?)
- Optionally: run manual tests

Auto-promotion within the experiment frontier is fine.
Auto-merge to main is not.

## Audit trail

In v1, the archive IS the audit trail. Every attempt, its results,
costs, and failure reasons are recorded in JSONL. Git history provides
the rest. No separate audit logging system needed.

## Escalation triggers

The system should pause and notify a human when:

| Trigger | Response |
|---------|----------|
| Reward plateau (5+ iterations) | Flag for review |
| Budget > 80% consumed | Warning |
| Unexpected evaluation failures | Pause + investigate |
| Candidate attempts to modify eval code | Hard reject + flag |
| All candidates in an iteration fail Tier 0 | Review generation strategy |
| All candidates in 3 consecutive iterations produce similar patches | Flag for review |

## What we explicitly do NOT do (v1)

- No auto-deployment
- No auto-dependency upgrades
- No modifications to CI/CD pipelines
- No changes outside experiment scope
- No network access during evaluation (unless benchmark requires it)
- No execution of candidate code outside the eval sandbox
