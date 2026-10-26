#!/usr/bin/env bash
# Link the Peacocks in Space themes into Omarchy's user themes directory.
# Omarchy honours neovim.lua and vscode.json only for symlinked or hand-made
# themes; a theme installed with `omarchy theme install` (a git clone) drops them.
set -euo pipefail

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/themes"
dest="$HOME/.config/omarchy/themes"
mkdir -p "$dest"

for theme in "$src"/*/; do
  name=$(basename "$theme")
  target="$dest/$name"
  if [[ -e $target && ! -L $target ]]; then
    echo "Skipping $name: $target exists and is not a symlink." >&2
    continue
  fi
  ln -sfn "${theme%/}" "$target"
  echo "Linked $name"
done

echo "Apply one with: omarchy-theme-set peacocks-in-space"
