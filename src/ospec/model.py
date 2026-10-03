"""Domain model: an OpenSpec change, its documents and its task progress."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from ospec.markdown import CHECKBOX

if TYPE_CHECKING:
    from pathlib import Path

CREATED = re.compile(r"^created:\s*(\S+)", re.MULTILINE)


class DocKind(Enum):
    TASKS = "Tasks"
    PROPOSAL = "Proposal"
    DESIGN = "Design"
    SPECS = "Specs"

    @property
    def label(self) -> str:
        return self.value

    @property
    def slug(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class TaskGroup:
    title: str
    done: int
    total: int

    @property
    def complete(self) -> bool:
        return self.total > 0 and self.done == self.total


@dataclass(frozen=True)
class Change:
    name: str
    path: Path
    created: str
    groups: tuple[TaskGroup, ...]
    next_task: str | None
    mtime: float

    @property
    def done(self) -> int:
        return sum(g.done for g in self.groups)

    @property
    def total(self) -> int:
        return sum(g.total for g in self.groups)

    @property
    def complete(self) -> bool:
        return self.total > 0 and self.done == self.total

    def doc_files(self, kind: DocKind) -> list[Path]:
        if kind is DocKind.SPECS:
            return sorted((self.path / "specs").glob("*/spec.md"))
        file = self.path / f"{kind.slug}.md"
        return [file] if file.is_file() else []

    def has(self, kind: DocKind) -> bool:
        return bool(self.doc_files(kind))

    def read(self, kind: DocKind) -> str:
        files = self.doc_files(kind)
        if not files:
            return f"_No {kind.label.lower()} in this change._"
        if kind is DocKind.SPECS:
            return "\n\n".join(f"# ▍{f.parent.name}\n\n{f.read_text()}" for f in files)
        return files[0].read_text()


def parse_tasks(text: str) -> tuple[tuple[TaskGroup, ...], str | None]:
    """Task groups (one per `## ` heading) and the first unchecked task of a tasks.md."""
    titles: list[str] = []
    counts: list[list[int]] = []  # [done, total] per group
    next_task: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            titles.append(line[3:].strip())
            counts.append([0, 0])
            continue
        match = CHECKBOX.match(line)
        if not match:
            continue
        if not titles:
            titles.append("Tasks")
            counts.append([0, 0])
        done = match.group(2) != " "
        counts[-1][0] += done
        counts[-1][1] += 1
        if not done and next_task is None:
            next_task = match.group(3).strip()
    groups = tuple(TaskGroup(title, done, total) for title, (done, total) in zip(titles, counts))
    return groups, next_task


def parse_created(meta: str) -> str:
    """The `created:` date from a change's .openspec.yaml, or ""."""
    match = CREATED.search(meta)
    return match.group(1) if match else ""
