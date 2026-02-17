#!/usr/bin/env python3
"""
music-sync: Transfer liked songs, playlists, and saved albums
between Spotify and Apple Music.
"""

import argparse
import sys
from src.spotify import SpotifyClient
from src.apple_music import AppleMusicClient
from src.transfer import TransferEngine
from src.config import load_config, config_exists, setup_wizard


def main():
    parser = argparse.ArgumentParser(
        prog="music-sync",
        description="Transfer music between Spotify and Apple Music.",
    )
    parser.add_argument(
        "direction",
        choices=["spotify-to-apple", "apple-to-spotify"],
        help="Transfer direction",
    )
    parser.add_argument(
        "--liked-songs",
        action="store_true",
        help="Transfer liked/saved songs",
    )
    parser.add_argument(
        "--playlists",
        action="store_true",
        help="Transfer playlists",
    )
    parser.add_argument(
        "--albums",
        action="store_true",
        help="Transfer saved albums",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Transfer everything (liked songs, playlists, albums)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run the setup wizard to configure API credentials",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be transferred without making changes",
    )

    args = parser.parse_args()

    if args.setup or not config_exists():
        setup_wizard()
        if args.setup:
            return

    config = load_config()

    if args.all:
        args.liked_songs = True
        args.playlists = True
        args.albums = True

    if not any([args.liked_songs, args.playlists, args.albums]):
        print("Specify at least one of: --liked-songs, --playlists, --albums, --all")
        parser.print_help()
        sys.exit(1)

    print(f"\nInitializing {args.direction} transfer...\n")

    spotify = SpotifyClient(config["spotify"])
    apple = AppleMusicClient(config["apple_music"])

    engine = TransferEngine(spotify, apple, dry_run=args.dry_run)

    if args.direction == "spotify-to-apple":
        source, destination = "spotify", "apple"
    else:
        source, destination = "apple", "spotify"

    if args.liked_songs:
        engine.transfer_liked_songs(source, destination)

    if args.playlists:
        engine.transfer_playlists(source, destination)

    if args.albums:
        engine.transfer_albums(source, destination)

    print("\nDone.")


if __name__ == "__main__":
    main()
