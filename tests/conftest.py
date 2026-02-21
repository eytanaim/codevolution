"""Test fixtures for codevolution tests."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

TOY_REPO_SRC = Path(__file__).parent / "fixtures" / "toy_repo"


@pytest.fixture
def toy_repo(tmp_path: Path) -> Path:
    """Create a temporary copy of the toy repo with git initialized.

    Returns the path to the temp repo (which is a proper git repo).
    """
    repo_dir = tmp_path / "toy_repo"
    shutil.copytree(TOY_REPO_SRC, repo_dir)

    subprocess.run(["git", "init"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit", "--no-verify"],
        cwd=str(repo_dir),
        capture_output=True,
        check=True,
        env={**__import__("os").environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com"},
    )
    return repo_dir
