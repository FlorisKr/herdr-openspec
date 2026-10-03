"""What the sidebar says about a project: an overview, or the change being edited locally."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ospec import git
from ospec.repository import CHANGES_PATH, load_changes

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ospec.model import Change

SIDEBAR_WIDTH = 28  # characters a sidebar row can show with the sidebar_width from herdr-config.toml


@dataclass(frozen=True)
class SidebarRows:
    primary: str
    secondary: str = ""


def active_change(changes: Iterable[Change], edits: Iterable[str]) -> Change | None:
    """The most recently touched open change with a local edit in `edits` (git porcelain lines)."""
    edits = list(edits)
    edited = [c for c in changes if any(f"{CHANGES_PATH}/{c.name}/" in line for line in edits)]
    return max(edited, key=lambda c: c.mtime, default=None)


def fit(text: str, width: int) -> str:
    """Shorten from the middle: change names share prefixes, the tail tells them apart."""
    if len(text) <= width:
        return text
    head = (width - 1) // 2
    return f"{text[:head]}…{text[len(text) - (width - 1 - head) :]}"


def mini_bar(done: int, total: int, width: int = 6) -> str:
    filled = round(width * done / total) if total else 0
    return "▰" * filled + "▱" * (width - filled)


def sidebar_rows(changes: list[Change], active: Change | None, width: int = SIDEBAR_WIDTH) -> SidebarRows:
    if active is not None:
        name = fit(active.name, width)
        if not active.total:
            return SidebarRows("✎ no tasks yet", name)
        return SidebarRows(f"✎ {active.done}/{active.total} {mini_bar(active.done, active.total)}", name)
    if not changes:
        return SidebarRows("◇ no open changes")
    ready = sum(c.complete for c in changes)
    return SidebarRows(f"◇ {len(changes)} open" + (f" · {ready} to archive" if ready else ""))


def project_rows(project: Path) -> SidebarRows:
    changes = load_changes(project)
    return sidebar_rows(changes, active_change(changes, git.local_edits(project, CHANGES_PATH)))
