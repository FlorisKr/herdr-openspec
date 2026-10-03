#!/usr/bin/env bash
# Dev install: link this checkout as the herdr plugin, put ospec on PATH, add the config snippet.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
herdr_cfg="$HOME/.config/herdr/config.toml"

ln -sfn "$here/bin/ospec" "$HOME/.local/bin/ospec"

herdr plugin unlink openspec >/dev/null 2>&1 || true
herdr plugin link "$here" >/dev/null

if ! grep -q "# OpenSpec browser" "$herdr_cfg" 2>/dev/null; then
  printf '\n' >> "$herdr_cfg"
  cat "$here/herdr-config.toml" >> "$herdr_cfg"
fi
herdr server reload-config >/dev/null || true

echo "ospec installed — ctrl+b t in herdr"
