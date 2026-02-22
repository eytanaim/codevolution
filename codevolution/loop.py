"""Main SCS loop: orchestrates one experiment."""

from __future__ import annotations

import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Optional

from .archive import init_archive, load_archive_state, load_baseline, save_attempt, save_baseline, save_candidate_files
from .baseline import calibrate
from .claude import invoke
from .config import ExperimentConfig
from .context import build_prompt
from .evaluate import run_all_tiers
from .reward import check_gates, compute_reward
from .types import ArchiveState, AttemptRecord, BaselineRecord
from .worktree import cleanup_worktree, create_worktree


def _log(msg: str) -> None:
    print(f"[codevolution] {msg}", flush=True)


def _check_budget(
    config: ExperimentConfig,
    iteration: int,
    total_cost_usd: float,
    start_time: float,
) -> Optional[str]:
    """Check if any budget limit is exceeded. Returns reason string or None."""
    if iteration >= config.budget.max_iterations:
        return f"max_iterations reached ({config.budget.max_iterations})"
    if total_cost_usd >= config.budget.max_api_cost_usd:
        return f"max_api_cost_usd reached (${total_cost_usd:.2f} >= ${config.budget.max_api_cost_usd})"
    elapsed_hours = (time.monotonic() - start_time) / 3600
    if elapsed_hours >= config.budget.max_wall_clock_hours:
        return f"max_wall_clock_hours reached ({elapsed_hours:.2f}h >= {config.budget.max_wall_clock_hours}h)"
    return None


def _run_single_attempt(
    config: ExperimentConfig,
    baseline_record: BaselineRecord,
    archive_state: ArchiveState,
    iteration: int,
    archive_lock: threading.Lock,
) -> AttemptRecord:
    """Run a single iteration: worktree -> invoke -> evaluate -> save."""
    worktree = create_worktree(config.target_repo, config.base_commit, f"iter-{iteration}-{uuid.uuid4().hex[:4]}")
    try:
        prompt, system_context = build_prompt(config, baseline_record, archive_state)

        _log(f"[iter {iteration}] Invoking claude...")
        claude_result = invoke(prompt, system_context, worktree, config.claude)

        attempt_id = str(uuid.uuid4())[:8]

        if not claude_result.success:
            _log(f"[iter {iteration}] Claude failed: {claude_result.error}")
            record = AttemptRecord(
                attempt_id=attempt_id,
                iteration=iteration,
                cost=claude_result.cost,
                failure_reason=f"claude error: {claude_result.error}",
            )
            with archive_lock:
                save_attempt(config.archive_dir, record)
            return record

        # Check scope limits
        loc_delta = claude_result.total_added + claude_result.total_removed
        if len(claude_result.diff_stat) > config.scope.max_files_changed:
            _log(f"[iter {iteration}] Too many files changed: {len(claude_result.diff_stat)} > {config.scope.max_files_changed}")
            record = AttemptRecord(
                attempt_id=attempt_id,
                iteration=iteration,
                diff_stat=claude_result.diff_stat,
                total_added=claude_result.total_added,
                total_removed=claude_result.total_removed,
                cost=claude_result.cost,
                failure_reason="scope: too many files changed",
            )
            with archive_lock:
                save_attempt(config.archive_dir, record)
            return record

        if loc_delta > config.scope.max_loc_delta:
            _log(f"[iter {iteration}] LOC over target: {loc_delta} > {config.scope.max_loc_delta} (penalty applies)")

        # Evaluate
        _log(f"[iter {iteration}] Running evaluation pipeline...")
        tier_results, merged_metrics, all_tiers_passed = run_all_tiers(config.tiers, worktree)

        # Check gates
        gates_passed, gate_failure = check_gates(tier_results, config.gates)

        # Compute reward
        reward = 0.0
        if gates_passed and all_tiers_passed:
            reward = compute_reward(
                merged_metrics,
                baseline_record,
                config.target_metric,
                config.metric_direction,
                loc_delta,
                config.reward.patch_size_penalty,
                config.scope.max_loc_delta,
            )

        failure_reason = ""
        if not all_tiers_passed:
            failed_steps = [r.step_name for r in tier_results if not r.passed]
            failure_reason = f"eval failed: {failed_steps}"
        elif not gates_passed:
            failure_reason = f"gate failed: {gate_failure}"

        record = AttemptRecord(
            attempt_id=attempt_id,
            iteration=iteration,
            tier_results=tier_results,
            all_tiers_passed=all_tiers_passed and gates_passed,
            reward=reward,
            diff_stat=claude_result.diff_stat,
            total_added=claude_result.total_added,
            total_removed=claude_result.total_removed,
            cost=claude_result.cost,
            failure_reason=failure_reason,
            metrics=merged_metrics,
        )

        with archive_lock:
            save_attempt(config.archive_dir, record)
            if record.all_tiers_passed:
                candidate_dir = save_candidate_files(
                    config.archive_dir, attempt_id, worktree, claude_result.diff_stat
                )
                _log(f"[iter {iteration}] SUCCESS: reward={reward:.2f}, metrics={merged_metrics}")
                _log(f"[iter {iteration}] Candidate files saved to {candidate_dir}")
            else:
                _log(f"[iter {iteration}] FAILED: {failure_reason}")

        return record
    finally:
        cleanup_worktree(config.target_repo, worktree)


def run_experiment(config: ExperimentConfig) -> Optional[AttemptRecord]:
    """Run the full SCS experiment loop.

    Returns the best attempt record, or None if no successful attempt.
    Uses a sliding window of concurrent workers — as soon as one finishes,
    a new one is submitted, keeping all worker slots full.
    """
    archive_path = init_archive(config.archive_dir)
    _log(f"Experiment {config.experiment_id} starting")
    _log(f"Archive: {archive_path}")

    # Step 1: Calibrate baseline
    baseline_record = load_baseline(config.archive_dir)
    if baseline_record is None:
        _log("Calibrating baseline...")
        baseline_record = calibrate(config)
        save_baseline(config.archive_dir, baseline_record)
        _log(f"Baseline metrics: {baseline_record.metrics_mean}")
    else:
        _log(f"Loaded existing baseline: {baseline_record.metrics_mean}")

    # Step 2: Main loop — sliding window of workers
    start_time = time.monotonic()
    archive_state = load_archive_state(config.archive_dir, config.target_metric, config.metric_direction)
    archive_lock = threading.Lock()

    workers = config.budget.max_candidates_per_iteration
    max_iterations = config.budget.max_iterations
    next_iteration = 0
    completed_count = 0

    _log(f"Running up to {max_iterations} iterations with {workers} concurrent workers")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        in_flight: dict[Future, int] = {}

        # Seed the pool
        while next_iteration < max_iterations and len(in_flight) < workers:
            archive_state = load_archive_state(config.archive_dir, config.target_metric, config.metric_direction)
            budget_reason = _check_budget(config, next_iteration, archive_state.total_cost_usd, start_time)
            if budget_reason:
                _log(f"Budget exhausted: {budget_reason}")
                break
            future = pool.submit(
                _run_single_attempt, config, baseline_record, archive_state, next_iteration, archive_lock,
            )
            in_flight[future] = next_iteration
            _log(f"[iter {next_iteration}] Submitted (in-flight: {len(in_flight)})")
            next_iteration += 1

        # Process completions and refill
        while in_flight:
            # Wait for the next completion
            done_iter = next(as_completed(in_flight))
            iteration = in_flight.pop(done_iter)
            try:
                record = done_iter.result()
                status = "PASS" if record.all_tiers_passed else "FAIL"
                _log(f"[iter {iteration}] Completed: {status} (reward={record.reward:.2f})")
            except Exception as exc:
                _log(f"[iter {iteration}] Exception: {exc}")
            completed_count += 1

            # Submit next if budget allows
            if next_iteration < max_iterations:
                archive_state = load_archive_state(config.archive_dir, config.target_metric, config.metric_direction)
                budget_reason = _check_budget(config, next_iteration, archive_state.total_cost_usd, start_time)
                if budget_reason:
                    _log(f"Budget exhausted: {budget_reason} — draining {len(in_flight)} in-flight workers")
                else:
                    future = pool.submit(
                        _run_single_attempt, config, baseline_record, archive_state, next_iteration, archive_lock,
                    )
                    in_flight[future] = next_iteration
                    _log(f"[iter {next_iteration}] Submitted (in-flight: {len(in_flight)})")
                    next_iteration += 1

    # Report
    archive_state = load_archive_state(config.archive_dir, config.target_metric, config.metric_direction)
    _log("--- Experiment Complete ---")
    _log(f"Total attempts: {len(archive_state.attempts)}")
    _log(f"Total cost: ${archive_state.total_cost_usd:.2f}")

    if archive_state.best:
        _log(f"Best reward: {archive_state.best.reward:.2f}")
        _log(f"Best metrics: {archive_state.best.metrics}")
    else:
        _log("No successful attempts")

    return archive_state.best
