import tempfile
import unittest
from pathlib import Path

from ospec.model import DocKind, TaskGroup, parse_created, parse_tasks
from ospec.repository import load_change

TASKS = """\
## 1. Backend

- [x] 1.1 Add the column
- [X] 1.2 Migrate data

## 2. Frontend

- [x] 2.1 Show the field
- [ ] 2.2 Validate input
- [ ] 2.3 Write docs

## 3. Docs
"""


class ParseTasksTest(unittest.TestCase):
    def test_counts_tasks_per_group_and_finds_the_next_one(self) -> None:
        groups, next_task = parse_tasks(TASKS)
        self.assertEqual(
            groups,
            (
                TaskGroup("1. Backend", 2, 2),
                TaskGroup("2. Frontend", 1, 3),
                TaskGroup("3. Docs", 0, 0),
            ),
        )
        self.assertEqual(next_task, "2.2 Validate input")

    def test_tasks_before_any_heading_get_a_default_group(self) -> None:
        groups, _ = parse_tasks("- [ ] only task\n")
        self.assertEqual(groups, (TaskGroup("Tasks", 0, 1),))

    def test_continuation_lines_are_not_tasks(self) -> None:
        groups, _ = parse_tasks("## G\n- [x] a long task\n      that wraps\n")
        self.assertEqual(groups, (TaskGroup("G", 1, 1),))

    def test_empty_file(self) -> None:
        self.assertEqual(parse_tasks(""), ((), None))


class MetadataTest(unittest.TestCase):
    def test_created_date(self) -> None:
        self.assertEqual(parse_created("schema: spec-driven\ncreated: 2026-09-30\n"), "2026-09-30")
        self.assertEqual(parse_created("schema: spec-driven\n"), "")


class ChangeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "add-thing"
        (self.path / "specs" / "b-cap").mkdir(parents=True)
        (self.path / "specs" / "a-cap").mkdir(parents=True)
        (self.path / "tasks.md").write_text(TASKS)
        (self.path / "specs" / "a-cap" / "spec.md").write_text("A spec")
        (self.path / "specs" / "b-cap" / "spec.md").write_text("B spec")

    def test_progress(self) -> None:
        change = load_change(self.path)
        self.assertEqual((change.done, change.total, change.complete), (3, 5, False))

    def test_documents(self) -> None:
        change = load_change(self.path)
        self.assertTrue(change.has(DocKind.TASKS))
        self.assertFalse(change.has(DocKind.DESIGN))
        self.assertIn("No design", change.read(DocKind.DESIGN))
        specs = change.read(DocKind.SPECS)
        self.assertLess(specs.index("a-cap"), specs.index("b-cap"))
        self.assertIn("B spec", specs)


if __name__ == "__main__":
    unittest.main()
