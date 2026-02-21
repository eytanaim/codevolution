"""All dataclasses for codevolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TierResult:
    tier: int
    step_name: str
    passed: bool
    exit_code: int
    metrics: dict[str, float] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    timed_out: bool = False


@dataclass
class CostRecord:
    input_tokens: int = 0
    output_tokens: int = 0
    api_cost_usd: float = 0.0
    duration_s: float = 0.0


@dataclass
class ClaudeResult:
    success: bool
    diff_stat: dict[str, tuple[int, int]] = field(default_factory=dict)  # file -> (added, removed)
    total_added: int = 0
    total_removed: int = 0
    cost: CostRecord = field(default_factory=CostRecord)
    raw_output: str = ""
    error: str = ""


@dataclass
class AttemptRecord:
    attempt_id: str
    iteration: int
    tier_results: list[TierResult] = field(default_factory=list)
    all_tiers_passed: bool = False
    reward: float = 0.0
    diff_stat: dict[str, tuple[int, int]] = field(default_factory=dict)
    total_added: int = 0
    total_removed: int = 0
    cost: CostRecord = field(default_factory=CostRecord)
    failure_reason: str = ""
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class BaselineRecord:
    metrics_mean: dict[str, float] = field(default_factory=dict)
    metrics_stddev: dict[str, float] = field(default_factory=dict)
    runs: int = 0
    all_tiers_passed: bool = False
    tier_results: list[TierResult] = field(default_factory=list)


@dataclass
class ArchiveState:
    attempts: list[AttemptRecord] = field(default_factory=list)
    best: Optional[AttemptRecord] = None
    failures: list[AttemptRecord] = field(default_factory=list)
    total_cost_usd: float = 0.0
