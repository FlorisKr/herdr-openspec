"""Which OpenSpec project each herdr workspace is working in."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ospec.repository import find_project

if TYPE_CHECKING:
    from pathlib import Path

    from ospec.herdr import Herdr


def workspace_projects(herdr: Herdr) -> dict[str, Path]:
    """{workspace id: project} for every workspace with a pane inside an OpenSpec project.

    When a workspace's panes sit in different projects, the focused pane wins.
    """
    found: dict[str, Path] = {}
    for pane in herdr.panes():
        project = find_project(pane.cwd) if pane.cwd else None
        if project and (pane.workspace_id not in found or pane.focused):
            found[pane.workspace_id] = project
    return found


def focused_project(herdr: Herdr) -> Path | None:
    focused = next((w for w in herdr.workspaces() or [] if w.focused), None)
    return workspace_projects(herdr).get(focused.id) if focused else None
