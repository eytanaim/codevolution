"""Calibrate baseline by running evaluation on unmodified code."""

from __future__ import annotations

import statistics
from collections import defaultdict

from .config import ExperimentConfig
from .evaluate import run_all_tiers
from .types import BaselineRecord
from .worktree import cleanup_worktree, create_worktree


def calibrate(config: ExperimentConfig) -> BaselineRecord:
    """Run evaluation pipeline on unmodified code to establish baseline.

    1. Creates a worktree at base_commit.
    2. Runs all tiers once to verify they pass.
    3. Runs the final tier (metrics tier) N times to compute mean/stddev.
    4. Cleans up worktree.

    Returns BaselineRecord with aggregated stats.
    """
    worktree = create_worktree(config.target_repo, config.base_commit, "baseline")

    try:
        # First run: verify all tiers pass
        all_results, merged_metrics, all_passed = run_all_tiers(config.tiers, worktree)

        if not all_passed:
            failure_steps = [r.step_name for r in all_results if not r.passed]
            raise RuntimeError(
                f"Baseline calibration failed: steps {failure_steps} did not pass. "
                "Fix the base code before running evolution."
            )

        # Collect metrics from multiple runs of the metrics tier (last tier)
        metrics_tier = max(config.tiers, key=lambda t: t.tier)
        all_metric_values: dict[str, list[float]] = defaultdict(list)

        # Include first run's metrics
        for r in all_results:
            for k, v in r.metrics.items():
                all_metric_values[k].append(v)

        # Additional runs for statistical confidence
        for _ in range(config.baseline.runs - 1):
            from .evaluate import run_tier
            tier_results = run_tier(metrics_tier, worktree)
            for r in tier_results:
                for k, v in r.metrics.items():
                    all_metric_values[k].append(v)

        # Compute stats
        metrics_mean: dict[str, float] = {}
        metrics_stddev: dict[str, float] = {}

        for name, values in all_metric_values.items():
            metrics_mean[name] = round(statistics.mean(values), 6)
            if len(values) > 1:
                metrics_stddev[name] = round(statistics.stdev(values), 6)
            else:
                metrics_stddev[name] = 0.0

        return BaselineRecord(
            metrics_mean=metrics_mean,
            metrics_stddev=metrics_stddev,
            runs=config.baseline.runs,
            all_tiers_passed=True,
            tier_results=all_results,
        )

    finally:
        cleanup_worktree(config.target_repo, worktree)
