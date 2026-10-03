"""Desktop integration: opening URLs and the user's editor."""

from __future__ import annotations

import shlex
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def open_url(url: str) -> bool:
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        result = subprocess.run([opener, url], capture_output=True, check=False)
    except OSError:
        return False
    return result.returncode == 0


def edit_file(path: Path, editor: str) -> None:
    """Run the editor in the foreground; `editor` may carry arguments, e.g. "code -w"."""
    subprocess.run([*shlex.split(editor), str(path)], check=False)
