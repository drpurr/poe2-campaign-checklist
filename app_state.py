"""Configuration, act data, and progress persistence for the PoE2 Campaign Overlay.

Everything is stored *next to the app* so the whole thing is portable:
- acts/*.json      -> the checklist definition for each act (you can edit these)
- data/config.json -> overlay settings + which act you're on + window geometry
- data/progress.json -> which items you've checked off, per act
"""

import json
import sys
from pathlib import Path

# Resolve the application's base directory whether we're running from source
# (python main.py) or from a PyInstaller-built executable.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

ACTS_DIR = BASE_DIR / "acts"
DATA_DIR = BASE_DIR / "data"
CONFIG_PATH = DATA_DIR / "config.json"
PROGRESS_PATH = DATA_DIR / "progress.json"

DEFAULT_CONFIG = {
    "current_act": None,
    "transparency": 0.85,        # background panel alpha, 0.2 - 1.0
    "font_size": 14,             # base text size in points
    "font_family": "Roboto",     # a Google Font family
    "font_color": "#f0e6d2",     # PoE-ish parchment color
    "bg_color": "#121218",       # overlay panel background color
    "scale": 1.0,                # global UI scale multiplier, 0.5 - 3.0
    "overlay_geometry": None,    # [x, y, w, h]
}


class AppState:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.acts = self._load_acts()
        self.acts_by_id = {a["id"]: a for a in self.acts}
        self.config = self._load_config()
        self.progress = self._load_progress()

        # Make sure the remembered act still exists; otherwise fall back.
        if self.config.get("current_act") not in self.acts_by_id:
            self.config["current_act"] = self.acts[0]["id"] if self.acts else None

    # ----- loading -------------------------------------------------------
    def _load_acts(self):
        acts = []
        if ACTS_DIR.exists():
            for path in sorted(ACTS_DIR.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:  # noqa: BLE001 - report and skip bad files
                    print(f"[acts] Failed to load {path.name}: {exc}", file=sys.stderr)
                    continue
                data.setdefault("id", path.stem)
                data.setdefault("name", path.stem)
                data.setdefault("items", [])
                for i, item in enumerate(data["items"]):
                    item.setdefault("id", f'{data["id"]}-{i}')
                    item.setdefault("text", "")
                acts.append(data)
        acts.sort(key=lambda a: (a.get("order", 999), a.get("name", "")))
        return acts

    def _load_config(self):
        cfg = dict(DEFAULT_CONFIG)
        if CONFIG_PATH.exists():
            try:
                cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
            except Exception as exc:  # noqa: BLE001
                print(f"[config] Failed to load: {exc}", file=sys.stderr)
        return cfg

    def _load_progress(self):
        if PROGRESS_PATH.exists():
            try:
                return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                print(f"[progress] Failed to load: {exc}", file=sys.stderr)
        return {}

    # ----- saving --------------------------------------------------------
    def save_config(self):
        try:
            CONFIG_PATH.write_text(
                json.dumps(self.config, indent=2), encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[config] Failed to save: {exc}", file=sys.stderr)

    def save_progress(self):
        try:
            PROGRESS_PATH.write_text(
                json.dumps(self.progress, indent=2), encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[progress] Failed to save: {exc}", file=sys.stderr)

    # ----- progress helpers ---------------------------------------------
    def is_done(self, act_id, item_id):
        return bool(self.progress.get(act_id, {}).get(item_id, False))

    def set_done(self, act_id, item_id, done):
        self.progress.setdefault(act_id, {})[item_id] = bool(done)
        self.save_progress()

    def reset_act_progress(self, act_id):
        self.progress[act_id] = {}
        self.save_progress()

    def reset_all_progress(self):
        """Clear every checkmark across all acts."""
        self.progress = {}
        self.save_progress()

    def act_completion(self, act_id):
        """Return (done, total) for the given act."""
        act = self.acts_by_id.get(act_id)
        if not act:
            return 0, 0
        total = len(act["items"])
        done = sum(1 for it in act["items"] if self.is_done(act_id, it["id"]))
        return done, total

    @property
    def current_act(self):
        return self.acts_by_id.get(self.config.get("current_act"))

    def go_to_next_act(self):
        """Advance the current act to the next one in order.

        Returns True if the act changed, False if already on the last act.
        """
        if not self.acts:
            return False
        ids = [a["id"] for a in self.acts]
        try:
            idx = ids.index(self.config.get("current_act"))
        except ValueError:
            idx = -1
        if idx + 1 >= len(ids):
            return False
        self.config["current_act"] = ids[idx + 1]
        self.save_config()
        return True
