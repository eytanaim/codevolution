"""Git worktree management for isolated candidate evaluation."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def create_worktree(repo: str | Path, commit: str, name: str) -> Path:
    """Create a git worktree at a temp location, checked out at the given commit.

    Returns the worktree path.
    """
    repo = Path(repo).resolve()
    worktree_dir = Path(tempfile.mkdtemp(prefix=f"codevolution-{name}-"))

    subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree_dir), commit],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return worktree_dir


def cleanup_worktree(repo: str | Path, worktree_path: str | Path) -> None:
    """Remove a git worktree and prune."""
    repo = Path(repo).resolve()
    worktree_path = Path(worktree_path)

    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
