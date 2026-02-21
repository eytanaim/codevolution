"""Load and validate experiment configuration from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TierStepConfig:
    name: str
    command: str
    timeout_s: int = 120


@dataclass
class TierConfig:
    tier: int
    steps: list[TierStepConfig] = field(default_factory=list)


@dataclass
class GateConfig:
    name: str
    tier: int
    condition: str = ""  # optional: "metric_name > 0.95" style


@dataclass
class RewardConfig:
    patch_size_penalty: float = 0.01


@dataclass
class BudgetConfig:
    max_iterations: int = 20
    max_candidates_per_iteration: int = 1
    max_wall_clock_hours: float = 4.0
    max_api_cost_usd: float = 50.0


@dataclass
class BaselineConfig:
    runs: int = 5


@dataclass
class ClaudeConfig:
    allowed_tools: str = ""
    max_turns: int = 20


@dataclass
class ScopeConfig:
    allowed_paths: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    max_files_changed: int = 10
    max_loc_delta: int = 400


@dataclass
class ExperimentConfig:
    experiment_id: str
    target_repo: str
    base_commit: str
    goal: str
    target_metric: str
    metric_direction: str  # "higher" or "lower"
    tiers: list[TierConfig]
    gates: list[GateConfig]
    scope: ScopeConfig = field(default_factory=ScopeConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    baseline: BaselineConfig = field(default_factory=BaselineConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    archive_dir: str = "archive"


class ConfigError(Exception):
    pass


def _parse_tier_steps(raw_steps: list[dict]) -> list[TierStepConfig]:
    steps = []
    for s in raw_steps:
        if "name" not in s or "command" not in s:
            raise ConfigError(f"Tier step missing 'name' or 'command': {s}")
        steps.append(TierStepConfig(
            name=s["name"],
            command=s["command"],
            timeout_s=s.get("timeout_s", 120),
        ))
    return steps


def _parse_tiers(raw_tiers: list[dict]) -> list[TierConfig]:
    tiers = []
    for t in raw_tiers:
        if "tier" not in t or "steps" not in t:
            raise ConfigError(f"Tier missing 'tier' or 'steps': {t}")
        tiers.append(TierConfig(
            tier=t["tier"],
            steps=_parse_tier_steps(t["steps"]),
        ))
    return sorted(tiers, key=lambda x: x.tier)


def _parse_gates(raw_gates: list[dict]) -> list[GateConfig]:
    gates = []
    for g in raw_gates:
        if "name" not in g or "tier" not in g:
            raise ConfigError(f"Gate missing 'name' or 'tier': {g}")
        gates.append(GateConfig(
            name=g["name"],
            tier=g["tier"],
            condition=g.get("condition", ""),
        ))
    return gates


_REQUIRED_FIELDS = [
    "experiment_id", "target_repo", "base_commit", "goal",
    "target_metric", "metric_direction", "tiers", "gates",
]


def load_config(path: str | Path) -> ExperimentConfig:
    """Load and validate an experiment config from a YAML file."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping")

    for field_name in _REQUIRED_FIELDS:
        if field_name not in raw:
            raise ConfigError(f"Missing required field: {field_name}")

    direction = raw["metric_direction"]
    if direction not in ("higher", "lower"):
        raise ConfigError(f"metric_direction must be 'higher' or 'lower', got: {direction}")

    scope_raw = raw.get("scope", {})
    scope = ScopeConfig(
        allowed_paths=scope_raw.get("allowed_paths", []),
        forbidden_paths=scope_raw.get("forbidden_paths", []),
        max_files_changed=scope_raw.get("max_files_changed", 10),
        max_loc_delta=scope_raw.get("max_loc_delta", 400),
    )

    reward_raw = raw.get("reward", {})
    reward = RewardConfig(patch_size_penalty=reward_raw.get("patch_size_penalty", 0.01))

    budget_raw = raw.get("budget", {})
    budget = BudgetConfig(
        max_iterations=budget_raw.get("max_iterations", 20),
        max_candidates_per_iteration=budget_raw.get("max_candidates_per_iteration", 1),
        max_wall_clock_hours=budget_raw.get("max_wall_clock_hours", 4.0),
        max_api_cost_usd=budget_raw.get("max_api_cost_usd", 50.0),
    )

    baseline_raw = raw.get("baseline", {})
    baseline = BaselineConfig(runs=baseline_raw.get("runs", 5))

    claude_raw = raw.get("claude", {})
    claude = ClaudeConfig(
        allowed_tools=claude_raw.get("allowed_tools", ""),
        max_turns=claude_raw.get("max_turns", 20),
    )

    return ExperimentConfig(
        experiment_id=raw["experiment_id"],
        target_repo=raw["target_repo"],
        base_commit=raw["base_commit"],
        goal=raw["goal"],
        target_metric=raw["target_metric"],
        metric_direction=direction,
        tiers=_parse_tiers(raw["tiers"]),
        gates=_parse_gates(raw["gates"]),
        scope=scope,
        reward=reward,
        budget=budget,
        baseline=baseline,
        claude=claude,
        archive_dir=raw.get("archive_dir", "archive"),
    )
