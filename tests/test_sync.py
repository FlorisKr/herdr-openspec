import fcntl
import tempfile
import unittest
from pathlib import Path

from helpers import FakeRunner, make_project
from ospec.herdr import Herdr
from ospec.sync import sync, sync_once


class SyncTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.project = make_project(self.root / "app", {"a": "- [ ] x\n", "b": "- [x] x\n"})
        self.runner = FakeRunner(
            {
                ("workspace", "list"): {"workspaces": [{"workspace_id": "w1"}, {"workspace_id": "w2"}]},
                ("pane", "list"): {
                    "panes": [
                        {"workspace_id": "w1", "cwd": str(self.project / "src")},
                        {"workspace_id": "w2", "cwd": str(self.root)},
                    ]
                },
            }
        )
        self.herdr = Herdr("herdr", run=self.runner)

    def reports(self) -> list[list[str]]:
        return [c[1:] for c in self.runner.calls if c[2] == "report-metadata"]

    def test_reports_projects_and_clears_other_workspaces(self) -> None:
        self.assertEqual(sync_once(self.herdr), 0)
        self.assertEqual(
            self.reports(),
            [
                [
                    "workspace",
                    "report-metadata",
                    "w1",
                    "--source",
                    "ospec",
                    "--token",
                    "openspec=◇ 2 open · 1 to archive",
                    "--token",
                    "openspec_change=",
                ],
                [
                    "workspace",
                    "report-metadata",
                    "w2",
                    "--source",
                    "ospec",
                    "--clear-token",
                    "openspec",
                    "--clear-token",
                    "openspec_change",
                ],
            ],
        )

    def test_unreachable_herdr_is_an_error(self) -> None:
        self.assertEqual(sync_once(Herdr("herdr", run=FakeRunner(returncode=1))), 1)

    def test_a_running_sync_absorbs_new_requests(self) -> None:
        cache = self.root / "cache"
        cache.mkdir()
        with (cache / "sync.lock").open("w") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            self.assertEqual(sync(self.herdr, cache), 0)
        self.assertTrue((cache / "sync.pending").exists())
        self.assertEqual(self.runner.calls, [])  # the lock holder does the work, not us

    def test_sync_runs_and_clears_the_pending_flag(self) -> None:
        cache = self.root / "cache"
        self.assertEqual(sync(self.herdr, cache), 0)
        self.assertFalse((cache / "sync.pending").exists())
        self.assertEqual(len(self.reports()), 2)


if __name__ == "__main__":
    unittest.main()
