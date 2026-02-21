"""Tests for config loading and validation."""

import tempfile
from pathlib import Path

import pytest

from codevolution.config import ConfigError, load_config


VALID_CONFIG = """\
experiment_id: "test-001"
target_repo: "/tmp/repo"
base_commit: "HEAD"
goal: "Make it faster"
target_metric: "rps"
metric_direction: "higher"
tiers:
  - tier: 0
    steps:
      - name: "check"
        command: "echo ok"
        timeout_s: 10
gates:
  - name: "check_ok"
    tier: 0
"""


def _write_config(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def test_load_valid_config():
    path = _write_config(VALID_CONFIG)
    config = load_config(path)
    assert config.experiment_id == "test-001"
    assert config.target_metric == "rps"
    assert config.metric_direction == "higher"
    assert len(config.tiers) == 1
    assert config.tiers[0].tier == 0
    assert config.tiers[0].steps[0].name == "check"
    assert len(config.gates) == 1
    assert config.gates[0].name == "check_ok"


def test_load_config_with_all_sections():
    content = VALID_CONFIG + """\
scope:
  allowed_paths: ["src/**"]
  forbidden_paths: ["*.lock"]
  max_files_changed: 3
  max_loc_delta: 200
reward:
  patch_size_penalty: 0.05
budget:
  max_iterations: 10
  max_api_cost_usd: 25.0
baseline:
  runs: 3
claude:
  allowed_tools: "Read,Edit"
  max_turns: 15
archive_dir: "my-archive"
"""
    path = _write_config(content)
    config = load_config(path)
    assert config.scope.allowed_paths == ["src/**"]
    assert config.scope.max_files_changed == 3
    assert config.reward.patch_size_penalty == 0.05
    assert config.budget.max_iterations == 10
    assert config.baseline.runs == 3
    assert config.claude.max_turns == 15
    assert config.archive_dir == "my-archive"


def test_missing_required_field():
    content = """\
experiment_id: "test"
target_repo: "/tmp"
"""
    path = _write_config(content)
    with pytest.raises(ConfigError, match="Missing required field"):
        load_config(path)


def test_invalid_metric_direction():
    content = VALID_CONFIG.replace('metric_direction: "higher"', 'metric_direction: "sideways"')
    path = _write_config(content)
    with pytest.raises(ConfigError, match="metric_direction must be"):
        load_config(path)


def test_file_not_found():
    with pytest.raises(ConfigError, match="not found"):
        load_config("/nonexistent/path.yaml")


def test_invalid_yaml():
    path = _write_config("not: [valid: yaml: {{")
    with pytest.raises(Exception):
        load_config(path)


def test_tiers_sorted_by_number():
    content = """\
experiment_id: "test"
target_repo: "/tmp"
base_commit: "HEAD"
goal: "test"
target_metric: "x"
metric_direction: "higher"
tiers:
  - tier: 2
    steps:
      - name: "bench"
        command: "echo bench"
  - tier: 0
    steps:
      - name: "check"
        command: "echo check"
gates:
  - name: "g"
    tier: 0
"""
    path = _write_config(content)
    config = load_config(path)
    assert config.tiers[0].tier == 0
    assert config.tiers[1].tier == 2


def test_defaults_applied():
    path = _write_config(VALID_CONFIG)
    config = load_config(path)
    assert config.budget.max_iterations == 20
    assert config.budget.max_api_cost_usd == 50.0
    assert config.baseline.runs == 5
    assert config.reward.patch_size_penalty == 0.01
