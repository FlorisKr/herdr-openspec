# herdr-openspec

See where every [OpenSpec](https://github.com/Fission-AI/OpenSpec) project stands, right inside
[herdr](https://herdr.dev), and open a change's tasks, proposal, design and specs with one key.

```
● web-app                           ┌ OpenSpec · web-app — 1 open change ─────────────────────────┐
  main  +2 ~1                       │ ▸✎add-dark-mode-toggle         ██████████░░ 19/22  T P D S  │
  ✎ 19/22 ▰▰▰▰▰▱                    │ ─────────────────────────────────────────────────────────── │
  add-dark-mode-toggle              │   ✓ 1. Theme tokens                          4/4            │
● api                               │   ◐ 3. Settings toggle                       5/7            │
  master                            │   next ▸ 3.6 Persist the choice per user                    │
  ◇ 10 open · 5 to archive          └─────────────────────────────────────────────────────────────┘
```

## Features

**Sidebar status** for every workspace that contains an OpenSpec project:

- `◇ 10 open · 5 to archive` — overview when nothing is being worked on locally.
- `✎ 19/22 ▰▰▰▰▰▱` + change name — when a change has local (uncommitted or untracked) edits.

It refreshes on herdr startup and on agent/pane events (an agent finishing a turn, switching
panes, …). Nothing runs while herdr is closed.

**Change browser** (`ctrl+b t`) — a popup for the project of the pane you're in:

- Every open change with a progress bar, task count, creation date and which docs exist (`T P D S`).
- The selected change's task groups (✓ done, ◐ started, ○ not started) and its next open task.
- `⏎` opens the change in tabs: **Tasks · Proposal · Design · Specs**, with formatted markdown.
- `m` opens the whole change as a web page with Mermaid diagrams rendered.

| Key | Action |
| --- | --- |
| `↑↓` / `j k` | Move / scroll |
| `⏎` or `1`–`4` | Open a change (at that tab) |
| `⇥` / `1`–`4` | Switch tab |
| `space` / `b`, `g` / `G` | Page down / up, top / end |
| `e` | Edit the current file in `$EDITOR` |
| `m` | Open in the browser (diagrams rendered) |
| `r` | Reload |
| `esc` / `q` | Back / quit |

## Requirements

- herdr ≥ 0.9.3
- Python 3.9+ (standard library only)
- git (to detect local edits)
- macOS or Linux (on Linux, `m` uses `xdg-open`)

## Install

```sh
herdr plugin install FlorisKr/herdr-openspec
```

Then add the key binding and sidebar rows to `~/.config/herdr/config.toml` — copy them from
[`herdr-config.toml`](herdr-config.toml) — and reload with `herdr server reload-config`.
Plugins can't change your herdr config, so this step is manual.

Optional: put `ospec` on your `PATH` to use it outside the popup.

```sh
ln -s "$(herdr plugin list --json | python3 -c 'import json,sys; print(next(p["plugin_root"] for p in json.load(sys.stdin)["result"]["plugins"] if p["plugin_id"] == "openspec"))')/bin/ospec" ~/.local/bin/ospec
```

## Command line

```
ospec [PATH]     Browse the OpenSpec project at PATH (default: current directory)
ospec sync       Refresh the herdr sidebar (the plugin runs this for you)
```

Archived changes (`openspec/changes/archive/`) aren't shown: ospec is about work in progress.

## Development

Clone the repo and run `./install.sh`. It links the checkout as the herdr plugin, symlinks
`bin/ospec` into `~/.local/bin`, and adds the config snippet if it's missing. Edits take effect
immediately.

```
bin/ospec              launcher (what herdr and your shell run)
src/ospec/
  cli.py               commands; builds Settings and the herdr client, passes them down
  config.py            Settings, read once from the environment
  model.py             Change, TaskGroup, DocKind, tasks.md parsing           (pure)
  repository.py        finding projects, loading changes from disk
  status.py            sidebar rules: overview vs. the locally edited change   (pure)
  markdown.py          markdown → styled lines, no curses                      (pure)
  page.py, page.html   the browser view
  git.py, herdr.py,    thin adapters around git, the herdr CLI,
  system.py            and the desktop (browser, editor)
  workspaces.py        herdr workspace → project
  sync.py              pushes status into the sidebar
  tui/                 curses UI: theme (Style → curses), canvas, views, app
tests/                 unittest, standard library only
```

```sh
PYTHONPATH=src python3 -m unittest discover -s tests   # tests
ruff check . && ruff format --check . && pyright        # lint, format, types
```

## Uninstall

```sh
herdr plugin uninstall openspec   # or `herdr plugin unlink openspec` for a dev checkout
rm -f ~/.local/bin/ospec
```

Then remove the "OpenSpec" blocks from `~/.config/herdr/config.toml`.

## License

MIT
