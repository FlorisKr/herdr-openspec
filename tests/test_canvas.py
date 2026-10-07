import unittest
from typing import Any

from ospec.tui.canvas import Canvas


class FakeScreen:
    """Records text written per row; stands in for a curses window."""

    def __init__(self, width: int, height: int = 5) -> None:
        self.size = (height, width)
        self.rows = [[" "] * width for _ in range(height)]

    def getmaxyx(self) -> tuple[int, int]:
        return self.size

    def addstr(self, y: int, x: int, text: str, _attr: int) -> None:
        self.rows[y][x : x + len(text)] = text

    def row(self, y: int) -> str:
        return "".join(self.rows[y]).rstrip()


class PlainTheme:
    def attr(self, _style: Any) -> int:
        return 0


class CanvasTest(unittest.TestCase):
    KEYS = (("e", "edit"), ("m", "browser"), ("esc", "back"), ("q", "quit"))

    def frame_bottom(self, width: int, message: str) -> str:
        screen = FakeScreen(width)
        Canvas(screen, PlainTheme()).frame("title", self.KEYS, message)  # type: ignore[arg-type]
        return screen.row(screen.size[0] - 1)

    def test_legend_is_shown_whole_without_a_message(self) -> None:
        self.assertEqual(self.frame_bottom(60, ""), " e edit  m browser  esc back  q quit")

    def test_a_message_drops_legend_entries_instead_of_overlapping_them(self) -> None:
        self.assertEqual(self.frame_bottom(41, "read-only"), " e edit  m browser  esc back  read-only")


if __name__ == "__main__":
    unittest.main()
