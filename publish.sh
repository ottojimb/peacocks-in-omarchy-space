#!/usr/bin/env bash
# Publish each theme in themes/ as its own GitHub repository, the layout
# `omarchy theme install` expects (colors.toml at the repository root).
# Each theme repo is a `git subtree split` of themes/<name>, so its history
# follows this repository. Creates missing repositories with gh.
set -euo pipefail

owner="${PEACOCKS_GITHUB_OWNER:-ottojimb}"
cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ -n $(git status --porcelain) ]]; then
  echo "Commit your changes before publishing." >&2
  exit 1
fi

for dir in themes/*/; do
  name=$(basename "$dir")
  repo="omarchy-$name-theme"
  label=$(head -1 "$dir/README.md" | sed -E 's/^# //; s/ for Omarchy$//')

  if ! gh repo view "$owner/$repo" >/dev/null 2>&1; then
    gh repo create "$owner/$repo" --public \
      --description "$label theme for Omarchy, adapted from Rainglow's Peacocks in Space" \
      --homepage "https://github.com/$owner/peacocks-in-omarchy-space"
    gh repo edit "$owner/$repo" --add-topic omarchy,omarchy-theme,hyprland,rainglow,peacocks-in-space
  fi

  sha=$(git subtree split --prefix="themes/$name" 2>/dev/null)
  git push "https://github.com/$owner/$repo.git" "$sha:refs/heads/main"
  echo "Published $name -> https://github.com/$owner/$repo"
done
