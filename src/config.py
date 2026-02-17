"""
Config management. Only Spotify API credentials are needed.
Apple Music is accessed via osascript — no credentials required.
"""

import os
import json

CONFIG_PATH = os.path.expanduser("~/.music-sync/config.json")


def config_exists():
    return os.path.exists(CONFIG_PATH)


def load_config():
    if not config_exists():
        return None
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)
