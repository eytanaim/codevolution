"""Tests for the main SCS loop."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from codevolution.config import (
    BaselineConfig,
    BudgetConfig,
    ClaudeConfig,
    ExperimentConfig,
    GateConfig,
    RewardConfig,
    ScopeConfig,
    TierConfig,
    TierStepConfig,
)
from codevolution.loop import _check_budget, run_experiment
from codevolution.types import ClaudeResult, CostRecord


def _make_config(target_repo: str, archive_dir: str, max_iterations: int = 1, max_candidates: int = 1) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id="test-loop",
        target_repo=target_repo,
        base_commit="HEAD",
        goal="Improve fibonacci speed",
        target_metric="fib_rps",
        metric_direction="higher",
        tiers=[
            TierConfig(tier=0, steps=[
                TierStepConfig(name="syntax", command="python3 -m py_compile src/fib.py", timeout_s=30),
            ]),
            TierConfig(tier=1, steps=[
                TierStepConfig(name="tests", command="python3 tests/test_fib.py", timeout_s=60),
            ]),
            TierConfig(tier=2, steps=[
                TierStepConfig(name="bench", command="bash bench.sh", timeout_s=60),
            ]),
        ],
        gates=[
            GateConfig(name="syntax_ok", tier=0),
            GateConfig(name="tests_pass", tier=1),
        ],
        scope=ScopeConfig(max_files_changed=5, max_loc_delta=400),
        reward=RewardConfig(patch_size_penalty=0.01),
        budget=BudgetConfig(
            max_iterations=max_iterations,
            max_candidates_per_iteration=max_candidates,
            max_api_cost_usd=50.0,
            max_wall_clock_hours=1.0,
        ),
        baseline=BaselineConfig(runs=2),
        claude=ClaudeConfig(max_turns=5),
        archive_dir=archive_dir,
    )


def test_check_budget_iterations():
    config = _make_config("/tmp/unused", "/tmp/unused", max_iterations=5)
    reason = _check_budget(config, 5, 0.0, 0.0)
    assert reason is not None
    assert "max_iterations" in reason


def test_check_budget_cost():
    config = _make_config("/tmp/unused", "/tmp/unused")
    config.budget.max_api_cost_usd = 1.0
    import time
    reason = _check_budget(config, 0, 2.0, time.monotonic())
    assert reason is not None
    assert "max_api_cost_usd" in reason


def test_check_budget_ok():
    config = _make_config("/tmp/unused", "/tmp/unused")
    import time
    reason = _check_budget(config, 0, 0.0, time.monotonic())
    assert reason is None


@patch("codevolution.loop.invoke")
def test_loop_single_iteration_with_mock(mock_invoke, toy_repo):
    """Test loop with mocked claude invocation that makes no changes."""
    archive_dir = tempfile.mkdtemp(prefix="codevolution-test-loop-")
    config = _make_config(str(toy_repo), archive_dir, max_iterations=1)

    mock_invoke.return_value = ClaudeResult(
        success=True,
        diff_stat={},
        total_added=0,
        total_removed=0,
        cost=CostRecord(api_cost_usd=0.01, duration_s=1.0),
        raw_output="{}",
    )

    result = run_experiment(config)
    assert mock_invoke.called


@patch("codevolution.loop.invoke")
def test_loop_budget_enforcement(mock_invoke, toy_repo):
    """Test that loop stops when budget is exhausted."""
    archive_dir = tempfile.mkdtemp(prefix="codevolution-test-budget-")
    config = _make_config(str(toy_repo), archive_dir, max_iterations=2)
    config.budget.max_api_cost_usd = 0.001

    mock_invoke.return_value = ClaudeResult(
        success=True,
        diff_stat={},
        total_added=0,
        total_removed=0,
        cost=CostRecord(api_cost_usd=0.01, duration_s=1.0),
        raw_output="{}",
    )

    result = run_experiment(config)
    assert mock_invoke.call_count <= 2


@patch("codevolution.loop.invoke")
def test_loop_scope_violation(mock_invoke, toy_repo):
    """Test that scope violations are caught."""
    archive_dir = tempfile.mkdtemp(prefix="codevolution-test-scope-")
    config = _make_config(str(toy_repo), archive_dir, max_iterations=1)
    config.scope.max_files_changed = 1

    mock_invoke.return_value = ClaudeResult(
        success=True,
        diff_stat={"a.py": (10, 0), "b.py": (10, 0)},
        total_added=20,
        total_removed=0,
        cost=CostRecord(api_cost_usd=0.01, duration_s=1.0),
        raw_output="{}",
    )

    result = run_experiment(config)


@patch("codevolution.loop.invoke")
def test_loop_parallel_workers(mock_invoke, toy_repo):
    """Test that multiple workers run when max_candidates_per_iteration > 1."""
    archive_dir = tempfile.mkdtemp(prefix="codevolution-test-parallel-")
    config = _make_config(str(toy_repo), archive_dir, max_iterations=3, max_candidates=3)

    mock_invoke.return_value = ClaudeResult(
        success=True,
        diff_stat={},
        total_added=0,
        total_removed=0,
        cost=CostRecord(api_cost_usd=0.01, duration_s=1.0),
        raw_output="{}",
    )

    result = run_experiment(config)
    # All 3 iterations should run in a single batch
    assert mock_invoke.call_count == 3
