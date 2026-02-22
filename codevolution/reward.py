"""Gate checking and scalar reward computation."""

from __future__ import annotations

from .config import GateConfig
from .types import BaselineRecord, TierResult


def check_gates(
    tier_results: list[TierResult],
    gates: list[GateConfig],
) -> tuple[bool, str]:
    """Check all gates against tier results.

    Returns (all_passed, failure_reason). failure_reason is empty string if all passed.
    """
    tier_passed: dict[int, bool] = {}
    merged_metrics: dict[str, float] = {}

    for tr in tier_results:
        # A tier passes if all its steps pass
        if tr.tier not in tier_passed:
            tier_passed[tr.tier] = True
        if not tr.passed:
            tier_passed[tr.tier] = False
        merged_metrics.update(tr.metrics)

    for gate in gates:
        # Check tier passed
        if not tier_passed.get(gate.tier, False):
            return False, f"Gate '{gate.name}' failed: tier {gate.tier} did not pass"

        # Check optional condition (e.g. "metric_name > 0.95")
        if gate.condition:
            ok, reason = _eval_condition(gate.condition, merged_metrics)
            if not ok:
                return False, f"Gate '{gate.name}' condition failed: {reason}"

    return True, ""


def _eval_condition(condition: str, metrics: dict[str, float]) -> tuple[bool, str]:
    """Parse and evaluate a simple condition like 'metric_name > 0.95'.

    Supports: >, <, >=, <=, ==, !=
    No eval() - manual parsing only.
    """
    operators = [">=", "<=", "!=", "==", ">", "<"]
    for op in operators:
        if op in condition:
            parts = condition.split(op, 1)
            if len(parts) != 2:
                return False, f"Cannot parse condition: {condition}"
            metric_name = parts[0].strip()
            try:
                threshold = float(parts[1].strip())
            except ValueError:
                return False, f"Cannot parse threshold in: {condition}"

            if metric_name not in metrics:
                return False, f"Metric '{metric_name}' not found"

            value = metrics[metric_name]
            result = _compare(value, op, threshold)
            if not result:
                return False, f"{metric_name}={value} {op} {threshold} is false"
            return True, ""

    return False, f"No operator found in condition: {condition}"


def _compare(value: float, op: str, threshold: float) -> bool:
    match op:
        case ">":
            return value > threshold
        case "<":
            return value < threshold
        case ">=":
            return value >= threshold
        case "<=":
            return value <= threshold
        case "==":
            return value == threshold
        case "!=":
            return value != threshold
        case _:
            return False


def compute_reward(
    metrics: dict[str, float],
    baseline: BaselineRecord,
    target_metric: str,
    direction: str,
    loc_delta: int,
    patch_size_penalty: float,
    max_loc_delta: int = 0,
) -> float:
    """Compute scalar reward: improvement_pct - patch_penalty - overflow_penalty.

    improvement_pct is relative to baseline mean for the target metric.
    direction: "higher" means larger values are better, "lower" means smaller.
    Lines over max_loc_delta get penalized at 10x the base rate.
    """
    baseline_value = baseline.metrics_mean.get(target_metric)
    current_value = metrics.get(target_metric)

    if baseline_value is None or current_value is None:
        return 0.0

    if baseline_value == 0:
        # Avoid division by zero; if baseline is 0, any positive change is +100%
        if current_value == 0:
            improvement_pct = 0.0
        elif direction == "higher":
            improvement_pct = 100.0 if current_value > 0 else -100.0
        else:
            improvement_pct = 100.0 if current_value < 0 else -100.0
    else:
        if direction == "higher":
            improvement_pct = ((current_value - baseline_value) / abs(baseline_value)) * 100.0
        else:
            # For "lower is better", improvement = how much it decreased
            improvement_pct = ((baseline_value - current_value) / abs(baseline_value)) * 100.0

    penalty = patch_size_penalty * abs(loc_delta)
    # Lines over the limit get a steep additional penalty (10x base rate)
    if max_loc_delta > 0 and abs(loc_delta) > max_loc_delta:
        overflow = abs(loc_delta) - max_loc_delta
        penalty += patch_size_penalty * 10 * overflow
    return round(improvement_pct - penalty, 4)
