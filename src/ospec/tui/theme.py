"""Maps semantic `Style`s to curses attributes."""

from __future__ import annotations

import curses

from ospec.markdown import Style

ROLE_COLORS = (
    (Style.ACCENT, curses.COLOR_CYAN),
    (Style.SUCCESS, curses.COLOR_GREEN),
    (Style.WARNING, curses.COLOR_YELLOW),
    (Style.HEADING, curses.COLOR_MAGENTA),
    (Style.MUTED, None),  # bright black where available, see Theme.__init__
)
MODIFIERS = (
    (Style.BOLD, curses.A_BOLD),
    (Style.ITALIC, curses.A_ITALIC),
    (Style.UNDERLINE, curses.A_UNDERLINE),
    (Style.REVERSE, curses.A_REVERSE),
)


class Theme:
    """Create only after curses has started (inside curses.wrapper)."""

    def __init__(self) -> None:
        curses.use_default_colors()
        muted = 8 if curses.COLORS >= 16 else curses.COLOR_WHITE
        self._roles: dict[Style, int] = {}
        for pair, (role, color) in enumerate(ROLE_COLORS, start=1):
            curses.init_pair(pair, muted if color is None else color, -1)
            self._roles[role] = curses.color_pair(pair)

    def attr(self, style: Style) -> int:
        value = next((attr for role, attr in self._roles.items() if role in style), 0)
        for flag, attr in MODIFIERS:
            if flag in style:
                value |= attr
        return value
