"""
Transfer engine. Reads from source, writes to destination,
and prints a summary of matched and unmatched items.
"""


class TransferEngine:
    def __init__(self, spotify, apple_music, dry_run=False):
        self.spotify = spotify
        self.apple = apple_music
        self.dry_run = dry_run

        if dry_run:
            print("DRY RUN: no changes will be made.\n")

    def _clients(self, source):
        if source == "spotify":
            return self.spotify, self.apple
        return self.apple, self.spotify

    # ------------------------------------------------------------------ #
    # Liked songs                                                          #
    # ------------------------------------------------------------------ #

    def transfer_liked_songs(self, source, destination):
        print(f"Transferring liked songs ({source} -> {destination})...")
        src, dst = self._clients(source)

        tracks = src.get_liked_songs()
        if not tracks:
            print("  No liked songs found.")
            return

        if self.dry_run:
            print(f"  Would transfer {len(tracks)} liked songs.")
            return

        added, failed = dst.add_liked_songs(tracks)
        self._print_summary("liked songs", len(tracks), added, failed)

    # ------------------------------------------------------------------ #
    # Playlists                                                            #
    # ------------------------------------------------------------------ #

    def transfer_playlists(self, source, destination):
        print(f"Transferring playlists ({source} -> {destination})...")
        src, dst = self._clients(source)

        playlists = src.get_playlists()
        if not playlists:
            print("  No playlists found.")
            return

        total_tracks = sum(len(p["tracks"]) for p in playlists)
        if self.dry_run:
            print(
                f"  Would transfer {len(playlists)} playlists "
                f"({total_tracks} total tracks)."
            )
            return

        all_failed = []
        for pl in playlists:
            print(f"  Creating playlist: {pl['name']} ({len(pl['tracks'])} tracks)")
            added, failed = dst.create_playlist(
                pl["name"], pl["description"], pl["tracks"]
            )
            print(f"    Added {added}/{len(pl['tracks'])} tracks")
            all_failed.extend(failed)

        if all_failed:
            self._print_unmatched("playlist tracks", all_failed)

    # ------------------------------------------------------------------ #
    # Albums                                                               #
    # ------------------------------------------------------------------ #

    def transfer_albums(self, source, destination):
        print(f"Transferring saved albums ({source} -> {destination})...")
        src, dst = self._clients(source)

        albums = src.get_saved_albums()
        if not albums:
            print("  No saved albums found.")
            return

        if self.dry_run:
            print(f"  Would transfer {len(albums)} saved albums.")
            return

        added, failed = dst.save_albums(albums)
        self._print_summary("saved albums", len(albums), added, failed)

    # ------------------------------------------------------------------ #
    # Reporting                                                            #
    # ------------------------------------------------------------------ #

    def _print_summary(self, label, total, added, failed):
        print(f"  {added}/{total} {label} transferred successfully.")
        if failed:
            self._print_unmatched(label, failed)

    def _print_unmatched(self, label, items):
        print(f"\n  Could not match {len(items)} {label}:")
        for item in items:
            name = item.get("name", "Unknown")
            artist = item.get("artist", "")
            if artist:
                print(f"    - {name} by {artist}")
            else:
                print(f"    - {name}")
        print(
            "\n  Tip: These tracks may not be available in the destination "
            "catalog, or the metadata may differ enough to prevent a match."
        )
