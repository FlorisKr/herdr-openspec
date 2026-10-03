import unittest

from ospec.markdown import Span, Style, column_widths, inline, plain, render, split_row, wrap


def texts(lines) -> list[str]:
    return [plain(line) for line in lines]


class InlineTest(unittest.TestCase):
    def test_styles(self) -> None:
        self.assertEqual(
            inline("a `code` **bold** *it* ~~old~~ [link](http://x)"),
            [
                Span("a "),
                Span("code", Style.ACCENT),
                Span(" "),
                Span("bold", Style.BOLD),
                Span(" "),
                Span("it", Style.ITALIC),
                Span(" "),
                Span("old", Style.MUTED),
                Span(" "),
                Span("link", Style.UNDERLINE),
            ],
        )

    def test_underscores_inside_words_stay(self) -> None:
        self.assertEqual(plain(inline("snake_case_word and _emph_")), "snake_case_word and emph")


class WrapTest(unittest.TestCase):
    def test_wraps_on_words_and_keeps_styles(self) -> None:
        lines = wrap([Span("one two "), Span("three four", Style.BOLD)], 9)
        self.assertEqual(texts(lines), ["one two", "three", "four"])
        self.assertEqual(lines[1], [Span("three", Style.BOLD)])

    def test_splits_words_longer_than_a_line(self) -> None:
        self.assertEqual(texts(wrap([Span("abcdefghij")], 4)), ["abcd", "efgh", "ij"])

    def test_empty_input_gives_one_empty_line(self) -> None:
        self.assertEqual(wrap([], 10), [[]])


class TableTest(unittest.TestCase):
    def test_split_row_respects_code_and_escapes(self) -> None:
        self.assertEqual(split_row("| a | `b|c` | d |"), ["a", "`b|c`", "d"])
        self.assertEqual(split_row(r"| x \| y | z |"), ["x | y", "z"])
        self.assertEqual(split_row("a | b"), ["a", "b"])

    def test_column_widths_shrink_wide_columns_first(self) -> None:
        self.assertEqual(column_widths([4, 10], 20), [4, 10])
        self.assertEqual(column_widths([4, 30, 30], 30), [4, 13, 13])

    def test_table_fits_the_width(self) -> None:
        md = "| Name | Notes |\n| --- | ---: |\n| a | " + "long words " * 10 + "|\n"
        lines = texts(render(md, 40))
        self.assertEqual(lines[0][0], "┌")
        self.assertEqual(lines[-1][0], "└")
        self.assertTrue(all(len(line) <= 40 for line in lines))
        self.assertIn("Name", lines[1])


class RenderTest(unittest.TestCase):
    def test_checkboxes_lists_and_quotes(self) -> None:
        self.assertEqual(
            texts(render("- [x] done\n- [ ] open\n- item\n1. first\n> quoted", 40)),
            ["✓ done", "☐ open", "• item", "1. first", "│ quoted"],
        )

    def test_mermaid_collapses_to_a_placeholder(self) -> None:
        lines = texts(render("```mermaid\nflowchart TD\n  A --> B\n```\nafter", 40))
        self.assertEqual(lines, ["│ mermaid diagram · flowchart", "│ press m to view it rendered", "after"])

    def test_code_blocks_are_kept_verbatim(self) -> None:
        self.assertEqual(texts(render("```sh\n  ls  -la\n```", 40)), ["```sh", "  ls  -la", "```"])

    def test_no_leading_or_double_blank_lines(self) -> None:
        self.assertEqual(texts(render("\n\npara\n\n\n## Next", 40)), ["para", "", "NEXT"])

    def test_wrapped_list_items_hang_under_the_text(self) -> None:
        lines = texts(render("- " + "word " * 12, 30))
        self.assertTrue(lines[1].startswith("  word"))


if __name__ == "__main__":
    unittest.main()
