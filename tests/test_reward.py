"""Tests for gate checking and reward computation."""

from codevolution.config import GateConfig
from codevolution.reward import check_gates, compute_reward
from codevolution.types import BaselineRecord, TierResult


def _tier_result(tier: int, passed: bool = True, metrics: dict | None = None) -> TierResult:
    return TierResult(
        tier=tier,
        step_name=f"step_{tier}",
        passed=passed,
        exit_code=0 if passed else 1,
        metrics=metrics or {},
    )


def test_gates_pass_simple():
    results = [_tier_result(0), _tier_result(1)]
    gates = [GateConfig(name="g0", tier=0), GateConfig(name="g1", tier=1)]
    passed, reason = check_gates(results, gates)
    assert passed is True
    assert reason == ""


def test_gates_fail_tier():
    results = [_tier_result(0), _tier_result(1, passed=False)]
    gates = [GateConfig(name="g0", tier=0), GateConfig(name="g1", tier=1)]
    passed, reason = check_gates(results, gates)
    assert passed is False
    assert "tier 1" in reason


def test_gates_with_condition_pass():
    results = [_tier_result(0, metrics={"accuracy": 0.98})]
    gates = [GateConfig(name="acc", tier=0, condition="accuracy >= 0.95")]
    passed, reason = check_gates(results, gates)
    assert passed is True


def test_gates_with_condition_fail():
    results = [_tier_result(0, metrics={"accuracy": 0.90})]
    gates = [GateConfig(name="acc", tier=0, condition="accuracy >= 0.95")]
    passed, reason = check_gates(results, gates)
    assert passed is False
    assert "condition failed" in reason


def test_gates_condition_metric_missing():
    results = [_tier_result(0)]
    gates = [GateConfig(name="acc", tier=0, condition="accuracy >= 0.95")]
    passed, reason = check_gates(results, gates)
    assert passed is False
    assert "not found" in reason


def test_compute_reward_higher_improvement():
    baseline = BaselineRecord(metrics_mean={"rps": 100.0})
    reward = compute_reward(
        metrics={"rps": 150.0},
        baseline=baseline,
        target_metric="rps",
        direction="higher",
        loc_delta=10,
        patch_size_penalty=0.01,
    )
    # improvement = (150-100)/100 * 100 = 50%, penalty = 0.01*10 = 0.1
    assert reward == 50.0 - 0.1


def test_compute_reward_lower_improvement():
    baseline = BaselineRecord(metrics_mean={"latency": 100.0})
    reward = compute_reward(
        metrics={"latency": 60.0},
        baseline=baseline,
        target_metric="latency",
        direction="lower",
        loc_delta=5,
        patch_size_penalty=0.01,
    )
    # improvement = (100-60)/100 * 100 = 40%, penalty = 0.01*5 = 0.05
    assert reward == 40.0 - 0.05


def test_compute_reward_regression():
    baseline = BaselineRecord(metrics_mean={"rps": 100.0})
    reward = compute_reward(
        metrics={"rps": 80.0},
        baseline=baseline,
        target_metric="rps",
        direction="higher",
        loc_delta=10,
        patch_size_penalty=0.01,
    )
    # improvement = (80-100)/100 * 100 = -20%, penalty = 0.1
    assert reward == -20.0 - 0.1


def test_compute_reward_missing_metric():
    baseline = BaselineRecord(metrics_mean={"rps": 100.0})
    reward = compute_reward(
        metrics={},
        baseline=baseline,
        target_metric="rps",
        direction="higher",
        loc_delta=10,
        patch_size_penalty=0.01,
    )
    assert reward == 0.0


def test_compute_reward_zero_baseline():
    baseline = BaselineRecord(metrics_mean={"rps": 0.0})
    reward = compute_reward(
        metrics={"rps": 50.0},
        baseline=baseline,
        target_metric="rps",
        direction="higher",
        loc_delta=0,
        patch_size_penalty=0.01,
    )
    assert reward == 100.0


def test_all_condition_operators():
    results = [_tier_result(0, metrics={"x": 5.0})]

    for cond, expected in [
        ("x > 4", True),
        ("x > 5", False),
        ("x < 6", True),
        ("x >= 5", True),
        ("x <= 5", True),
        ("x == 5", True),
        ("x != 5", False),
    ]:
        gates = [GateConfig(name="test", tier=0, condition=cond)]
        passed, _ = check_gates(results, gates)
        assert passed is expected, f"Failed for condition: {cond}"
