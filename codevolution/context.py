"""Build prompts from goal + archive state + feedback."""

from __future__ import annotations

from .config import ExperimentConfig
from .types import ArchiveState, AttemptRecord, BaselineRecord


def _format_metrics(metrics: dict[str, float]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(metrics.items()))


def _format_diff_stat(record: AttemptRecord) -> str:
    if not record.diff_stat:
        return "no changes"
    lines = []
    for path, (added, removed) in sorted(record.diff_stat.items()):
        lines.append(f"  {path}: +{added}/-{removed}")
    return "\n".join(lines)


def _format_attempt_summary(record: AttemptRecord, label: str) -> str:
    parts = [f"[{label}] attempt={record.attempt_id}, iteration={record.iteration}"]
    parts.append(f"  reward={record.reward:.2f}")
    parts.append(f"  metrics: {_format_metrics(record.metrics)}")
    parts.append(f"  lines changed: +{record.total_added}/-{record.total_removed}")
    if record.failure_reason:
        parts.append(f"  failure: {record.failure_reason}")
    parts.append(f"  files:\n{_format_diff_stat(record)}")
    return "\n".join(parts)


def build_prompt(
    config: ExperimentConfig,
    baseline: BaselineRecord,
    archive_state: ArchiveState,
) -> tuple[str, str]:
    """Build the prompt and system context for claude.

    Returns (prompt, system_context).
    """
    system_parts: list[str] = []
    prompt_parts: list[str] = []

    # System context: role and constraints
    system_parts.append(
        "You are an expert software engineer optimizing code. "
        "Your goal is to improve the target metric while keeping all tests passing. "
        "Make focused, minimal changes. Prefer algorithmic improvements over cosmetic ones."
    )

    if config.scope.allowed_paths:
        system_parts.append(f"Allowed paths: {', '.join(config.scope.allowed_paths)}")
    if config.scope.forbidden_paths:
        system_parts.append(f"Forbidden paths (do NOT modify): {', '.join(config.scope.forbidden_paths)}")
    system_parts.append(f"Max files to change: {config.scope.max_files_changed}")
    system_parts.append(
        f"Target max lines changed: {config.scope.max_loc_delta} "
        f"(exceeding this incurs a steep score penalty)"
    )
    system_parts.append(
        f"You have {config.claude.max_turns} turns to complete your work. "
        f"Be direct and efficient — do not waste turns on exploration you don't need."
    )

    # Prompt: goal + baseline + archive feedback + action request
    prompt_parts.append(f"# Goal\n{config.goal}")
    prompt_parts.append(
        f"\n# Target Metric\n"
        f"Metric: {config.target_metric}\n"
        f"Direction: {config.metric_direction} is better"
    )

    # Baseline
    prompt_parts.append(
        f"\n# Baseline (current performance)\n"
        f"Metrics: {_format_metrics(baseline.metrics_mean)}\n"
        f"Stddev: {_format_metrics(baseline.metrics_stddev)}"
    )

    # Best result so far
    if archive_state.best:
        prompt_parts.append(
            f"\n# Best Result So Far\n"
            f"{_format_attempt_summary(archive_state.best, 'BEST')}"
        )

    # Recent failures (budget: max 2, keep feedback <30% of prompt)
    if archive_state.failures:
        recent_failures = archive_state.failures[-2:]
        failure_lines = ["\n# Recent Failed Attempts (learn from these)"]
        for f in recent_failures:
            failure_lines.append(_format_attempt_summary(f, "FAILED"))
        prompt_parts.append("\n".join(failure_lines))

    # Action request
    prompt_parts.append(
        "\n# Action\n"
        "Analyze the codebase and make changes to improve the target metric. "
        "Focus on algorithmic and structural improvements. "
        "Do NOT add comments, documentation, or cosmetic changes. "
        "Make the minimum changes needed for maximum improvement."
    )

    system_context = "\n".join(system_parts)
    prompt = "\n".join(prompt_parts)

    return prompt, system_context
