"""Markdown → styled terminal lines.

Pure text processing: lines are lists of `Span(text, Style)`, and the TUI theme decides what a
`Style` looks like. Each block type is one small function; `render` tries them in order.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import IntFlag
from typing import Literal, NamedTuple, Optional

CHECKBOX = re.compile(r"^(\s*)[-*]\s+\[([ xX])\]\s?(.*)$")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)")
RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
NORMATIVE = re.compile(r"\b(SHALL|MUST)\b")
INLINE = re.compile(
    r"`(?P<code>[^`]+)`"
    r"|\*\*(?P<bold>.+?)\*\*|__(?P<bold2>.+?)__"
    r"|~~(?P<strike>.+?)~~"
    r"|\[(?P<link>[^\]]+)\]\([^)]+\)"
    r"|(?<![\w*])\*(?!\s)(?P<em>.+?)(?<!\s)\*(?!\w)"
    r"|(?<![\w_])_(?!\s)(?P<em2>.+?)(?<!\s)_(?![\w_])"
)


class Style(IntFlag):
    NONE = 0
    BOLD = 1
    ITALIC = 2
    UNDERLINE = 4
    REVERSE = 8
    # colour roles: at most one per span
    ACCENT = 16
    SUCCESS = 32
    WARNING = 64
    HEADING = 128
    MUTED = 256


class Span(NamedTuple):
    text: str
    style: Style = Style.NONE


Line = list[Span]
Align = Literal["left", "right", "center"]
Block = Callable[[list[str], int, int], Optional[tuple[list[Line], int]]]  # runtime alias: no `|` on 3.9


# ---------------------------------------------------------------- inline text


def inline(text: str, base: Style = Style.NONE) -> Line:
    """`code`, **bold**, *italic*, ~~strike~~ and [links](...) as styled spans."""
    spans: Line = []
    pos = 0
    for match in INLINE.finditer(text):
        if match.start() > pos:
            spans.append(Span(text[pos : match.start()], base))
        spans += _inline_match(match, base)
        pos = match.end()
    if pos < len(text):
        spans.append(Span(text[pos:], base))
    return spans


def _inline_match(match: re.Match[str], base: Style) -> Line:
    group = match.groupdict()
    if group["code"] is not None:
        return [Span(group["code"], Style.ACCENT)]
    if group["strike"] is not None:
        return [Span(group["strike"], Style.MUTED)]
    if group["link"] is not None:
        return inline(group["link"], base | Style.UNDERLINE)
    bold = group["bold"] or group["bold2"]
    if bold:
        return inline(bold, base | Style.BOLD)
    return inline(group["em"] or group["em2"] or "", base | Style.ITALIC)


def plain(line: Line) -> str:
    return "".join(span.text for span in line)


def wrap(line: Line, width: int) -> list[Line]:
    """Word-wrap styled spans to `width`; words longer than a line are split."""
    width = max(width, 1)
    lines: list[Line] = []
    current: Line = []
    used = 0
    for word in _words(line):
        if word.text == " ":
            if 0 < used < width:
                current.append(word)
                used += 1
            continue
        text = word.text
        while len(text) > width:
            if used:
                lines.append(_rstrip(current))
                current, used = [], 0
            lines.append([Span(text[:width], word.style)])
            text = text[width:]
        if used + len(text) > width:
            lines.append(_rstrip(current))
            current, used = [], 0
        current.append(Span(text, word.style))
        used += len(text)
    current = _rstrip(current)
    if current or not lines:
        lines.append(current)
    return lines


def _words(line: Line) -> list[Span]:
    """Spans split into words, with every run of whitespace collapsed to a single " " span."""
    return [
        Span(" " if piece.isspace() else piece, span.style)
        for span in line
        for piece in re.split(r"(\s+)", span.text)
        if piece
    ]


def _rstrip(line: Line) -> Line:
    while line and line[-1].text == " ":
        line = line[:-1]
    return line


# ---------------------------------------------------------------- tables


def split_row(row: str) -> list[str]:
    r"""'| a | `b|c` | d |' -> ['a', '`b|c`', 'd']: pipes inside code spans and \| don't split."""
    row = row.strip().removeprefix("|")
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    cells: list[str] = []
    cell, in_code, i = "", False, 0
    while i < len(row):
        char = row[i]
        if char == "\\" and row[i + 1 : i + 2] == "|":
            cell += "|"
            i += 2
            continue
        if char == "`":
            in_code = not in_code
        if char == "|" and not in_code:
            cells.append(cell.strip())
            cell = ""
        else:
            cell += char
        i += 1
    cells.append(cell.strip())
    return cells


def alignment(separator_cell: str) -> Align:
    cell = separator_cell.strip()
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    return "right" if cell.endswith(":") else "left"


def column_widths(natural: list[int], room: int) -> list[int]:
    """Fit columns into `room`: narrow columns keep their width, wide ones share what's left."""
    if sum(natural) <= room:
        return natural[:]
    fixed: dict[int, int] = {}
    flexible = set(range(len(natural)))
    while flexible:
        share = (room - sum(fixed.values())) // len(flexible)
        narrow = {c for c in flexible if natural[c] <= share}
        if not narrow:
            fixed.update({c: max(share, 3) for c in flexible})
            break
        fixed.update({c: natural[c] for c in narrow})
        flexible -= narrow
    return [fixed[c] for c in range(len(natural))]


def render_table(rows: list[list[str]], aligns: list[Align], width: int) -> list[Line]:
    columns = max(len(r) for r in rows)
    padding: list[Align] = ["left"] * columns
    aligns = (aligns + padding)[:columns]
    cells = [
        [inline(text, Style.BOLD if r == 0 else Style.NONE) for text in row + [""] * (columns - len(row))]
        for r, row in enumerate(rows)
    ]
    natural = [max(1, *(len(plain(row[c])) for row in cells)) for c in range(columns)]
    widths = column_widths(natural, max(width - (3 * columns + 1), columns * 3))

    def rule(left: str, middle: str, right: str) -> Line:
        return [Span(left + middle.join("─" * (w + 2) for w in widths) + right, Style.MUTED)]

    out = [rule("┌", "┬", "┐")]
    for r, row in enumerate(cells):
        wrapped = [wrap(cell, widths[c]) for c, cell in enumerate(row)]
        for n in range(max(len(w) for w in wrapped)):
            line: Line = [Span("│", Style.MUTED)]
            for c, cell_lines in enumerate(wrapped):
                content = cell_lines[n] if n < len(cell_lines) else []
                pad = widths[c] - len(plain(content))
                left = {"right": pad, "center": pad // 2}.get(aligns[c], 0)
                line += [Span(" " * (left + 1)), *content, Span(" " * (pad - left + 1)), Span("│", Style.MUTED)]
            out.append(line)
        if r == 0 and len(cells) > 1:
            out.append(rule("├", "┼", "┤"))
    out.append(rule("└", "┴", "┘"))
    return out


# ---------------------------------------------------------------- blocks


def code_block(src: list[str], i: int, width: int) -> tuple[list[Line], int] | None:
    """A fenced block. Mermaid diagrams collapse to a placeholder (they render in the browser view)."""
    opening = src[i].strip()
    if not opening.startswith("```"):
        return None
    end = next((j for j in range(i + 1, len(src)) if src[j].strip().startswith("```")), len(src))
    body = src[i + 1 : end]
    if opening[3:].strip().lower() == "mermaid":
        kind = next((b.split()[0] for b in body if b.strip()), "")
        title = f"mermaid diagram · {kind}" if kind else "mermaid diagram"
        placeholder = [
            [Span("│ ", Style.HEADING), Span(title, Style.HEADING | Style.BOLD)],
            [Span("│ ", Style.HEADING), Span("press m to view it rendered", Style.MUTED)],
        ]
        return placeholder, end + 1
    fences = [src[i]] + ([src[end]] if end < len(src) else [])
    lines = [[Span(fences[0].rstrip()[:width], Style.MUTED)]]
    lines += [[Span(b.rstrip()[:width], Style.ACCENT)] for b in body]
    lines += [[Span(f.rstrip()[:width], Style.MUTED)] for f in fences[1:]]
    return lines, end + 1


def blank(src: list[str], i: int, width: int) -> tuple[list[Line], int] | None:
    return ([[]], i + 1) if not src[i].strip() else None


def table(src: list[str], i: int, width: int) -> tuple[list[Line], int] | None:
    """A pipe row followed by a separator row, then more pipe rows."""
    if not src[i].lstrip().startswith("|") or i + 1 >= len(src) or not TABLE_SEPARATOR.match(src[i + 1]):
        return None
    end = i + 2
    while end < len(src) and src[end].lstrip().startswith("|"):
        end += 1
    rows = [split_row(src[i])] + [split_row(r) for r in src[i + 2 : end]]
    return render_table(rows, [alignment(c) for c in split_row(src[i + 1])], width), end


def rule(src: list[str], i: int, width: int) -> tuple[list[Line], int] | None:
    return ([[Span("─" * width, Style.MUTED)]], i + 1) if RULE.match(src[i]) else None


def heading(src: list[str], i: int, width: int) -> tuple[list[Line], int] | None:
    match = HEADING.match(src[i])
    if not match:
        return None
    level, title = len(match.group(1)), match.group(2).strip()
    if level == 2 and len(title) < 40:
        title = title.upper()
    style = (Style.HEADING if level == 1 else Style.ACCENT) | Style.BOLD
    spans = [Span(s.text, s.style | style) for s in inline(title)]
    lines: list[Line] = ([[]] if level <= 2 else []) + wrap(spans, width)  # air above major headings
    if level == 1:
        lines.append([Span("─" * min(width, len(plain(spans)) + 2), Style.MUTED)])
    return lines, i + 1


def text_line(src: list[str], i: int, width: int) -> tuple[list[Line], int]:
    """Paragraph lines, list items, checkboxes and quotes; wrapped lines hang under the text."""
    indent, prefix, body, base = _line_parts(src[i].rstrip())
    if not prefix and NORMATIVE.search(body):
        base |= Style.BOLD
    lead = len(indent) + len(plain(prefix))
    chunks = wrap(inline(body, base), max(width - lead, 10))
    first: Line = [Span(indent), *prefix, *chunks[0]]
    return [first] + [[Span(" " * lead), *chunk] for chunk in chunks[1:]], i + 1


def _line_parts(line: str) -> tuple[str, Line, str, Style]:
    """(indent, prefix spans, body text, body style) for one source line."""
    match = CHECKBOX.match(line)
    if match:
        done = match.group(2) != " "
        mark = Span("✓ ", Style.SUCCESS | Style.BOLD) if done else Span("☐ ", Style.WARNING | Style.BOLD)
        return match.group(1), [mark], match.group(3), Style.MUTED if done else Style.NONE
    match = LIST_ITEM.match(line)
    if match:
        bullet = "• " if match.group(2) in "-*+" else f"{match.group(2)} "
        return match.group(1), [Span(bullet, Style.ACCENT)], match.group(3), Style.NONE
    stripped = line.lstrip()
    if stripped.startswith(">"):
        return "", [Span("│ ", Style.MUTED)], stripped[1:].strip(), Style.MUTED
    return line[: len(line) - len(stripped)], [], stripped, Style.NONE


BLOCKS: tuple[Block, ...] = (code_block, blank, table, rule, heading)


def render(text: str, width: int) -> list[Line]:
    """Markdown → lines of styled spans, at most `width` characters wide (tables and text wrap)."""
    width = max(width, 20)
    src = text.splitlines()
    out: list[Line] = []
    i = 0
    while i < len(src):
        result = next((r for r in (block(src, i, width) for block in BLOCKS) if r is not None), None)
        lines, i = result if result is not None else text_line(src, i, width)
        for line in lines:
            if line or (out and out[-1]):  # no leading blank line, never two in a row
                out.append(line)
    return out
