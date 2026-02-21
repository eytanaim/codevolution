"""Run tiered evaluation pipeline and parse metrics."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from .config import TierConfig
from .types import TierResult

METRIC_PATTERN = re.compile(r"^METRIC:(\w+)=([\d.eE+\-]+)$", re.MULTILINE)


def parse_metrics(output: str) -> dict[str, float]:
    """Extract METRIC:name=value pairs from command output."""
    metrics: dict[str, float] = {}
    for match in METRIC_PATTERN.finditer(output):
        name = match.group(1)
        try:
            metrics[name] = float(match.group(2))
        except ValueError:
            pass
    return metrics


def run_tier(tier_config: TierConfig, workdir: str | Path) -> list[TierResult]:
    """Run all steps in a tier. Returns TierResult for each step.

    Stops at first failure (step with non-zero exit code or timeout).
    """
    workdir = str(Path(workdir).resolve())
    results: list[TierResult] = []

    for step in tier_config.steps:
        start = time.monotonic()
        timed_out = False
        try:
            proc = subprocess.run(
                step.command,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=step.timeout_s,
            )
            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired as e:
            exit_code = -1
            stdout = e.stdout or "" if isinstance(e.stdout, str) else (e.stdout or b"").decode(errors="replace")
            stderr = e.stderr or "" if isinstance(e.stderr, str) else (e.stderr or b"").decode(errors="replace")
            timed_out = True

        duration = time.monotonic() - start
        metrics = parse_metrics(stdout)
        passed = exit_code == 0

        results.append(TierResult(
            tier=tier_config.tier,
            step_name=step.name,
            passed=passed,
            exit_code=exit_code,
            metrics=metrics,
            stdout=stdout,
            stderr=stderr,
            duration_s=round(duration, 3),
            timed_out=timed_out,
        ))

        if not passed:
            break

    return results


def run_all_tiers(
    tier_configs: list[TierConfig],
    workdir: str | Path,
) -> tuple[list[TierResult], dict[str, float], bool]:
    """Run all tiers in order. Early-stop on first tier failure.

    Returns (all_results, merged_metrics, all_passed).
    """
    all_results: list[TierResult] = []
    merged_metrics: dict[str, float] = {}
    all_passed = True

    for tier_config in sorted(tier_configs, key=lambda t: t.tier):
        tier_results = run_tier(tier_config, workdir)
        all_results.extend(tier_results)

        for tr in tier_results:
            merged_metrics.update(tr.metrics)

        tier_passed = all(r.passed for r in tier_results)
        if not tier_passed:
            all_passed = False
            break

    return all_results, merged_metrics, all_passed
