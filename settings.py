"""User settings, saved in settings.json next to the code.

The menu-bar app and the assistant are separate processes, so they share
settings through this file. The assistant re-reads it for every event,
so a change in the menu takes effect right away, with no restart.
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

DEFAULTS = {
    # Show an Add / Ignore prompt (with an editable title) before adding.
    "ask_before_adding": True,
}


def load_settings(path: str = SETTINGS_FILE) -> dict:
    try:
        with open(path) as f:
            saved = json.load(f)
    except (OSError, ValueError):  # missing or corrupted: use defaults
        saved = {}
    return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS}}


def save_settings(settings: dict, path: str = SETTINGS_FILE) -> None:
    # Write to a temporary file, then swap it in, so the assistant never
    # reads a half-written file.
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp, path)
