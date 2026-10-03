import tempfile
import unittest
from pathlib import Path

from helpers import make_project
from ospec.repository import load_changes
from ospec.status import SidebarRows, active_change, fit, sidebar_rows


class FitTest(unittest.TestCase):
    def test_short_text_is_untouched(self) -> None:
        self.assertEqual(fit("short", 10), "short")

    def test_long_text_keeps_both_ends(self) -> None:
        shortened = fit("checkout-payment-retry-flow", 20)
        self.assertEqual(shortened, "checkout-…retry-flow")


class SidebarTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = make_project(
            Path(tmp.name),
            {
                "add-dark-mode": "- [x] a\n- [x] b\n- [ ] c\n",
                "done-change": "- [x] a\n",
                "empty-change": "",
            },
        )
        self.changes = load_changes(project)

    def named(self, name: str):
        return next(c for c in self.changes if c.name == name)

    def test_active_change_needs_a_local_edit_inside_it(self) -> None:
        edits = [" M openspec/changes/add-dark-mode/tasks.md", "?? openspec/changes/other/x.md"]
        self.assertEqual(active_change(self.changes, edits), self.named("add-dark-mode"))
        self.assertIsNone(active_change(self.changes, []))
        self.assertIsNone(active_change(self.changes, [" M openspec/changes/add-dark-mode-v2/x.md"]))

    def test_overview_when_nothing_is_edited(self) -> None:
        self.assertEqual(sidebar_rows(self.changes, None), SidebarRows("◇ 3 open · 1 to archive"))
        self.assertEqual(sidebar_rows([], None), SidebarRows("◇ no open changes"))

    def test_progress_of_the_edited_change(self) -> None:
        rows = sidebar_rows(self.changes, self.named("add-dark-mode"))
        self.assertEqual(rows, SidebarRows("✎ 2/3 ▰▰▰▰▱▱", "add-dark-mode"))

    def test_edited_change_without_tasks(self) -> None:
        rows = sidebar_rows(self.changes, self.named("empty-change"))
        self.assertEqual(rows, SidebarRows("✎ no tasks yet", "empty-change"))


if __name__ == "__main__":
    unittest.main()
