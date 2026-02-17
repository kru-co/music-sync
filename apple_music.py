"""
Apple Music API client using the musickit library.
Handles JWT generation, liked songs, playlists, and saved albums.
"""

import time
import json
import jwt
import requests


APPLE_MUSIC_BASE = "https://api.music.apple.com/v1"


class AppleMusicClient:
    def __init__(self, config):
        self.key_path = config["key_path"]
        self.key_id = config["key_id"]
        self.team_id = config["team_id"]
        self._developer_token = None
        self._user_token = None

    # ------------------------------------------------------------------ #
    # Auth                                                                 #
    # ------------------------------------------------------------------ #

    @property
    def developer_token(self):
        if not self._developer_token:
            with open(self.key_path, "r") as f:
                private_key = f.read()
            now = int(time.time())
            payload = {
                "iss": self.team_id,
                "iat": now,
                "exp": now + 15_777_000,  # 6 months
            }
            self._developer_token = jwt.encode(
                payload,
                private_key,
                algorithm="ES256",
                headers={"kid": self.key_id},
            )
        return self._developer_token

    @property
    def user_token(self):
        if not self._user_token:
            self._user_token = self._fetch_user_token()
        return self._user_token

    def _fetch_user_token(self):
        """
        Apple Music user tokens require a native app or web prompt.
        This method guides the user to obtain one manually via a helper page.
        """
        print("\nApple Music requires a user token to access your library.")
        print(
            "Open this URL in Safari on a device signed into your Apple ID:\n"
        )
        print("  https://music.apple.com/")
        print(
            "\nThen paste your MusicKit user token below."
        )
        print(
            "See README.md for instructions on how to get your user token.\n"
        )
        token = input("Apple Music User Token: ").strip()
        return token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.developer_token}",
            "Music-User-Token": self.user_token,
        }

    def _get(self, path, params=None):
        url = f"{APPLE_MUSIC_BASE}{path}"
        response = requests.get(url, headers=self._headers(), params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, path, body):
        url = f"{APPLE_MUSIC_BASE}{path}"
        response = requests.post(
            url, headers=self._headers(), json=body
        )
        response.raise_for_status()
        return response.json() if response.text else {}

    def _delete(self, path, params=None):
        url = f"{APPLE_MUSIC_BASE}{path}"
        response = requests.delete(url, headers=self._headers(), params=params)
        response.raise_for_status()

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def get_liked_songs(self):
        tracks = []
        offset = 0
        limit = 100
        while True:
            data = self._get(
                "/me/library/songs",
                params={"limit": limit, "offset": offset},
            )
            items = data.get("data", [])
            for item in items:
                attrs = item.get("attributes", {})
                tracks.append(
                    {
                        "name": attrs.get("name"),
                        "artist": attrs.get("artistName"),
                        "album": attrs.get("albumName"),
                        "isrc": attrs.get("isrc"),
                        "duration_ms": attrs.get("durationInMillis"),
                    }
                )
            if len(items) < limit:
                break
            offset += limit
        print(f"  Apple Music: found {len(tracks)} liked songs")
        return tracks

    def get_playlists(self):
        playlists = []
        offset = 0
        limit = 100
        while True:
            data = self._get(
                "/me/library/playlists",
                params={"limit": limit, "offset": offset},
            )
            items = data.get("data", [])
            for item in items:
                attrs = item.get("attributes", {})
                # Skip playlists not editable by the user
                if not attrs.get("canEdit", True):
                    continue
                tracks = self._get_playlist_tracks(item["id"])
                playlists.append(
                    {
                        "name": attrs.get("name"),
                        "description": attrs.get("description", {}).get(
                            "standard", ""
                        ),
                        "tracks": tracks,
                    }
                )
            if len(items) < limit:
                break
            offset += limit
        print(f"  Apple Music: found {len(playlists)} playlists")
        return playlists

    def get_saved_albums(self):
        albums = []
        offset = 0
        limit = 100
        while True:
            data = self._get(
                "/me/library/albums",
                params={"limit": limit, "offset": offset},
            )
            items = data.get("data", [])
            for item in items:
                attrs = item.get("attributes", {})
                albums.append(
                    {
                        "name": attrs.get("name"),
                        "artist": attrs.get("artistName"),
                        "upc": attrs.get("upc"),
                    }
                )
            if len(items) < limit:
                break
            offset += limit
        print(f"  Apple Music: found {len(albums)} saved albums")
        return albums

    def _get_playlist_tracks(self, playlist_id):
        tracks = []
        offset = 0
        limit = 100
        while True:
            data = self._get(
                f"/me/library/playlists/{playlist_id}/tracks",
                params={"limit": limit, "offset": offset},
            )
            items = data.get("data", [])
            for item in items:
                attrs = item.get("attributes", {})
                tracks.append(
                    {
                        "name": attrs.get("name"),
                        "artist": attrs.get("artistName"),
                        "album": attrs.get("albumName"),
                        "isrc": attrs.get("isrc"),
                        "duration_ms": attrs.get("durationInMillis"),
                    }
                )
            if len(items) < limit:
                break
            offset += limit
        return tracks

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def add_liked_songs(self, tracks):
        added, failed = 0, []
        for track in tracks:
            catalog_id = self._search_track(track)
            if catalog_id:
                self._post(
                    "/me/library",
                    {"ids[songs]": [catalog_id]},
                )
                added += 1
            else:
                failed.append(track)
        return added, failed

    def create_playlist(self, name, description, tracks):
        # Create empty playlist
        body = {
            "attributes": {
                "name": name,
                "description": description or "",
            }
        }
        data = self._post("/me/library/playlists", body)
        playlist_id = data["data"][0]["id"]

        track_ids = []
        failed = []
        for track in tracks:
            tid = self._search_track(track)
            if tid:
                track_ids.append({"id": tid, "type": "songs"})
            else:
                failed.append(track)

        if track_ids:
            self._post(
                f"/me/library/playlists/{playlist_id}/tracks",
                {"data": track_ids},
            )

        return len(track_ids), failed

    def save_albums(self, albums):
        added, failed = 0, []
        for album in albums:
            catalog_id = self._search_album(album)
            if catalog_id:
                self._post("/me/library", {"ids[albums]": [catalog_id]})
                added += 1
            else:
                failed.append(album)
        return added, failed

    def _search_track(self, track):
        """Search catalog by ISRC first, fall back to term search."""
        if track.get("isrc"):
            data = self._get(
                "/catalog/us/songs",
                params={"filter[isrc]": track["isrc"]},
            )
            items = data.get("data", [])
            if items:
                return items[0]["id"]

        term = f"{track['name']} {track['artist']}"
        data = self._get(
            "/catalog/us/search",
            params={"term": term, "types": "songs", "limit": 1},
        )
        results = data.get("results", {}).get("songs", {}).get("data", [])
        return results[0]["id"] if results else None

    def _search_album(self, album):
        term = f"{album['name']} {album['artist']}"
        data = self._get(
            "/catalog/us/search",
            params={"term": term, "types": "albums", "limit": 1},
        )
        results = data.get("results", {}).get("albums", {}).get("data", [])
        return results[0]["id"] if results else None
