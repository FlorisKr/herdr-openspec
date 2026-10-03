"""Push every workspace's OpenSpec status into the herdr sidebar."""

from __future__ import annotations

import fcntl
from typing import TYPE_CHECKING

from ospec.status import project_rows
from ospec.workspaces import workspace_projects

if TYPE_CHECKING:
    from pathlib import Path

    from ospec.herdr import Herdr

SOURCE = "ospec"
PROGRESS_TOKEN = "openspec"
CHANGE_TOKEN = "openspec_change"


def sync(herdr: Herdr, cache_dir: Path) -> int:
    """Coalescing sync: if one is already running, ask it to go again and return immediately.

    herdr fires several events at once (an agent finishing also changes focus), so this keeps
    bursts down to at most one extra pass.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    pending = cache_dir / "sync.pending"
    with (cache_dir / "sync.lock").open("w") as lock:  # the lock is held while the file is open
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pending.touch()
            return 0
        while True:
            pending.unlink(missing_ok=True)
            code = sync_once(herdr)
            if not pending.exists():
                return code


def sync_once(herdr: Herdr) -> int:
    workspaces = herdr.workspaces()
    if workspaces is None:
        return 1
    projects = workspace_projects(herdr)
    for workspace in workspaces:
        project = projects.get(workspace.id)
        if project is None:
            herdr.clear_tokens(workspace.id, SOURCE, (PROGRESS_TOKEN, CHANGE_TOKEN))
            continue
        rows = project_rows(project)
        herdr.report_tokens(workspace.id, SOURCE, {PROGRESS_TOKEN: rows.primary, CHANGE_TOKEN: rows.secondary})
    return 0
