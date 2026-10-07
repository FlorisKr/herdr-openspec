"""A change as one web page: markdown and Mermaid diagrams rendered in the browser."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import TYPE_CHECKING

from ospec.model import DocKind

if TYPE_CHECKING:
    from ospec.model import Change

TEMPLATE = Path(__file__).with_name("page.html")
SECTION_ORDER = (DocKind.PROPOSAL, DocKind.DESIGN, DocKind.TASKS)


def sections(change: Change) -> list[dict[str, str]]:
    """Page sections in reading order; the first spec gets id "specs" so #specs lands on it."""
    found = [
        {"id": kind.slug, "label": kind.label, "markdown": change.read(kind)}
        for kind in SECTION_ORDER
        if change.has(kind)
    ]
    for index, spec in enumerate(change.doc_files(DocKind.SPECS)):
        anchor = DocKind.SPECS.slug if index == 0 else f"spec-{spec.parent.name}"
        found.append({"id": anchor, "label": f"Spec · {spec.parent.name}", "markdown": spec.read_text()})
    return found


def render_page(title: str, page_sections: list[dict[str, str]]) -> str:
    nav = "".join(f'<a href="#{html.escape(s["id"])}">{html.escape(s["label"])}</a>' for s in page_sections)
    data = json.dumps(page_sections).replace("</", "<\\/")  # keep "</script>" inside markdown harmless
    return (
        TEMPLATE.read_text().replace("__TITLE__", html.escape(title)).replace("__NAV__", nav).replace("__DOCS__", data)
    )


def write_page(project: Path, change: Change, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{project.name}--{change.path.name}.html"
    out.write_text(render_page(f"{project.name} › {change.name}", sections(change)))
    return out
