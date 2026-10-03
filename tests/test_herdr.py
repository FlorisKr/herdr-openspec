import subprocess
import unittest
from pathlib import Path

from helpers import FakeRunner
from ospec.herdr import Herdr, Pane, Workspace


class HerdrTest(unittest.TestCase):
    def test_typed_workspaces_and_panes(self) -> None:
        runner = FakeRunner(
            {
                ("workspace", "list"): {"workspaces": [{"workspace_id": "w1", "focused": True}]},
                ("pane", "list"): {"panes": [{"workspace_id": "w1", "cwd": "/a", "foreground_cwd": "/b"}]},
            }
        )
        herdr = Herdr("herdr", run=runner)
        self.assertEqual(herdr.workspaces(), [Workspace("w1", focused=True)])
        self.assertEqual(herdr.panes(), [Pane("w1", "/b", focused=False)])

    def test_failures_mean_no_result(self) -> None:
        self.assertIsNone(Herdr("herdr", run=FakeRunner(returncode=1)).workspaces())

        def missing(*_args, **_kwargs):
            raise FileNotFoundError("herdr")

        self.assertIsNone(Herdr("herdr", run=missing).call("workspace", "list"))

        def garbage(argv, **_kwargs):
            return subprocess.CompletedProcess(argv, 0, "not json", "")

        self.assertIsNone(Herdr("herdr", run=garbage).call("workspace", "list"))

    def test_token_reports(self) -> None:
        runner = FakeRunner()
        herdr = Herdr("herdr", run=runner)
        herdr.report_tokens("w1", "ospec", {"a": "1 2", "b": ""})
        herdr.clear_tokens("w2", "ospec", ["a", "b"])
        self.assertEqual(
            runner.calls,
            [
                [
                    "herdr",
                    "workspace",
                    "report-metadata",
                    "w1",
                    "--source",
                    "ospec",
                    "--token",
                    "a=1 2",
                    "--token",
                    "b=",
                ],
                [
                    "herdr",
                    "workspace",
                    "report-metadata",
                    "w2",
                    "--source",
                    "ospec",
                    "--clear-token",
                    "a",
                    "--clear-token",
                    "b",
                ],
            ],
        )

    def test_popup_never_targets_a_workspace(self) -> None:
        # herdr rejects --workspace for popups: they always open over the active pane
        runner = FakeRunner()
        Herdr("herdr", run=runner).open_plugin_popup("openspec", "browser", cwd=Path("/p"), env={"OSPEC_PROJECT": "/p"})
        argv = runner.calls[0]
        self.assertNotIn("--workspace", argv)
        self.assertEqual(argv[argv.index("--env") + 1], "OSPEC_PROJECT=/p")
        self.assertEqual(argv[argv.index("--cwd") + 1], "/p")


if __name__ == "__main__":
    unittest.main()
