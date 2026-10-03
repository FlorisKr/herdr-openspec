"""Reading OpenSpec projects and changes from disk."""

from __future__ import annotations

from pathlib import Path

from ospec.model import Change, parse_created, parse_tasks

CHANGES_PATH = "openspec/changes"


def is_project(directory: Path) -> bool:
    return (directory / CHANGES_PATH).is_dir()


def find_project(start: str | Path) -> Path | None:
    """The nearest directory at or above `start` that contains openspec/changes."""
    path = Path(start).expanduser().resolve()
    return next((d for d in (path, *path.parents) if is_project(d)), None)


def load_change(path: Path) -> Change:
    meta = path / ".openspec.yaml"
    tasks = path / "tasks.md"
    created = parse_created(meta.read_text()) if meta.is_file() else ""
    groups, next_task = parse_tasks(tasks.read_text()) if tasks.is_file() else ((), None)
    mtime = max((f.stat().st_mtime for f in path.rglob("*") if f.is_file()), default=0.0)
    return Change(path.name, path, created, groups, next_task, mtime)


def load_changes(project: Path) -> list[Change]:
    """Open changes (archive/ excluded): unfinished first, then most recently touched first."""
    base = project / CHANGES_PATH
    changes = [load_change(d) for d in base.iterdir() if d.is_dir() and d.name != "archive"]
    return sorted(changes, key=lambda c: (c.complete, -c.mtime))
