# PoE2 Campaign Overlay

A lightweight, always-on-top checklist overlay for **Path of Exile 2**. Choose the
act you're on, tick off objectives as you play, and customize the look from a
separate settings window. Your current act, checked items, window position, and
all style settings are remembered between sessions.

![overlay + settings](docs-screenshot-placeholder)

## Features

- **Always-on-top overlay** that floats over the game (use Windowed or Borderless mode — see note below).
- **Per-act checklists** for Acts 1–4 and the Ogham / Vastiri / Kriar Interludes — real campaign content (bosses, ascendancy trials, skill-point quests), stored as plain JSON files you can freely edit.
- **Check off objectives** — completed items get a strike-through; progress shows as `done/total` in the header.
- **Switch acts right from the overlay header** — pick any act from the title dropdown, or step to the previous (⏮) / next (⏭) act, or **exit the program** (✕) without using the tray.
- **Remembers everything**: current act, checkmarks, overlay size/position, and style.
- **Separate settings window** with live preview:
  - Transparency (drag the slider or type an exact percentage)
  - Font size
  - Font family (a curated set of **Google Fonts**, downloaded and cached on first use)
  - Font color (click the color square to pick)
  - Background color (click the color square to pick)
  - Scale (overall UI multiplier)
  - **Reset progress** for the current act, **Reset all progress**, or **Reset settings**
- **Drag to move** the overlay any time; **drag the edges/corners to resize** while the settings window is open.
- **Lock the overlay position** with the lock button (next to the settings gear) to prevent accidental dragging.
- **System tray icon** for Settings, Show/Hide, Reset position, and Quit.

## Requirements

- Windows
- [Python 3.10+](https://www.python.org/downloads/) (tick "Add Python to PATH" during install)

## Quick start (run from source)

1. Double-click **`setup.bat`** once to install the dependency (PyQt6).
2. Double-click **`run.bat`** to launch the overlay.

The overlay appears in the top-right of your primary screen. Click the **⚙ gear**
in its header (or the tray icon) to open **Settings**. Click the **✕** in the
header to exit the program (the tray menu's **Quit** does the same).

## Build a standalone .exe (optional)

If you'd rather not keep Python around, double-click **`build_exe.bat`**. When it
finishes you'll have a self-contained app at:

```
dist\PoE2CampaignOverlay\PoE2CampaignOverlay.exe
```

The `acts\` folder is copied next to the `.exe` so you can keep editing your
checklists. You can move the whole `PoE2CampaignOverlay` folder anywhere.

## Using it while playing

Path of Exile 2 must run in **Windowed** or **Windowed Fullscreen / Borderless**
mode for any overlay to show on top of it. True exclusive-fullscreen hides all
overlays — this is a Windows limitation, not specific to this app.

Because the overlay is **always interactive**, clicks inside its panel hit the
checkboxes (not the game). Drag it to a corner you don't click during combat, or
use the tray icon's **Show / hide overlay** to tuck it away when you don't need it.

## Editing the checklists

Each act is one JSON file in the **`acts\`** folder. Add, remove, or rename files
freely — the app loads every `*.json` in that folder, sorted by `order`.

```json
{
  "id": "act1",                       // unique id (used to store your progress)
  "name": "Act 1 — Ogham",            // shown in the dropdown and overlay header
  "order": 1,                          // sort position in the dropdown
  "items": [
    { "id": "a1-01", "category": "Skill Points & Bonuses", "text": "Reach Clearfell Encampment" },
    { "id": "a1-02", "text": "Defeat The Bloated Miller" }
  ]
}
```

Field notes:

- **`id`** (item) — keep it stable and unique within the act. Your checkmarks are
  stored against this id, so renaming `text` keeps progress, but changing `id`
  resets that item.
- **`category`** — optional. Consecutive items with the same category are grouped
  under a heading. Omit it for a flat list.
- To add or reorder acts, just drop a new `*.json` file into `acts\` with the
  right `order` value — the app picks it up automatically (the filename itself
  doesn't matter; sorting uses `order`).

The included files cover **Acts 1–4 plus the Ogham, Vastiri, and Kriar
Interludes**, populated with real campaign content — bosses, ascendancy trials,
skill-point quests, and permanent-reward locations — current to the **0.5
"Return of the Ancients"** era. Path of Exile 2 is still being updated, so
double-check against the latest patch and tweak any wording you like; every item
is yours to edit.

## Where your data lives

A `data\` folder is created next to the app:

- `data\config.json` — settings, current act, and overlay geometry
- `data\progress.json` — your checked items per act
- `data\fonts\` — Google Font files cached after their first use

Delete these to start fresh. (To reset just one act's checkmarks, use
**Reset progress (this act)** in Settings.)

## Project layout

```
PoE2-Campaign-Overlay\
├─ main.py              # entry point + system tray
├─ overlay_window.py    # the always-on-top checklist overlay
├─ settings_window.py   # the separate settings window
├─ app_state.py         # config + progress + act loading/saving
├─ google_fonts.py      # downloads & caches Google Fonts on demand
├─ acts\                # one JSON file per act (edit these!)
├─ requirements.txt
├─ setup.bat            # install dependencies
├─ run.bat              # launch
└─ build_exe.bat        # build a standalone .exe
```

## Troubleshooting

- **Overlay doesn't show over the game** → switch PoE2 to Windowed / Borderless.
- **Overlay went off-screen** → tray icon → *Reset overlay position*.
- **`python` not recognized** → reinstall Python with "Add to PATH" checked.
- **Want it to launch with Windows** → put a shortcut to `run.bat` in your
  Startup folder (`Win+R` → `shell:startup`).
