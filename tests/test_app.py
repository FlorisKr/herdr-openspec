import tempfile
import unittest
from pathlib import Path

from helpers import make_project
from ospec.config import Settings
from ospec.tui.app import App
from ospec.tui.views import ChangesView, NoProjectView


class AppTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.settings = Settings.from_env({"XDG_CACHE_HOME": str(self.root / "cache")})

    def test_without_a_project_it_explains_and_closes_on_any_key(self) -> None:
        app = App(self.settings, None)
        self.assertIsInstance(app.view, NoProjectView)
        self.assertTrue(app.view.handle(app, ord("x")))

    def test_with_a_project_it_lists_the_changes(self) -> None:
        project = make_project(self.root / "app", {"a": "- [ ] x\n", "b": "- [x] x\n"})
        app = App(self.settings, project)
        self.assertIsInstance(app.view, ChangesView)
        self.assertEqual([c.name for c in app.changes], ["a", "b"])
        self.assertEqual(app.change_at(project / "openspec/changes/b"), app.changes[1])


if __name__ == "__main__":
    unittest.main()
