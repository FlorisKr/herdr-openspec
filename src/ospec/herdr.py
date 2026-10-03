"""A small client for the herdr CLI: only the calls ospec needs, with typed results."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


@dataclass(frozen=True)
class Workspace:
    id: str
    focused: bool


@dataclass(frozen=True)
class Pane:
    workspace_id: str
    cwd: str
    focused: bool


class Herdr:
    def __init__(self, binary: str | None = None, run: Runner = subprocess.run) -> None:
        self.binary = binary or shutil.which("herdr") or str(Path("~/.local/bin/herdr").expanduser())
        self._run = run

    def run(self, *args: str, timeout: float = 5) -> subprocess.CompletedProcess[str]:
        return self._run([self.binary, *args], capture_output=True, text=True, timeout=timeout, check=False)

    def call(self, *args: str) -> dict[str, Any] | None:
        """The `result` object of a herdr command, or None if herdr is unreachable or the call failed."""
        try:
            completed = self.run(*args)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            return None
        try:
            result = json.loads(completed.stdout)["result"]
        except (ValueError, KeyError, TypeError):
            return None
        return result if isinstance(result, dict) else None

    def workspaces(self) -> list[Workspace] | None:
        result = self.call("workspace", "list")
        if result is None:
            return None
        return [Workspace(w["workspace_id"], bool(w.get("focused"))) for w in result.get("workspaces", [])]

    def panes(self) -> list[Pane]:
        result = self.call("pane", "list") or {}
        return [
            Pane(p["workspace_id"], p.get("foreground_cwd") or p.get("cwd") or "", bool(p.get("focused")))
            for p in result.get("panes", [])
        ]

    def report_tokens(self, workspace_id: str, source: str, tokens: Mapping[str, str]) -> None:
        args = [f"{name}={value}" for name, value in tokens.items()]
        self.call("workspace", "report-metadata", workspace_id, "--source", source, *_flagged("--token", args))

    def clear_tokens(self, workspace_id: str, source: str, names: Iterable[str]) -> None:
        self.call("workspace", "report-metadata", workspace_id, "--source", source, *_flagged("--clear-token", names))

    def open_plugin_popup(
        self,
        plugin_id: str,
        entrypoint: str,
        *,
        cwd: Path | None,
        env: Mapping[str, str],
    ) -> subprocess.CompletedProcess[str]:
        """Open a plugin pane as a popup over the active pane; returns herdr's raw result."""
        args = [
            "plugin",
            "pane",
            "open",
            "--plugin",
            plugin_id,
            "--entrypoint",
            entrypoint,
            "--placement",
            "popup",
            "--width",
            "90%",
            "--height",
            "90%",
            "--focus",
        ]
        args += _flagged("--env", [f"{k}={v}" for k, v in env.items()])
        if cwd is not None:
            args += ["--cwd", str(cwd)]
        return self.run(*args, timeout=10)


def _flagged(flag: str, values: Iterable[str]) -> list[str]:
    """('--token', ['a', 'b']) -> ['--token', 'a', '--token', 'b']"""
    return [part for value in values for part in (flag, value)]
