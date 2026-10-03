"""ospec — OpenSpec status and change browser for herdr.

Usage:
  ospec [PATH]     Browse the OpenSpec project at PATH (default: the current directory)
  ospec sync       Refresh the herdr sidebar ($openspec and $openspec_change tokens)
  ospec popup      Open the browser as a herdr popup (used by the plugin action)

Project lookup: PATH > $OSPEC_PROJECT > current directory > focused herdr workspace.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ospec.config import Settings
from ospec.herdr import Herdr
from ospec.repository import find_project
from ospec.sync import sync
from ospec.tui.app import run_tui
from ospec.workspaces import focused_project

if TYPE_CHECKING:
    from collections.abc import Sequence

POPUP_ENTRYPOINT = "browser"  # the [[panes]] id in herdr-plugin.toml


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else ""
    settings = Settings.from_env(os.environ)
    herdr = Herdr()
    if command in ("-h", "--help"):
        print(__doc__)
        return 0
    if command == "sync":
        return sync(herdr, settings.cache_dir)
    if command == "popup":
        return popup(settings, herdr)
    if command and not Path(command).expanduser().exists():
        print(f"ospec: no such command or path: {command}\n\n{__doc__}", file=sys.stderr)
        return 2
    return browse(settings, herdr, command or None)


def resolve_project(settings: Settings, herdr: Herdr, hint: str | None) -> Path | None:
    for candidate in (hint, settings.project_hint, Path.cwd()):
        project = find_project(candidate) if candidate else None
        if project:
            return project
    return focused_project(herdr) if settings.in_herdr else None


def browse(settings: Settings, herdr: Herdr, hint: str | None) -> int:
    run_tui(settings, resolve_project(settings, herdr, hint))
    if settings.in_herdr:
        sync(herdr, settings.cache_dir)
    return 0


def popup(settings: Settings, herdr: Herdr) -> int:
    """Plugin action: open the browser popup for the pane the action was invoked from."""
    context = settings.plugin_context
    cwd = context.get("focused_pane_cwd") or context.get("workspace_cwd")
    project = find_project(cwd) if cwd else focused_project(herdr)
    env = {"OSPEC_PROJECT": str(project)} if project else {}
    try:
        result = herdr.open_plugin_popup(settings.plugin_id, POPUP_ENTRYPOINT, cwd=project, env=env)
    except OSError as error:
        print(f"ospec: can't run herdr: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(result.stdout)  # shows up in `herdr plugin log list`
    sys.stderr.write(result.stderr)
    return result.returncode
