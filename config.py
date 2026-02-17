"""
Configuration loading, saving, and interactive setup wizard.
"""

import os
import json

CONFIG_PATH = os.path.expanduser("~/.music-sync/config.json")


def config_exists():
    return os.path.exists(CONFIG_PATH)


def load_config():
    if not config_exists():
        raise FileNotFoundError(
            "No config found. Run with --setup to configure credentials."
        )
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


def setup_wizard():
    print("\n=== music-sync setup ===\n")
    print("You need credentials from both Spotify and Apple Music.")
    print("See README.md for step-by-step instructions on getting these.\n")

    print("--- Spotify ---")
    spotify_client_id = input("Spotify Client ID: ").strip()
    spotify_client_secret = input("Spotify Client Secret: ").strip()
    spotify_redirect_uri = input(
        "Spotify Redirect URI (default: http://localhost:8888/callback): "
    ).strip() or "http://localhost:8888/callback"

    print("\n--- Apple Music ---")
    print("You need a MusicKit private key (.p8 file), Key ID, and Team ID.")
    apple_key_path = input("Path to .p8 private key file: ").strip()
    apple_key_id = input("Key ID: ").strip()
    apple_team_id = input("Team ID: ").strip()

    config = {
        "spotify": {
            "client_id": spotify_client_id,
            "client_secret": spotify_client_secret,
            "redirect_uri": spotify_redirect_uri,
        },
        "apple_music": {
            "key_path": apple_key_path,
            "key_id": apple_key_id,
            "team_id": apple_team_id,
        },
    }

    save_config(config)
    print(f"\nConfig saved to {CONFIG_PATH}")
    print("Run sync.py again with your transfer options to get started.\n")
