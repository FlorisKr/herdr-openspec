import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from helpers import FakeRunner, make_project
from ospec.cli import main, popup, resolve_project
from ospec.config import Settings
from ospec.herdr import Herdr


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.project = make_project(self.root / "app", {"a": ""})
        self.other = make_project(self.root / "other", {"b": ""})

    def settings(self, **env: str) -> Settings:
        return Settings.from_env({"XDG_CACHE_HOME": str(self.root / "cache"), **env})

    def test_project_lookup_order(self) -> None:
        herdr = Herdr("herdr", run=FakeRunner())
        hinted = self.settings(OSPEC_PROJECT=str(self.other))
        self.assertEqual(resolve_project(hinted, herdr, str(self.project / "deep")), self.project)
        self.assertEqual(resolve_project(hinted, herdr, None), self.other)
        cwd = Path.cwd()
        try:
            os.chdir(self.root)
            self.assertIsNone(resolve_project(self.settings(), herdr, None))
        finally:
            os.chdir(cwd)

    def test_popup_opens_for_the_invoking_pane(self) -> None:
        runner = FakeRunner()
        context = f'{{"focused_pane_cwd": "{self.project}/src", "workspace_id": "w9"}}'
        settings = self.settings(HERDR_PLUGIN_CONTEXT_JSON=context, HERDR_PLUGIN_ID="openspec")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(popup(settings, Herdr("herdr", run=runner)), 0)
        argv = runner.calls[0]
        self.assertEqual(argv[1:4], ["plugin", "pane", "open"])
        self.assertIn(f"OSPEC_PROJECT={self.project}", argv)
        self.assertNotIn("--workspace", argv)

    def test_unknown_argument_is_an_error(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(main(["status"]), 2)
        self.assertIn("no such command or path: status", err.getvalue())

    def test_settings_survive_bad_environment_values(self) -> None:
        self.assertEqual(self.settings(HERDR_PLUGIN_CONTEXT_JSON="[1, 2]").plugin_context, {})
        self.assertEqual(self.settings(HERDR_PLUGIN_CONTEXT_JSON="{broken").plugin_context, {})


if __name__ == "__main__":
    unittest.main()
