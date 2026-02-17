"""
Spotify API client using the spotipy library.
Handles OAuth, liked songs, playlists, and saved albums.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth


SCOPES = [
    "user-library-read",
    "user-library-modify",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
]


class SpotifyClient:
    def __init__(self, config):
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                redirect_uri=config["redirect_uri"],
                scope=" ".join(SCOPES),
                open_browser=True,
            )
        )
        self._user_id = None

    @property
    def user_id(self):
        if not self._user_id:
            self._user_id = self.sp.current_user()["id"]
        return self._user_id

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def get_liked_songs(self):
        """Return a list of track dicts from the user's liked songs."""
        tracks = []
        results = self.sp.current_user_saved_tracks(limit=50)
        while results:
            for item in results["items"]:
                track = item["track"]
                tracks.append(self._normalize_track(track))
            results = self.sp.next(results) if results["next"] else None
        print(f"  Spotify: found {len(tracks)} liked songs")
        return tracks

    def get_playlists(self):
        """Return a list of playlist dicts with their tracks."""
        playlists = []
        results = self.sp.current_user_playlists(limit=50)
        while results:
            for pl in results["items"]:
                # Skip playlists not owned by the user
                if pl["owner"]["id"] != self.user_id:
                    continue
                tracks = self._get_playlist_tracks(pl["id"])
                playlists.append(
                    {
                        "name": pl["name"],
                        "description": pl.get("description", ""),
                        "tracks": tracks,
                    }
                )
            results = self.sp.next(results) if results["next"] else None
        print(f"  Spotify: found {len(playlists)} playlists")
        return playlists

    def get_saved_albums(self):
        """Return a list of album dicts."""
        albums = []
        results = self.sp.current_user_saved_albums(limit=50)
        while results:
            for item in results["items"]:
                album = item["album"]
                albums.append(
                    {
                        "name": album["name"],
                        "artist": album["artists"][0]["name"],
                        "isrc": None,  # Albums don't have ISRC
                        "upc": album.get("external_ids", {}).get("upc"),
                    }
                )
            results = self.sp.next(results) if results["next"] else None
        print(f"  Spotify: found {len(albums)} saved albums")
        return albums

    def _get_playlist_tracks(self, playlist_id):
        tracks = []
        results = self.sp.playlist_tracks(playlist_id, limit=100)
        while results:
            for item in results["items"]:
                if item["track"] and item["track"]["id"]:
                    tracks.append(self._normalize_track(item["track"]))
            results = self.sp.next(results) if results["next"] else None
        return tracks

    def _normalize_track(self, track):
        return {
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"],
            "isrc": track.get("external_ids", {}).get("isrc"),
            "duration_ms": track["duration_ms"],
        }

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def add_liked_songs(self, tracks):
        """Search for and like tracks on Spotify."""
        added, failed = 0, []
        for track in tracks:
            track_id = self._search_track(track)
            if track_id:
                self.sp.current_user_saved_tracks_add([track_id])
                added += 1
            else:
                failed.append(track)
        return added, failed

    def create_playlist(self, name, description, tracks):
        """Create a playlist and populate it with matched tracks."""
        pl = self.sp.user_playlist_create(
            self.user_id, name, public=False, description=description or ""
        )
        track_ids = []
        failed = []
        for track in tracks:
            tid = self._search_track(track)
            if tid:
                track_ids.append(tid)
            else:
                failed.append(track)

        # Spotify add limit is 100 per request
        for i in range(0, len(track_ids), 100):
            self.sp.playlist_add_items(pl["id"], track_ids[i : i + 100])

        return len(track_ids), failed

    def save_albums(self, albums):
        """Search for and save albums on Spotify."""
        added, failed = 0, []
        for album in albums:
            album_id = self._search_album(album)
            if album_id:
                self.sp.current_user_saved_albums_add([album_id])
                added += 1
            else:
                failed.append(album)
        return added, failed

    def _search_track(self, track):
        """Search by ISRC first, fall back to title/artist query."""
        if track.get("isrc"):
            results = self.sp.search(
                q=f"isrc:{track['isrc']}", type="track", limit=1
            )
            items = results["tracks"]["items"]
            if items:
                return items[0]["id"]

        query = f"track:{track['name']} artist:{track['artist']}"
        results = self.sp.search(q=query, type="track", limit=1)
        items = results["tracks"]["items"]
        return items[0]["id"] if items else None

    def _search_album(self, album):
        query = f"album:{album['name']} artist:{album['artist']}"
        results = self.sp.search(q=query, type="album", limit=1)
        items = results["albums"]["items"]
        return items[0]["id"] if items else None
