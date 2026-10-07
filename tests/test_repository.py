import os
import tempfile
import time
import unittest
from pathlib import Path

from helpers import make_project
from ospec.repository import find_project, load_archived, load_changes


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

    def test_archived_changes_come_most_recently_archived_first(self) -> None:
        project = make_project(self.root / "app", {"open": ""})
        archive = project / "openspec/changes/archive"
        for folder in ("2026-01-05-older", "2026-03-01-newer"):
            (archive / folder).mkdir(parents=True)
            (archive / folder / "tasks.md").write_text("- [x] a\n")
        archived = load_archived(project)
        self.assertEqual([(c.name, c.archived) for c in archived], [("newer", "2026-03-01"), ("older", "2026-01-05")])
        self.assertEqual(archived[0].done, 1)

    def test_no_archive_folder_means_nothing_archived(self) -> None:
        self.assertEqual(load_archived(make_project(self.root / "app", {"open": ""})), [])


if __name__ == "__main__":
    unittest.main()
