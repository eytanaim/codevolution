"""CLI entry point: python -m codevolution"""

from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config


def cmd_run(args: argparse.Namespace) -> int:
    from .loop import run_experiment

    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    best = run_experiment(config)
    return 0 if best is not None else 1


def cmd_baseline(args: argparse.Namespace) -> int:
    from .archive import init_archive, save_baseline
    from .baseline import calibrate

    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    init_archive(config.archive_dir)
    print(f"Calibrating baseline for {config.experiment_id}...")

    try:
        baseline = calibrate(config)
    except RuntimeError as e:
        print(f"Baseline calibration failed: {e}", file=sys.stderr)
        return 1

    save_baseline(config.archive_dir, baseline)
    print(f"Baseline saved to {config.archive_dir}/baseline.json")
    print(f"Metrics mean: {baseline.metrics_mean}")
    print(f"Metrics stddev: {baseline.metrics_stddev}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="codevolution",
        description="Evolutionary code optimization via Sequential Conditioned Sampling",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run an evolution experiment")
    run_parser.add_argument("config", help="Path to experiment config YAML")
    run_parser.set_defaults(func=cmd_run)

    baseline_parser = subparsers.add_parser("baseline", help="Calibrate baseline metrics")
    baseline_parser.add_argument("config", help="Path to experiment config YAML")
    baseline_parser.set_defaults(func=cmd_baseline)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
