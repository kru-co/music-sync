"""
Apple Music client using macOS osascript (AppleScript).
Reads and writes directly to the Music app — no API keys required.
"""

import subprocess
import json


def _run_script(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


def _run_script_file(path: str) -> str:
    result = subprocess.run(
        ["osascript", path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr.strip()}")
    return result.stdout.strip()


class AppleMusicClient:

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def get_liked_songs(self):
        """Return tracks where loved is true."""
        script = """
tell application "Music"
    set output to ""
    set lovedTracks to (every track of library playlist 1 whose loved is true)
    repeat with t in lovedTracks
        set tName to name of t
        set tArtist to artist of t
        set tAlbum to album of t
        set output to output & tName & "|||" & tArtist & "|||" & tAlbum & "\\n"
    end repeat
    return output
end tell
"""
        raw = _run_script(script)
        tracks = []
        for line in raw.splitlines():
            parts = line.split("|||")
            if len(parts) == 3:
                tracks.append({
                    "name": parts[0],
                    "artist": parts[1],
                    "album": parts[2],
                })
        return tracks

    def get_playlists(self):
        """Return user-created playlists with their tracks."""
        # Get playlist names first
        script = """
tell application "Music"
    set output to ""
    repeat with p in (every user playlist whose special kind is none)
        set output to output & name of p & "\\n"
    end repeat
    return output
end tell
"""
        raw = _run_script(script)
        playlist_names = [l for l in raw.splitlines() if l.strip()]

        playlists = []
        for pl_name in playlist_names:
            safe_name = pl_name.replace('"', '\\"')
            track_script = f"""
tell application "Music"
    set output to ""
    set pl to user playlist "{safe_name}"
    repeat with t in (every track of pl)
        set tName to name of t
        set tArtist to artist of t
        set tAlbum to album of t
        set output to output & tName & "|||" & tArtist & "|||" & tAlbum & "\\n"
    end repeat
    return output
end tell
"""
            try:
                track_raw = _run_script(track_script)
                tracks = []
                for line in track_raw.splitlines():
                    parts = line.split("|||")
                    if len(parts) == 3:
                        tracks.append({
                            "name": parts[0],
                            "artist": parts[1],
                            "album": parts[2],
                        })
                playlists.append({"name": pl_name, "tracks": tracks})
            except RuntimeError:
                continue

        return playlists

    def get_saved_albums(self):
        """Return albums in the library (deduplicated by name + artist)."""
        script = """
tell application "Music"
    set output to ""
    set seen to {}
    repeat with t in (every track of library playlist 1)
        set albumKey to (album of t) & "|||" & (artist of t)
        if seen does not contain albumKey then
            set end of seen to albumKey
            set output to output & (album of t) & "|||" & (artist of t) & "\\n"
        end if
    end repeat
    return output
end tell
"""
        raw = _run_script(script)
        albums = []
        for line in raw.splitlines():
            parts = line.split("|||")
            if len(parts) == 2:
                albums.append({"name": parts[0], "artist": parts[1]})
        return albums

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def add_liked_songs(self, tracks, progress_cb=None):
        added, failed = 0, []
        total = len(tracks)
        for i, track in enumerate(tracks):
            safe_name = track["name"].replace('"', '\\"')
            safe_artist = track["artist"].replace('"', '\\"')
            script = f"""
tell application "Music"
    set results to (every track of library playlist 1 whose name is "{safe_name}" and artist is "{safe_artist}")
    if length of results > 0 then
        set loved of (item 1 of results) to true
        return "ok"
    else
        return "notfound"
    end if
end tell
"""
            try:
                result = _run_script(script)
                if result == "ok":
                    added += 1
                else:
                    failed.append(track)
            except RuntimeError:
                failed.append(track)

            if progress_cb:
                progress_cb(i + 1, total)

        return added, failed

    def create_playlist(self, name, tracks, progress_cb=None):
        safe_name = name.replace('"', '\\"')
        # Create the playlist
        _run_script(f'tell application "Music" to make new user playlist with properties {{name:"{safe_name}"}}')

        added, failed = 0, []
        total = len(tracks)
        for i, track in enumerate(tracks):
            safe_track = track["name"].replace('"', '\\"')
            safe_artist = track["artist"].replace('"', '\\"')
            script = f"""
tell application "Music"
    set results to (every track of library playlist 1 whose name is "{safe_track}" and artist is "{safe_artist}")
    if length of results > 0 then
        duplicate (item 1 of results) to user playlist "{safe_name}"
        return "ok"
    else
        return "notfound"
    end if
end tell
"""
            try:
                result = _run_script(script)
                if result == "ok":
                    added += 1
                else:
                    failed.append(track)
            except RuntimeError:
                failed.append(track)

            if progress_cb:
                progress_cb(i + 1, total)

        return added, failed

    def save_albums(self, albums, progress_cb=None):
        """Albums in Apple Music library are implicit — just report what exists."""
        # In Music.app, albums are collections of tracks. We can't
        # "save an album" the same way Spotify does, so we report matches.
        added, failed = 0, []
        total = len(albums)

        for i, album in enumerate(albums):
            safe_album = album["name"].replace('"', '\\"')
            safe_artist = album["artist"].replace('"', '\\"')
            script = f"""
tell application "Music"
    set results to (every track of library playlist 1 whose album is "{safe_album}" and artist is "{safe_artist}")
    if length of results > 0 then
        return "found"
    else
        return "notfound"
    end if
end tell
"""
            try:
                result = _run_script(script)
                if result == "found":
                    added += 1
                else:
                    failed.append(album)
            except RuntimeError:
                failed.append(album)

            if progress_cb:
                progress_cb(i + 1, total)

        return added, failed
