"""Invoke claude CLI and capture results."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from .config import ClaudeConfig
from .types import ClaudeResult, CostRecord


def _parse_diff_numstat(workdir: str) -> tuple[dict[str, tuple[int, int]], int, int]:
    """Run git diff --numstat HEAD in workdir and parse results.

    Returns (file_stats, total_added, total_removed).
    """
    proc = subprocess.run(
        ["git", "diff", "--numstat", "HEAD"],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    stats: dict[str, tuple[int, int]] = {}
    total_added = 0
    total_removed = 0

    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added_str, removed_str, filepath = parts
            try:
                added = int(added_str) if added_str != "-" else 0
                removed = int(removed_str) if removed_str != "-" else 0
            except ValueError:
                continue
            stats[filepath] = (added, removed)
            total_added += added
            total_removed += removed

    return stats, total_added, total_removed


def _parse_cost_from_output(raw_output: str) -> CostRecord:
    """Try to extract cost info from claude's JSON output."""
    cost = CostRecord()
    try:
        data = json.loads(raw_output)
        if isinstance(data, dict):
            cost.input_tokens = data.get("input_tokens", 0)
            cost.output_tokens = data.get("output_tokens", 0)
            cost.api_cost_usd = data.get("cost_usd", 0.0)
    except (json.JSONDecodeError, TypeError):
        # Try to grep for cost patterns in non-JSON output
        for line in raw_output.splitlines():
            if "cost" in line.lower() and "$" in line:
                match = re.search(r"\$?([\d.]+)", line)
                if match:
                    try:
                        cost.api_cost_usd = float(match.group(1))
                    except ValueError:
                        pass
    return cost


def invoke(
    prompt: str,
    system_context: str,
    worktree_path: str | Path,
    config: ClaudeConfig,
) -> ClaudeResult:
    """Invoke claude -p in a worktree directory.

    Runs `claude -p` with the given prompt, captures output and git diff.
    """
    worktree_path = str(Path(worktree_path).resolve())

    cmd = ["claude", "-p", "--output-format", "json"]
    if config.allowed_tools:
        cmd.extend(["--allowedTools", config.allowed_tools])
    if config.max_turns:
        cmd.extend(["--max-turns", str(config.max_turns)])

    full_prompt = prompt
    if system_context:
        full_prompt = f"{system_context}\n\n---\n\n{full_prompt}"

    # Strip CLAUDECODE env var to allow nested invocations
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            input=full_prompt,
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min hard timeout
            env=env,
        )
        raw_output = proc.stdout
        error = proc.stderr if proc.returncode != 0 else ""
        success = proc.returncode == 0
    except subprocess.TimeoutExpired as e:
        raw_output = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        error = "claude invocation timed out after 600s"
        success = False
    except FileNotFoundError:
        return ClaudeResult(
            success=False,
            error="claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
        )

    duration = time.monotonic() - start

    # Parse cost from output
    cost = _parse_cost_from_output(raw_output)
    cost.duration_s = round(duration, 3)

    if not success:
        return ClaudeResult(
            success=False,
            cost=cost,
            raw_output=raw_output,
            error=error,
        )

    # Capture diff
    diff_stat, total_added, total_removed = _parse_diff_numstat(worktree_path)

    return ClaudeResult(
        success=True,
        diff_stat=diff_stat,
        total_added=total_added,
        total_removed=total_removed,
        cost=cost,
        raw_output=raw_output,
    )
