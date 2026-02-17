"""
Spotify client using spotipy with automatic browser-based OAuth.
Credentials cached locally after first auth — no re-login needed.
"""

import os
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

CACHE_PATH = os.path.expanduser("~/.music-sync/.spotify_cache")


class SpotifyClient:
    def __init__(self, client_id, client_secret, redirect_uri="http://localhost:8888/callback"):
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=" ".join(SCOPES),
                cache_path=CACHE_PATH,
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
        tracks = []
        results = self.sp.current_user_saved_tracks(limit=50)
        while results:
            for item in results["items"]:
                t = item["track"]
                if t:
                    tracks.append(self._normalize(t))
            results = self.sp.next(results) if results["next"] else None
        return tracks

    def get_playlists(self):
        playlists = []
        results = self.sp.current_user_playlists(limit=50)
        while results:
            for pl in results["items"]:
                if pl["owner"]["id"] != self.user_id:
                    continue
                tracks = self._get_playlist_tracks(pl["id"])
                playlists.append({
                    "name": pl["name"],
                    "description": pl.get("description", ""),
                    "tracks": tracks,
                })
            results = self.sp.next(results) if results["next"] else None
        return playlists

    def get_saved_albums(self):
        albums = []
        results = self.sp.current_user_saved_albums(limit=50)
        while results:
            for item in results["items"]:
                a = item["album"]
                albums.append({
                    "name": a["name"],
                    "artist": a["artists"][0]["name"],
                    "upc": a.get("external_ids", {}).get("upc"),
                })
            results = self.sp.next(results) if results["next"] else None
        return albums

    def _get_playlist_tracks(self, playlist_id):
        tracks = []
        results = self.sp.playlist_tracks(playlist_id, limit=100)
        while results:
            for item in results["items"]:
                t = item.get("track")
                if t and t.get("id"):
                    tracks.append(self._normalize(t))
            results = self.sp.next(results) if results["next"] else None
        return tracks

    def _normalize(self, track):
        return {
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"],
            "isrc": track.get("external_ids", {}).get("isrc"),
        }

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def add_liked_songs(self, tracks, progress_cb=None):
        added, failed = 0, []
        total = len(tracks)
        for i, track in enumerate(tracks):
            tid = self._find_track(track)
            if tid:
                self.sp.current_user_saved_tracks_add([tid])
                added += 1
            else:
                failed.append(track)
            if progress_cb:
                progress_cb(i + 1, total)
        return added, failed

    def create_playlist(self, name, description, tracks, progress_cb=None):
        pl = self.sp.user_playlist_create(
            self.user_id, name, public=False, description=description or ""
        )
        track_ids, failed = [], []
        total = len(tracks)
        for i, track in enumerate(tracks):
            tid = self._find_track(track)
            if tid:
                track_ids.append(tid)
            else:
                failed.append(track)
            if progress_cb:
                progress_cb(i + 1, total)

        for i in range(0, len(track_ids), 100):
            self.sp.playlist_add_items(pl["id"], track_ids[i:i + 100])

        return len(track_ids), failed

    def save_albums(self, albums, progress_cb=None):
        added, failed = 0, []
        total = len(albums)
        for i, album in enumerate(albums):
            aid = self._find_album(album)
            if aid:
                self.sp.current_user_saved_albums_add([aid])
                added += 1
            else:
                failed.append(album)
            if progress_cb:
                progress_cb(i + 1, total)
        return added, failed

    def _find_track(self, track):
        if track.get("isrc"):
            r = self.sp.search(q=f"isrc:{track['isrc']}", type="track", limit=1)
            items = r["tracks"]["items"]
            if items:
                return items[0]["id"]
        r = self.sp.search(
            q=f"track:{track['name']} artist:{track['artist']}",
            type="track", limit=1
        )
        items = r["tracks"]["items"]
        return items[0]["id"] if items else None

    def _find_album(self, album):
        r = self.sp.search(
            q=f"album:{album['name']} artist:{album['artist']}",
            type="album", limit=1
        )
        items = r["albums"]["items"]
        return items[0]["id"] if items else None
