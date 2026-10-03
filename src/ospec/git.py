"""The one git question ospec asks: which files under a path have local edits?"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def local_edits(repo: Path, pathspec: str) -> list[str]:
    """`git status --porcelain` lines for uncommitted or untracked files under `pathspec`.

    Anything that stops git from answering (not a repo, git missing, a hang) counts as no edits.
    """
    command = ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all", "--", pathspec]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return result.stdout.splitlines() if result.returncode == 0 else []
