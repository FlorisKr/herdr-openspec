"""Drawing styled lines on a curses window, clipped to the screen."""

from __future__ import annotations

import contextlib
import curses
from typing import TYPE_CHECKING

from ospec.markdown import Span, Style

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from ospec.markdown import Line
    from ospec.tui.theme import Theme


class Canvas:
    def __init__(self, screen: curses.window, theme: Theme) -> None:
        self.screen = screen
        self.theme = theme

    @property
    def height(self) -> int:
        return self.screen.getmaxyx()[0]

    @property
    def width(self) -> int:
        return self.screen.getmaxyx()[1]

    def put(self, y: int, x: int, line: Line) -> int:
        """Draw `line` at (y, x), clipped to the screen; returns the column after the last character."""
        if not 0 <= y < self.height:
            return x
        limit = self.width - 1
        for span in line:
            if x >= limit:
                break
            text = span.text[: limit - x]
            with contextlib.suppress(curses.error):  # writing the bottom-right cell raises
                self.screen.addstr(y, x, text, self.theme.attr(span.style))
            x += len(text)
        return x

    def frame(self, title: str, keys: Sequence[tuple[str, str]], message: str = "") -> None:
        """A title bar on top and a key legend (plus an optional message) at the bottom."""
        bar = Style.ACCENT | Style.REVERSE
        self.put(0, 0, [Span(" " * self.width, bar)])
        self.put(0, 1, [Span(title, bar | Style.BOLD)])
        bottom = self.height - 1
        self.put(bottom, 1, [Span("  ".join(f"{key} {what}" for key, what in keys), Style.MUTED)])
        if message:
            self.put(bottom, max(self.width - len(message) - 2, 1), [Span(message, Style.SUCCESS)])

    def suspend(self, action: Callable[[], None]) -> None:
        """Hand the terminal to `action` (e.g. an editor), then take it back."""
        curses.endwin()
        try:
            action()
        finally:
            self.screen.refresh()
