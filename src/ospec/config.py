"""Settings: everything ospec reads from the environment, resolved once at startup."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class Settings:
    cache_dir: Path
    editor: str
    in_herdr: bool = False
    plugin_id: str = "openspec"
    project_hint: str | None = None  # $OSPEC_PROJECT: set by the plugin popup
    plugin_context: Mapping[str, Any] = field(default_factory=dict)  # $HERDR_PLUGIN_CONTEXT_JSON

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Settings:
        cache_home = Path(env.get("XDG_CACHE_HOME") or "~/.cache").expanduser()
        return cls(
            cache_dir=cache_home / "ospec",
            editor=env.get("EDITOR") or shutil.which("nvim") or shutil.which("vim") or "vi",
            in_herdr=env.get("HERDR_ENV") == "1",
            plugin_id=env.get("HERDR_PLUGIN_ID") or "openspec",
            project_hint=env.get("OSPEC_PROJECT") or None,
            plugin_context=_json_object(env.get("HERDR_PLUGIN_CONTEXT_JSON")),
        )


def _json_object(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value) if value else {}
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
