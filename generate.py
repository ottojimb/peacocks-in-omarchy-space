#!/usr/bin/env python3
"""Build the Peacocks in Space themes for Omarchy from a single palette.

    python3 generate.py           write the theme files
    python3 generate.py --assets  also render wallpapers and preview.png
                                  (needs google-chrome-stable or chromium, and Pillow)

Source palettes: https://github.com/rainglow/vscode (peacocks-in-space*.json).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
THEMES_DIR = ROOT / "themes"
RENDER_DIR = ROOT / "render"

# Rainglow accents shared by the three variants.
TEAL = "#26a6a6"
ORANGE = "#ff5d38"
LIME = "#bcd42a"
LIME_LIGHT = "#a6b73a"  # Rainglow Light's lime

# Eight-hue terminal palette. Teal, orange, lime and red come from Rainglow, gold and
# violet from its git and notification colors; the blue is derived to match.
ANSI_DARK = {
    "red": "#f03e5f",
    "yellow": "#f7b83d",
    "orange": ORANGE,
    "green": LIME,
    "cyan": TEAL,
    "blue": "#629ada",
    "magenta": "#b360fb",
    "brown": "#664e4d",
    "bright_red": "#ff6682",
    "bright_yellow": "#fad181",
    "bright_green": "#d7e67e",
    "bright_cyan": "#59d9d9",
    "bright_blue": "#8bb5e4",
    "bright_magenta": "#c98ffc",
}

# Light keeps the same hues, darkened so they read as text on #dee3ec (>= 4.4:1).
ANSI_LIGHT = {
    "red": "#a30e29",
    "yellow": "#8b5e04",
    "orange": "#bd2f0f",
    "green": "#5f6b0f",
    "cyan": "#176d6d",
    "blue": "#225691",
    "magenta": "#6a1faf",
    "brown": "#664e4d",
    "bright_red": "#e61f44",
    "bright_yellow": "#c48405",
    "bright_green": "#59a50b",
    "bright_cyan": TEAL,
    "bright_blue": "#2f6fb8",
    "bright_magenta": "#9d37fc",
}

# Peacock-eye colors for the wallpapers (shared by all variants).
FEATHER = {
    "core": "#0e1f3f",
    "blue": "#2f6fb8",
    "teal": TEAL,
    "teal_bright": "#59d9d9",
    "bronze": "#a24a2a",
    "gold": "#f7b83d",
    "lime": LIME,
    "orange": ORANGE,
}

VARIANTS = [
    {
        "id": "peacocks-in-space",
        "label": "Peacocks In Space",
        "vscode": "Peacocks In Space (rainglow)",
        "mode": "dark",
        "background": "#2b303b",
        "dark_background": "#22262f",
        "darker_background": "#16181d",
        "lighter_background": "#363c4a",
        "inactive_border": "#414858",
        "foreground": "#dee3ec",
        "dark_foreground": "#8993a9",
        "light_foreground": "#eef1f5",
        "bright_foreground": "#ffffff",
        "muted": "#6e7a94",
        "accent": TEAL,
        "border": (TEAL, LIME, ORANGE),
        "selection_veil": 0.30,
        "ansi": ANSI_DARK,
        "syntax": {"teal": TEAL, "orange": ORANGE, "lime": LIME, "fg": "#dee3ec", "comment": "#6e7a94"},
        "wallpaper": {"mode": "dark", "top": "#242a35", "bottom": "#0f1115", "nebula": 0.55, "stars": 1.0},
    },
    {
        "id": "peacocks-in-space-contrast",
        "label": "Peacocks In Space Contrast",
        "vscode": "Peacocks In Space Contrast (rainglow)",
        "mode": "dark",
        "background": "#121419",
        "dark_background": "#0e0f13",
        "darker_background": "#07080a",
        "lighter_background": "#1d2028",
        "inactive_border": "#272c37",
        "foreground": "#dee3ec",
        "dark_foreground": "#677390",
        "light_foreground": "#eef1f5",
        "bright_foreground": "#ffffff",
        "muted": "#6e7a94",
        "accent": TEAL,
        "border": (TEAL, LIME, ORANGE),
        "selection_veil": 0.30,
        "ansi": ANSI_DARK,
        "syntax": {"teal": TEAL, "orange": ORANGE, "lime": LIME, "fg": "#dee3ec", "comment": "#6e7a94"},
        "wallpaper": {"mode": "dark", "top": "#0d0f13", "bottom": "#020203", "nebula": 0.42, "stars": 1.25},
    },
    {
        "id": "peacocks-in-space-light",
        "label": "Peacocks In Space Light",
        "vscode": "Peacocks In Space Light (rainglow)",
        "mode": "light",
        "background": "#dee3ec",
        "dark_background": "#d4dbe6",
        "darker_background": "#ced5e3",
        "lighter_background": "#d1d8e5",
        "inactive_border": "#eef1f5",
        "foreground": "#2b303b",
        "dark_foreground": "#616c85",
        "light_foreground": "#363c4a",
        "bright_foreground": "#20242c",
        "muted": "#6e7a94",
        # Text-safe teal; borders keep the vivid accents through the gradient.
        "accent": "#176d6d",
        "border": (TEAL, LIME_LIGHT, ORANGE),
        "selection_veil": 0.22,
        "ansi": ANSI_LIGHT,
        "syntax": {"teal": "#176d6d", "orange": "#bd2f0f", "lime": "#5f6b0f", "fg": "#2b303b", "comment": "#6e7a94"},
        "wallpaper": {"mode": "light", "top": "#eceff5", "bottom": "#cfd6e3", "nebula": 0.5, "stars": 0.0},
    },
]

WALLPAPERS = [("1-peacock-eye", "eye"), ("2-plumage", "plumage"), ("3-nebula", "nebula")]
ICON_THEME = "Yaru-prussiangreen"
VSCODE_EXTENSION = "daylerees.rainglow"

GITHUB_OWNER = "ottojimb"
SOURCE_REPO = "peacocks-in-omarchy-space"


def theme_repo(theme_id: str) -> str:
    """Repository name; `omarchy theme install` strips `omarchy-` and `-theme` to get the theme name."""
    return f"omarchy-{theme_id}-theme"


THEME_README = Template('''\
# $label for Omarchy

An Omarchy 4 theme adapted from Peacocks in Space by [Rainglow](https://github.com/rainglow/vscode).

Variants: $variants

![$label](preview.png)

## Install

```bash
omarchy theme install https://github.com/$owner/$repo
```

Omarchy skips `neovim.lua` and `vscode.json` in themes installed from git, so Neovim uses the
syntax colors aether derives from `colors.toml`. For Rainglow's syntax in Neovim and the Rainglow
VS Code theme, install all three variants from the [source repository]($source_url) instead:

```bash
git clone $source_url
cd $source_repo && ./install.sh
```

## What's included

- Peacock-feather gradient on window borders, carried to notifications, the launcher and the lock screen
- Eight-hue terminal palette built from Rainglow's accents
- Three 4K wallpapers drawn from the palette: a peacock eye, a fanned plumage and a nebula

## Credits

Palette: Peacocks in Space by Dayle Rees, from Rainglow (MIT). This repository is generated
from [$source_repo]($source_url); send changes there.
''')

COLORS_ORDER = [
    "mode", "",
    "accent", "selection", "muted", "",
    "background", "dark_background", "darker_background", "lighter_background", "",
    "foreground", "dark_foreground", "light_foreground", "bright_foreground", "",
    "red", "yellow", "orange", "green", "cyan", "blue", "magenta", "brown", "",
    "bright_red", "bright_yellow", "bright_green", "bright_cyan", "bright_blue", "bright_magenta", "",
    "hyprland_active_border", "hyprland_inactive_border",
]

NEOVIM_TEMPLATE = Template('''\
-- Generated by generate.py. Edit the palette there and regenerate.
--
-- aether builds the editor UI from the Omarchy colors below. on_highlights
-- swaps its syntax roles for Rainglow's: teal keywords and operators, lime
-- strings, numbers and functions, orange types, builtins and literals.
local syntax = {
  teal = "$syn_teal",
  orange = "$syn_orange",
  lime = "$syn_lime",
  fg = "$syn_fg",
  comment = "$syn_comment",
}

local groups = {
  comment = { "Comment", "SpecialComment", "@comment" },
  teal = {
    "Keyword", "Statement", "Conditional", "Repeat", "Exception", "Include", "Define",
    "PreProc", "Macro", "Operator", "Tag",
    "@keyword", "@keyword.function", "@keyword.return", "@keyword.conditional",
    "@keyword.repeat", "@keyword.import", "@keyword.exception", "@keyword.operator",
    "@keyword.coroutine", "@keyword.type", "@keyword.directive",
    "@operator", "@tag", "@punctuation.special",
    "@markup.link", "@markup.link.url", "@markup.strong", "@markup.italic", "@markup.list",
  },
  lime = {
    "String", "Character", "Number", "Float", "Function",
    "@string", "@character", "@number", "@number.float",
    "@function", "@function.call", "@function.method", "@function.method.call",
    "@markup.raw",
  },
  orange = {
    "Type", "Typedef", "Structure", "StorageClass", "Boolean", "Constant", "Special", "SpecialChar",
    "@type", "@type.builtin", "@type.definition", "@constructor", "@boolean",
    "@constant.builtin", "@constant.macro", "@function.builtin", "@variable.builtin",
    "@module.builtin", "@keyword.modifier", "@keyword.storage", "@string.escape",
    "@string.special", "@tag.attribute", "@markup.heading",
  },
  fg = {
    "Identifier", "@variable", "@variable.parameter", "@variable.member", "@property",
    "@constant", "@module", "@punctuation.bracket", "@punctuation.delimiter", "@tag.delimiter",
  },
}

for level = 1, 6 do
  table.insert(groups.orange, "@markup.heading." .. level .. ".markdown")
end

return {
  {
    "bjarneo/aether.nvim",
    branch = "v3",
    name = "aether",
    priority = 1000,
    opts = {
      styles = {
        comments = { italic = false },
        keywords = { italic = false },
      },
      colors = {
        bg = "$background",
        dark_bg = "$dark_background",
        darker_bg = "$darker_background",
        lighter_bg = "$lighter_background",

        fg = "$foreground",
        dark_fg = "$dark_foreground",
        light_fg = "$light_foreground",
        bright_fg = "$bright_foreground",
        muted = "$muted",

        red = "$red",
        yellow = "$yellow",
        orange = "$orange",
        green = "$green",
        cyan = "$cyan",
        blue = "$blue",
        magenta = "$magenta",
        brown = "$brown",

        bright_red = "$bright_red",
        bright_yellow = "$bright_yellow",
        bright_green = "$bright_green",
        bright_cyan = "$bright_cyan",
        bright_blue = "$bright_blue",
        bright_magenta = "$bright_magenta",

        accent = "$accent",
        cursor = "$bright_foreground",
        foreground = "$foreground",
        background = "$background",
        selection = "$selection",
        selection_foreground = "$bright_foreground",
        selection_background = "$selection",
      },
      on_highlights = function(hl)
        for role, names in pairs(groups) do
          for _, name in ipairs(names) do
            hl[name] = { fg = syntax[role] }
          end
        end
      end,
    },
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "aether",
    },
  },
}
''')


def mix(a: str, b: str, t: float) -> str:
    """Mix color a toward b by t, like Omarchy's `mix a b t`."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(x * (1 - t) + y * t + 0.5):02x}" for x, y in zip(ca, cb))


def theme_colors(v: dict) -> dict:
    keys = ["mode", "background", "dark_background", "darker_background", "lighter_background",
            "foreground", "dark_foreground", "light_foreground", "bright_foreground", "muted", "accent"]
    colors = {k: v[k] for k in keys}
    colors.update(v["ansi"])
    colors["selection"] = mix(v["background"], TEAL, v["selection_veil"])
    colors["hyprland_active_border"] = " ".join(v["border"]) + " 45deg"
    colors["hyprland_inactive_border"] = v["inactive_border"]
    return colors


def colors_toml(colors: dict) -> str:
    out = ["# Generated by generate.py. Edit the palette there and regenerate."]
    for key in COLORS_ORDER:
        if key == "":
            out.append("")
        elif key in colors:
            out.append(f'{key} = "{colors[key]}"')
    return "\n".join(out).rstrip() + "\n"


def write_theme(v: dict) -> dict:
    colors = theme_colors(v)
    target = THEMES_DIR / v["id"]
    target.mkdir(parents=True, exist_ok=True)
    (target / "colors.toml").write_text(colors_toml(colors))
    syn = {f"syn_{k}": val for k, val in v["syntax"].items()}
    (target / "neovim.lua").write_text(NEOVIM_TEMPLATE.substitute(**colors, **syn))
    (target / "vscode.json").write_text(json.dumps({"name": v["vscode"], "extension": VSCODE_EXTENSION}, indent=2) + "\n")
    (target / "icons.theme").write_text(ICON_THEME + "\n")
    write_repo_files(v, target)
    return colors


def write_repo_files(v: dict, target: Path) -> None:
    """README and LICENSE so each theme directory works as a standalone repository."""
    source_url = f"https://github.com/{GITHUB_OWNER}/{SOURCE_REPO}"
    variants = " · ".join(
        f"**{o['label']}**" if o["id"] == v["id"] else f"[{o['label']}](https://github.com/{GITHUB_OWNER}/{theme_repo(o['id'])})"
        for o in VARIANTS
    )
    (target / "README.md").write_text(THEME_README.substitute(
        label=v["label"], variants=variants, owner=GITHUB_OWNER, repo=theme_repo(v["id"]),
        source_url=source_url, source_repo=SOURCE_REPO,
    ))
    shutil.copyfile(ROOT / "LICENSE", target / "LICENSE")


def write_render_data(themes: dict) -> None:
    data = "// Generated by generate.py.\nwindow.THEMES = " + json.dumps(themes, indent=2) + ";\n"
    (RENDER_DIR / "themes.js").write_text(data)


def find_chrome() -> str:
    for name in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("Rendering assets needs google-chrome-stable or chromium on PATH.")


def screenshot(chrome: str, page: Path, query: str, size: tuple[int, int], out: Path, profile: Path, scale: float = 1) -> None:
    """Render a page headless. Runs must stay sequential: they share one Chrome profile."""
    url = page.resolve().as_uri() + "?" + query
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
         "--allow-file-access-from-files", f"--user-data-dir={profile}",
         f"--force-device-scale-factor={scale}", f"--window-size={size[0]},{size[1]}",
         "--virtual-time-budget=15000", f"--screenshot={out}", url],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def render_assets() -> None:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Rendering assets needs Pillow (python-pillow).")

    chrome = find_chrome()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        profile = tmp_path / "profile"
        for v in VARIANTS:
            backgrounds = THEMES_DIR / v["id"] / "backgrounds"
            backgrounds.mkdir(parents=True, exist_ok=True)
            for name, kind in WALLPAPERS:
                png = tmp_path / f"{v['id']}-{name}.png"
                screenshot(chrome, RENDER_DIR / "wallpaper.html", f"theme={v['id']}&kind={kind}", (3840, 2160), png, profile)
                Image.open(png).convert("RGB").save(backgrounds / f"{name}.jpg", quality=92, subsampling=0, optimize=True, progressive=True)
                print(f"  {v['id']}/backgrounds/{name}.jpg")

            png = tmp_path / f"{v['id']}-preview.png"
            screenshot(chrome, RENDER_DIR / "preview.html", f"theme={v['id']}", (1600, 900), png, profile, scale=1.125)
            preview = Image.open(png).convert("RGB").resize((1800, 1012), Image.LANCZOS)
            preview.quantize(colors=256, dither=Image.Dither.FLOYDSTEINBERG).save(THEMES_DIR / v["id"] / "preview.png", optimize=True)
            print(f"  {v['id']}/preview.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--assets", action="store_true", help="also render wallpapers and preview.png")
    args = parser.parse_args()

    render_data = {}
    for v in VARIANTS:
        colors = write_theme(v)
        render_data[v["id"]] = {
            "label": v["label"],
            "colors": colors,
            "syntax": v["syntax"],
            "wallpaper": v["wallpaper"],
            "feather": FEATHER,
            "background": f"../themes/{v['id']}/backgrounds/{WALLPAPERS[0][0]}.jpg",
        }
        print(f"  {v['id']}: colors.toml, neovim.lua, vscode.json, icons.theme, README.md, LICENSE")
    write_render_data(render_data)

    if args.assets:
        render_assets()


if __name__ == "__main__":
    main()
