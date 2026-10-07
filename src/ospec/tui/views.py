"""The screens: the change list, a change's documents, and a note when there is no project.

Each view draws itself and handles its own keys; shared state and actions live on `App`.
"""

from __future__ import annotations

import curses
from typing import TYPE_CHECKING, Protocol

from ospec import markdown
from ospec.markdown import Span, Style
from ospec.model import DocKind

if TYPE_CHECKING:
    from pathlib import Path

    from ospec.markdown import Line
    from ospec.model import Change, TaskGroup
    from ospec.tui.app import App
    from ospec.tui.canvas import Canvas

TABS = (DocKind.TASKS, DocKind.PROPOSAL, DocKind.DESIGN, DocKind.SPECS)
TAB_KEYS = {ord(str(n + 1)): n for n in range(len(TABS))}
ENTER = frozenset({10, 13, curses.KEY_ENTER})
ESCAPE = 27
DOWN = frozenset({curses.KEY_DOWN, ord("j")})
UP = frozenset({curses.KEY_UP, ord("k")})
QUIT = frozenset({ord("q"), ESCAPE})
DOC_WIDTH = 110  # readable line length for documents, even in a wide popup


class View(Protocol):
    def draw(self, app: App, canvas: Canvas) -> None: ...

    def handle(self, app: App, key: int) -> bool:
        """React to `key`; True means quit."""
        ...


def plural(count: int, word: str) -> str:
    return f"{count} {word}{'s' * (count != 1)}"


def progress_bar(done: int, total: int, width: int = 12) -> Line:
    if not total:
        return [Span("·" * width, Style.MUTED)]
    filled = round(width * done / total)
    color = Style.SUCCESS if done == total else Style.WARNING
    return [Span("█" * filled, color), Span("░" * (width - filled), Style.MUTED)]


def group_icon(group: TaskGroup) -> Span:
    if group.complete:
        return Span("✓ ", Style.SUCCESS)
    return Span("◐ ", Style.WARNING) if group.done else Span("○ ", Style.MUTED)


class NoProjectView:
    """Shown when ospec starts outside an OpenSpec project; any key closes it."""

    def draw(self, app: App, canvas: Canvas) -> None:
        canvas.frame("OpenSpec", (("any key", "close"),))
        canvas.put(2, 2, [Span("No OpenSpec project here.", Style.BOLD)])
        canvas.put(3, 2, [Span("Open ospec from a folder inside a project (one with openspec/changes).", Style.MUTED)])

    def handle(self, app: App, key: int) -> bool:
        return True


class ChangesView:
    """Open changes, or (toggled with `a`) the archived ones."""

    def __init__(self) -> None:
        self.selected = 0
        self.archived = False

    def listed(self, app: App) -> list[Change]:
        return app.archived if self.archived else app.changes

    def draw(self, app: App, canvas: Canvas) -> None:
        changes = self.listed(app)
        self.selected = min(self.selected, max(len(changes) - 1, 0))
        canvas.frame(f"OpenSpec · {app.project_name}  —  {self._summary(app)}", self._keys(), app.message)
        if not changes and self.archived:
            canvas.put(2, 2, [Span("No archived changes.")])
            return
        if not changes:
            canvas.put(2, 2, [Span("No open changes. "), Span("Start one with /opsx:propose", Style.MUTED)])
            return
        y = self._draw_list(app, canvas, changes)
        self._draw_detail(app, canvas, changes[self.selected], y + 1)

    def _summary(self, app: App) -> str:
        if self.archived:
            return f"{len(app.archived)} archived"
        summary = plural(len(app.changes), "open change")
        return f"{summary}  ·  {len(app.archived)} archived" if app.archived else summary

    def _keys(self) -> tuple[tuple[str, str], ...]:
        return (
            ("↑↓", "move"),
            ("⏎/1-4", "open"),
            ("m", "browser"),
            ("a", "open changes" if self.archived else "archived"),
            ("r", "reload"),
            ("q", "quit"),
        )

    def _draw_list(self, app: App, canvas: Canvas, changes: list[Change]) -> int:
        name_width = min(max(len(c.name) for c in changes) + 2, max(canvas.width - 46, 20))
        count_width = max(3, *(len(str(c.total)) for c in changes))  # one width for all rows, so the dates line up
        visible = canvas.height - 13  # leave room for the detail panel
        top = max(0, self.selected - visible + 1)
        y = 2
        for index, change in enumerate(changes[top : top + visible], start=top):
            canvas.put(y, 1, self._row(change, index == self.selected, change == app.active, name_width, count_width))
            y += 1
            if y >= canvas.height - 11:
                break
        return y

    @staticmethod
    def _row(change: Change, selected: bool, active: bool, name_width: int, count_width: int) -> Line:
        name = change.name if len(change.name) <= name_width - 2 else change.name[: name_width - 3] + "…"
        return [
            Span("▸" if selected else " ", Style.ACCENT | Style.BOLD),
            Span("✎" if active else " ", Style.SUCCESS | Style.BOLD),
            Span(f"{name:<{name_width}}", Style.BOLD | Style.REVERSE if selected else Style.NONE),
            *progress_bar(change.done, change.total),
            Span(
                f" {change.done:>{count_width}}/{change.total:<{count_width}} ",
                Style.SUCCESS if change.complete else Style.NONE,
            ),
            Span(f"{change.archived or change.created:<11}", Style.MUTED),
            *(Span(f"{kind.label[0]} ", Style.ACCENT if change.has(kind) else Style.MUTED) for kind in TABS),
        ]

    @staticmethod
    def _state(change: Change, active: bool) -> str:
        if change.archived:
            return f"archived {change.archived}"
        if change.complete:
            state = "complete — ready to archive"
        else:
            state = f"{plural(change.total - change.done, 'task')} left"
        return f"{state}  ·  ✎ local edits" if active else state

    def _draw_detail(self, app: App, canvas: Canvas, change: Change, y: int) -> None:
        canvas.put(y, 1, [Span("─" * (canvas.width - 3), Style.MUTED)])
        canvas.put(
            y + 1,
            2,
            [
                Span(change.name, Style.HEADING | Style.BOLD),
                Span(f"   {self._state(change, change == app.active)}", Style.MUTED),
            ],
        )
        y += 2
        title_width = max(min(canvas.width - 22, 52), 10)
        for group in change.groups:
            if y >= canvas.height - 3:
                canvas.put(y, 4, [Span("…", Style.MUTED)])
                y += 1
                break
            canvas.put(
                y,
                4,
                [
                    group_icon(group),
                    Span(f"{group.title[:title_width]:<{title_width}}", Style.MUTED if group.complete else Style.NONE),
                    Span(f" {group.done}/{group.total}", Style.MUTED),
                ],
            )
            y += 1
        if change.next_task and not change.archived and y < canvas.height - 2:
            canvas.put(y + 1, 2, [Span("next ▸ ", Style.WARNING | Style.BOLD), Span(change.next_task)])

    def handle(self, app: App, key: int) -> bool:
        changes = self.listed(app)
        selected = changes[self.selected] if changes else None
        if key in DOWN:
            self.selected = min(self.selected + 1, max(len(changes) - 1, 0))
        elif key in UP:
            self.selected = max(self.selected - 1, 0)
        elif key == ord("a"):
            self.archived, self.selected = not self.archived, 0
        elif key == ord("r"):
            app.reload()
            app.message = "reloaded"
        elif key in QUIT:
            return True
        elif selected is not None:
            self._handle_selected(app, key, selected)
        return False

    @staticmethod
    def _handle_selected(app: App, key: int, change: Change) -> None:
        if key in ENTER or key in (curses.KEY_RIGHT, ord("l")):
            app.show(DocView(change.path))
        elif key in TAB_KEYS:
            app.show(DocView(change.path, TAB_KEYS[key]))
        elif key == ord("m"):
            app.open_in_browser(change, DocKind.PROPOSAL)


class DocView:
    KEYS = (
        ("1-4/⇥", "tab"),
        ("↑↓ space b", "scroll"),
        ("g/G", "top/end"),
        ("e", "edit"),
        ("m", "browser"),
        ("esc", "back"),
        ("q", "quit"),
    )

    def __init__(self, change_path: Path, tab: int = 0) -> None:
        self.change_path = change_path
        self.tab = tab
        self.scroll = 0
        self.page = 1  # set by draw: lines per page and document length, for paging keys
        self.length = 0

    @property
    def kind(self) -> DocKind:
        return TABS[self.tab]

    def draw(self, app: App, canvas: Canvas) -> None:
        change = app.change_at(self.change_path)
        if change is None:  # archived or deleted since we opened it (seen after a reload)
            app.show_changes()
            return
        where = f"{app.project_name} › archive" if change.archived else app.project_name
        canvas.frame(f"{where} › {change.name}", self.KEYS, app.message)
        self._draw_tabs(canvas, change)
        lines = markdown.render(change.read(self.kind), min(canvas.width - 4, DOC_WIDTH))
        body = canvas.height - 4
        self.scroll = max(0, min(self.scroll, len(lines) - body))
        for row, line in enumerate(lines[self.scroll : self.scroll + body]):
            canvas.put(3 + row, 2, line)
        if len(lines) > body:
            percent = min(100, 100 * (self.scroll + body) // len(lines))
            canvas.put(1, canvas.width - 7, [Span(f"{percent:>3}% ", Style.MUTED)])
        self.page, self.length = max(body - 2, 1), len(lines)

    def _draw_tabs(self, canvas: Canvas, change: Change) -> None:
        x = 1
        for index, kind in enumerate(TABS):
            count = f" {change.done}/{change.total}" if kind is DocKind.TASKS and change.total else ""
            if index == self.tab:
                style = Style.ACCENT | Style.REVERSE | Style.BOLD
            else:
                style = Style.NONE if change.has(kind) else Style.MUTED
            x = canvas.put(1, x, [Span(f" {index + 1} {kind.label}{count} ", style), Span(" ")])

    def handle(self, app: App, key: int) -> bool:
        if self._scroll(key):
            return False
        change = app.change_at(self.change_path)
        if key in TAB_KEYS:
            self._switch_tab(TAB_KEYS[key])
        elif key in (ord("\t"), curses.KEY_RIGHT, ord("l")):
            self._switch_tab(self.tab + 1)
        elif key in (curses.KEY_BTAB, curses.KEY_LEFT, ord("h")):
            self._switch_tab(self.tab - 1)
        elif key == ord("m") and change is not None:
            app.open_in_browser(change, self.kind)
        elif key == ord("e") and change is not None:
            app.edit(change, self.kind)
        elif key in (ESCAPE, curses.KEY_BACKSPACE, 127):
            app.show_changes()
        elif key == ord("q"):
            return True
        return False

    def _scroll(self, key: int) -> bool:
        """Apply a scrolling key; False if `key` isn't one."""
        moves = {
            ord(" "): self.page,
            ord("d"): self.page,
            curses.KEY_NPAGE: self.page,
            ord("b"): -self.page,
            ord("u"): -self.page,
            curses.KEY_PPAGE: -self.page,
            ord("g"): -self.length,
            ord("G"): self.length,
            **dict.fromkeys(DOWN, 1),
            **dict.fromkeys(UP, -1),
        }
        if key not in moves:
            return False
        self.scroll = max(self.scroll + moves[key], 0)  # draw clamps the bottom end
        return True

    def _switch_tab(self, tab: int) -> None:
        self.tab, self.scroll = tab % len(TABS), 0
