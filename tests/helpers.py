"""Builders for throwaway OpenSpec projects and a scriptable herdr runner."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def make_project(root: Path, changes: dict[str, str]) -> Path:
    """A project under `root` with one change per entry: {name: tasks.md text}."""
    base = root / "openspec" / "changes"
    for name, tasks in changes.items():
        (base / name).mkdir(parents=True)
        (base / name / "tasks.md").write_text(tasks)
        (base / name / "proposal.md").write_text(f"# {name}\n")
    base.mkdir(parents=True, exist_ok=True)
    return root


class FakeRunner:
    """Stands in for subprocess.run: answers herdr commands from a table and records every call."""

    def __init__(self, results: dict[tuple[str, ...], Any] | None = None, returncode: int = 0) -> None:
        self.results = results or {}
        self.returncode = returncode
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        key = tuple(argv[1:3])
        payload = {"result": self.results.get(key, {"type": "ok"})}
        return subprocess.CompletedProcess(argv, self.returncode, json.dumps(payload), "")
