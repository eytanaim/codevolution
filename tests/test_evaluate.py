"""Tests for evaluation pipeline."""

import tempfile
from pathlib import Path

from codevolution.config import TierConfig, TierStepConfig
from codevolution.evaluate import parse_metrics, run_all_tiers, run_tier


def _workdir() -> str:
    return tempfile.mkdtemp(prefix="codevolution-test-eval-")


def test_parse_metrics_basic():
    output = "some output\nMETRIC:rps=142.5\nmore output\nMETRIC:elapsed=0.035\n"
    metrics = parse_metrics(output)
    assert metrics["rps"] == 142.5
    assert metrics["elapsed"] == 0.035


def test_parse_metrics_empty():
    assert parse_metrics("no metrics here") == {}


def test_parse_metrics_scientific():
    output = "METRIC:tiny=1.5e-3\nMETRIC:big=2.5E+6\n"
    metrics = parse_metrics(output)
    assert metrics["tiny"] == 1.5e-3
    assert metrics["big"] == 2.5e6


def test_run_tier_success():
    tier = TierConfig(
        tier=0,
        steps=[TierStepConfig(name="echo", command="echo 'METRIC:x=42.0'", timeout_s=10)],
    )
    results = run_tier(tier, _workdir())
    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].metrics["x"] == 42.0
    assert results[0].exit_code == 0


def test_run_tier_failure_stops():
    tier = TierConfig(
        tier=0,
        steps=[
            TierStepConfig(name="fail", command="exit 1", timeout_s=10),
            TierStepConfig(name="never", command="echo should_not_run", timeout_s=10),
        ],
    )
    results = run_tier(tier, _workdir())
    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].step_name == "fail"


def test_run_tier_timeout():
    tier = TierConfig(
        tier=0,
        steps=[TierStepConfig(name="slow", command="sleep 10", timeout_s=1)],
    )
    results = run_tier(tier, _workdir())
    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].timed_out is True


def test_run_all_tiers_early_stop():
    tiers = [
        TierConfig(tier=0, steps=[TierStepConfig(name="ok", command="echo ok", timeout_s=10)]),
        TierConfig(tier=1, steps=[TierStepConfig(name="fail", command="exit 1", timeout_s=10)]),
        TierConfig(tier=2, steps=[TierStepConfig(name="bench", command="echo 'METRIC:x=1'", timeout_s=10)]),
    ]
    results, metrics, all_passed = run_all_tiers(tiers, _workdir())
    assert all_passed is False
    # Should have run tier 0 (ok) and tier 1 (fail), not tier 2
    step_names = [r.step_name for r in results]
    assert "ok" in step_names
    assert "fail" in step_names
    assert "bench" not in step_names


def test_run_all_tiers_success():
    tiers = [
        TierConfig(tier=0, steps=[TierStepConfig(name="check", command="echo ok", timeout_s=10)]),
        TierConfig(tier=1, steps=[TierStepConfig(name="bench", command="echo 'METRIC:rps=100'", timeout_s=10)]),
    ]
    results, metrics, all_passed = run_all_tiers(tiers, _workdir())
    assert all_passed is True
    assert metrics["rps"] == 100.0


def test_run_tier_captures_stderr():
    tier = TierConfig(
        tier=0,
        steps=[TierStepConfig(name="err", command="echo 'error msg' >&2 && exit 1", timeout_s=10)],
    )
    results = run_tier(tier, _workdir())
    assert "error msg" in results[0].stderr
