"""Browser state and the actions views can trigger, plus the curses main loop."""

from __future__ import annotations

import curses
from typing import TYPE_CHECKING

from ospec import git, system
from ospec.page import write_page
from ospec.repository import CHANGES_PATH, load_changes
from ospec.status import active_change
from ospec.tui.canvas import Canvas
from ospec.tui.theme import Theme
from ospec.tui.views import ChangesView, NoProjectView

if TYPE_CHECKING:
    from pathlib import Path

    from ospec.config import Settings
    from ospec.model import Change, DocKind
    from ospec.tui.views import View


class App:
    def __init__(self, settings: Settings, project: Path | None) -> None:
        self.settings = settings
        self.project = project
        self.changes: list[Change] = []
        self.active: Change | None = None
        self.message = ""
        self.changes_view = ChangesView()  # kept, so returning to the list keeps the selection
        self.view: View = self.changes_view if project else NoProjectView()
        self.canvas: Canvas | None = None
        self.reload()

    @property
    def project_name(self) -> str:
        return self.project.name if self.project else ""

    # -- state

    def reload(self) -> None:
        if self.project is None:
            return
        self.changes = load_changes(self.project)
        self.active = active_change(self.changes, git.local_edits(self.project, CHANGES_PATH))

    def change_at(self, path: Path) -> Change | None:
        return next((c for c in self.changes if c.path == path), None)

    # -- navigation

    def show(self, view: View) -> None:
        self.view = view

    def show_changes(self) -> None:
        self.show(self.changes_view)

    # -- actions

    def open_in_browser(self, change: Change, kind: DocKind) -> None:
        if self.project is None:
            return
        page = write_page(self.project, change, self.settings.cache_dir)
        opened = system.open_url(f"file://{page}#{kind.slug}")
        self.message = "opened in browser" if opened else f"couldn't open {page}"

    def edit(self, change: Change, kind: DocKind) -> None:
        files = change.doc_files(kind)
        if not files or self.canvas is None:
            self.message = "nothing to edit"
            return
        self.canvas.suspend(lambda: system.edit_file(files[0], self.settings.editor))
        self.reload()

    # -- main loop

    def run(self, screen: curses.window) -> None:
        curses.curs_set(0)
        curses.set_escdelay(25)
        screen.keypad(True)
        self.canvas = canvas = Canvas(screen, Theme())
        while True:
            view = self.view
            screen.erase()
            view.draw(self, canvas)
            if self.view is not view:  # the view handed over while drawing; draw the new one
                continue
            screen.refresh()
            key = screen.getch()
            if key == curses.KEY_RESIZE:
                continue
            self.message = ""
            if view.handle(self, key):
                return


def run_tui(settings: Settings, project: Path | None) -> None:
    curses.wrapper(App(settings, project).run)
