"""Tests for archive read/write."""

import tempfile
from pathlib import Path

from codevolution.archive import (
    init_archive,
    load_archive_state,
    load_baseline,
    save_attempt,
    save_baseline,
)
from codevolution.types import AttemptRecord, BaselineRecord, CostRecord, TierResult


def _tmp_archive() -> Path:
    return Path(tempfile.mkdtemp(prefix="codevolution-test-archive-"))


def _make_attempt(
    attempt_id: str = "a1",
    iteration: int = 0,
    passed: bool = True,
    reward: float = 10.0,
    metric_value: float = 100.0,
    cost_usd: float = 0.5,
) -> AttemptRecord:
    return AttemptRecord(
        attempt_id=attempt_id,
        iteration=iteration,
        tier_results=[
            TierResult(tier=0, step_name="check", passed=passed, exit_code=0 if passed else 1),
        ],
        all_tiers_passed=passed,
        reward=reward,
        diff_stat={"src/fib.py": (5, 3)},
        total_added=5,
        total_removed=3,
        cost=CostRecord(api_cost_usd=cost_usd),
        failure_reason="" if passed else "eval failed",
        metrics={"rps": metric_value},
    )


def test_init_archive_creates_directory():
    archive = _tmp_archive()
    result = init_archive(archive)
    assert result.exists()
    assert result.is_dir()


def test_save_and_load_attempt():
    archive = _tmp_archive()
    init_archive(archive)

    record = _make_attempt()
    save_attempt(archive, record)

    state = load_archive_state(archive, "rps", "higher")
    assert len(state.attempts) == 1
    assert state.attempts[0].attempt_id == "a1"
    assert state.attempts[0].metrics["rps"] == 100.0
    assert state.total_cost_usd == 0.5


def test_best_candidate_selection_higher():
    archive = _tmp_archive()
    init_archive(archive)

    save_attempt(archive, _make_attempt("a1", 0, True, 10.0, 100.0))
    save_attempt(archive, _make_attempt("a2", 1, True, 20.0, 200.0))
    save_attempt(archive, _make_attempt("a3", 2, True, 5.0, 50.0))

    state = load_archive_state(archive, "rps", "higher")
    assert state.best is not None
    assert state.best.attempt_id == "a2"


def test_best_candidate_selection_lower():
    archive = _tmp_archive()
    init_archive(archive)

    save_attempt(archive, _make_attempt("a1", 0, True, 10.0, 100.0))
    save_attempt(archive, _make_attempt("a2", 1, True, 20.0, 50.0))

    state = load_archive_state(archive, "rps", "lower")
    assert state.best is not None
    assert state.best.attempt_id == "a2"


def test_failures_separated():
    archive = _tmp_archive()
    init_archive(archive)

    save_attempt(archive, _make_attempt("a1", 0, True, 10.0, 100.0))
    save_attempt(archive, _make_attempt("a2", 1, False, 0.0, 0.0))

    state = load_archive_state(archive, "rps", "higher")
    assert len(state.failures) == 1
    assert state.failures[0].attempt_id == "a2"
    assert state.best is not None
    assert state.best.attempt_id == "a1"


def test_empty_archive():
    archive = _tmp_archive()
    init_archive(archive)

    state = load_archive_state(archive, "rps", "higher")
    assert len(state.attempts) == 0
    assert state.best is None
    assert state.total_cost_usd == 0.0


def test_save_and_load_baseline():
    archive = _tmp_archive()
    init_archive(archive)

    baseline = BaselineRecord(
        metrics_mean={"rps": 100.0, "elapsed": 0.5},
        metrics_stddev={"rps": 5.0, "elapsed": 0.02},
        runs=5,
        all_tiers_passed=True,
    )
    save_baseline(archive, baseline)

    loaded = load_baseline(archive)
    assert loaded is not None
    assert loaded.metrics_mean["rps"] == 100.0
    assert loaded.metrics_stddev["rps"] == 5.0
    assert loaded.runs == 5


def test_load_baseline_not_found():
    archive = _tmp_archive()
    init_archive(archive)
    assert load_baseline(archive) is None


def test_diff_stat_roundtrip():
    archive = _tmp_archive()
    init_archive(archive)

    record = _make_attempt()
    save_attempt(archive, record)

    state = load_archive_state(archive, "rps", "higher")
    assert state.attempts[0].diff_stat["src/fib.py"] == (5, 3)
