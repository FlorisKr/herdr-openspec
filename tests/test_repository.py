import os
import tempfile
import time
import unittest
from pathlib import Path

from helpers import make_project
from ospec.repository import find_project, load_changes


class RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_find_project_walks_up(self) -> None:
        project = make_project(self.root / "app", {"c": ""})
        nested = project / "src" / "deep"
        nested.mkdir(parents=True)
        self.assertEqual(find_project(nested), project)
        self.assertIsNone(find_project(self.root))

    def test_open_changes_come_unfinished_first_then_most_recent(self) -> None:
        project = make_project(
            self.root / "app",
            {
                "finished": "- [x] a\n",
                "older": "- [ ] a\n",
                "newer": "- [ ] a\n",
            },
        )
        past = time.time() - 3600
        for f in (project / "openspec/changes/older").iterdir():
            os.utime(f, (past, past))
        names = [c.name for c in load_changes(project)]
        self.assertEqual(names, ["newer", "older", "finished"])

    def test_archived_changes_are_left_out(self) -> None:
        project = make_project(self.root / "app", {"open": ""})
        (project / "openspec/changes/archive/2026-01-01-old").mkdir(parents=True)
        self.assertEqual([c.name for c in load_changes(project)], ["open"])


if __name__ == "__main__":
    unittest.main()
