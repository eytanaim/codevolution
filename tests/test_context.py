"""Tests for prompt building."""

from codevolution.config import ExperimentConfig, GateConfig, ScopeConfig, TierConfig, TierStepConfig
from codevolution.context import build_prompt
from codevolution.types import ArchiveState, AttemptRecord, BaselineRecord, CostRecord


def _config() -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id="test",
        target_repo="/tmp/repo",
        base_commit="HEAD",
        goal="Make fibonacci faster",
        target_metric="fib_rps",
        metric_direction="higher",
        tiers=[TierConfig(tier=0, steps=[TierStepConfig(name="check", command="echo ok")])],
        gates=[GateConfig(name="g", tier=0)],
        scope=ScopeConfig(allowed_paths=["src/**"], forbidden_paths=["*.lock"]),
    )


def _baseline() -> BaselineRecord:
    return BaselineRecord(
        metrics_mean={"fib_rps": 100.0, "fib_elapsed": 0.5},
        metrics_stddev={"fib_rps": 5.0, "fib_elapsed": 0.02},
        runs=5,
        all_tiers_passed=True,
    )


def test_prompt_contains_goal():
    prompt, _ = build_prompt(_config(), _baseline(), ArchiveState())
    assert "Make fibonacci faster" in prompt


def test_prompt_contains_baseline_metrics():
    prompt, _ = build_prompt(_config(), _baseline(), ArchiveState())
    assert "fib_rps=100.0" in prompt


def test_prompt_contains_target_metric():
    prompt, _ = build_prompt(_config(), _baseline(), ArchiveState())
    assert "fib_rps" in prompt
    assert "higher" in prompt


def test_system_context_contains_scope():
    _, system = build_prompt(_config(), _baseline(), ArchiveState())
    assert "src/**" in system
    assert "*.lock" in system


def test_prompt_includes_best_attempt():
    best = AttemptRecord(
        attempt_id="best1",
        iteration=3,
        all_tiers_passed=True,
        reward=25.0,
        metrics={"fib_rps": 200.0},
        diff_stat={"src/fib.py": (10, 5)},
        total_added=10,
        total_removed=5,
        cost=CostRecord(),
    )
    state = ArchiveState(attempts=[best], best=best)
    prompt, _ = build_prompt(_config(), _baseline(), state)
    assert "BEST" in prompt
    assert "best1" in prompt


def test_prompt_includes_recent_failures():
    failures = [
        AttemptRecord(
            attempt_id=f"fail{i}",
            iteration=i,
            all_tiers_passed=False,
            failure_reason=f"reason_{i}",
            metrics={},
            cost=CostRecord(),
        )
        for i in range(5)
    ]
    state = ArchiveState(failures=failures)
    prompt, _ = build_prompt(_config(), _baseline(), state)
    assert "FAILED" in prompt
    # Should only include last 2 failures
    assert "fail4" in prompt
    assert "fail3" in prompt
    assert "fail0" not in prompt
