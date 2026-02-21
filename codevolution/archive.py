"""JSONL archive for attempt records and baselines."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .types import ArchiveState, AttemptRecord, BaselineRecord, CostRecord, TierResult


def init_archive(archive_dir: str | Path) -> Path:
    """Create archive directory structure. Returns the archive path."""
    path = Path(archive_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _serialize(obj: object) -> str:
    return json.dumps(asdict(obj), default=str)  # type: ignore[arg-type]


def _append_jsonl(filepath: Path, data: str) -> None:
    with open(filepath, "a") as f:
        f.write(data + "\n")


def save_attempt(archive_dir: str | Path, record: AttemptRecord) -> None:
    """Append an attempt record to attempts.jsonl."""
    path = Path(archive_dir) / "attempts.jsonl"
    _append_jsonl(path, _serialize(record))


def save_baseline(archive_dir: str | Path, record: BaselineRecord) -> None:
    """Write baseline record to baseline.json (overwrites)."""
    path = Path(archive_dir) / "baseline.json"
    path.write_text(json.dumps(asdict(record), indent=2))


def _parse_tier_result(d: dict) -> TierResult:
    return TierResult(**d)


def _parse_cost_record(d: dict) -> CostRecord:
    return CostRecord(**d)


def _parse_diff_stat(raw: dict) -> dict[str, tuple[int, int]]:
    return {k: tuple(v) for k, v in raw.items()}  # type: ignore[misc]


def _parse_attempt(d: dict) -> AttemptRecord:
    return AttemptRecord(
        attempt_id=d["attempt_id"],
        iteration=d["iteration"],
        tier_results=[_parse_tier_result(tr) for tr in d.get("tier_results", [])],
        all_tiers_passed=d.get("all_tiers_passed", False),
        reward=d.get("reward", 0.0),
        diff_stat=_parse_diff_stat(d.get("diff_stat", {})),
        total_added=d.get("total_added", 0),
        total_removed=d.get("total_removed", 0),
        cost=_parse_cost_record(d.get("cost", {})),
        failure_reason=d.get("failure_reason", ""),
        metrics=d.get("metrics", {}),
    )


def load_archive_state(archive_dir: str | Path, target_metric: str, direction: str) -> ArchiveState:
    """Load all attempts from JSONL and compute archive state."""
    path = Path(archive_dir) / "attempts.jsonl"
    if not path.exists():
        return ArchiveState()

    attempts: list[AttemptRecord] = []
    total_cost = 0.0

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        record = _parse_attempt(json.loads(line))
        attempts.append(record)
        total_cost += record.cost.api_cost_usd

    passed = [a for a in attempts if a.all_tiers_passed]
    failures = [a for a in attempts if not a.all_tiers_passed]

    best: Optional[AttemptRecord] = None
    if passed:
        if direction == "higher":
            best = max(passed, key=lambda a: a.metrics.get(target_metric, 0.0))
        else:
            best = min(passed, key=lambda a: a.metrics.get(target_metric, float("inf")))

    return ArchiveState(
        attempts=attempts,
        best=best,
        failures=failures,
        total_cost_usd=total_cost,
    )


def load_baseline(archive_dir: str | Path) -> Optional[BaselineRecord]:
    """Load baseline record from baseline.json if it exists."""
    path = Path(archive_dir) / "baseline.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    return BaselineRecord(
        metrics_mean=d.get("metrics_mean", {}),
        metrics_stddev=d.get("metrics_stddev", {}),
        runs=d.get("runs", 0),
        all_tiers_passed=d.get("all_tiers_passed", False),
        tier_results=[_parse_tier_result(tr) for tr in d.get("tier_results", [])],
    )
