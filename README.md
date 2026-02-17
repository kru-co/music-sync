# music-sync

A free Mac desktop app to transfer liked songs, playlists, and saved albums between Spotify and Apple Music. Click a direction, pick what to transfer, hit Sync.

No subscription. No third-party service. Apple Music is accessed directly through the Music app via AppleScript — no Apple Developer account or API keys needed.

![music-sync screenshot](docs/screenshot.png)

---

## Requirements

- macOS 12 or later
- Python 3.9 or later
- Spotify and Apple Music apps installed and signed in
- A free Spotify developer app (takes 2 minutes to create)

---

## Installation

```bash
git clone https://github.com/your-username/music-sync.git
cd music-sync
pip install -r requirements.txt
python app.py
```

---

## Getting your Spotify credentials

You only need to do this once.

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and log in
2. Click **Create app**
3. Give it any name (e.g. "music-sync")
4. Set the redirect URI to exactly: `http://localhost:8888/callback`
5. Copy your **Client ID** and **Client Secret**

When you first launch music-sync, it will ask for these two values. After that, it opens a browser window to authorize your Spotify account. Once done, your token is cached and you won't be asked again unless it expires.

---

## Apple Music

No setup needed. music-sync talks to the Music app directly using AppleScript. Make sure the Music app is open and you are signed into your Apple ID.

The first time you run a transfer, macOS may ask you to grant permission for the terminal (or Python) to control the Music app. Click **OK**.

---

## How to use it

1. Run `python app.py`
2. Select what to transfer: Liked Songs, Playlists, Albums (or all three)
3. Click the **→** arrow to flip direction between Spotify → Apple Music and Apple Music → Spotify
4. Click **Sync**

Progress and any unmatched tracks appear in the log panel at the bottom.

---

## How matching works

Tracks are matched by title and artist name against the Music app library (Apple Music → Spotify direction) or by searching the Spotify catalog (Spotify → Apple Music direction). When a Spotify ISRC code is available, it is used for a more precise match.

Tracks that cannot be matched — usually due to regional catalog differences — are listed in the log so you know exactly what didn't transfer.

---

## Limitations

- **Playlists**: Only playlists you created are transferred. Followed/subscribed playlists are skipped.
- **Apple Music → Spotify (albums)**: The Music app does not expose a separate "saved albums" concept the way Spotify does. Albums are inferred from your library tracks.
- **Apple Music → Spotify (liked songs)**: Only tracks marked as **Loved** in the Music app are treated as liked songs.
- **Catalog gaps**: Some tracks exist on one platform but not the other due to licensing. These are reported but cannot be resolved automatically.
- **Spotify token**: Spotify OAuth tokens are cached in `~/.music-sync/.spotify_cache`. Delete this file to force re-authentication.

---

## Project structure

```
music-sync/
├── app.py               # GUI entry point
├── requirements.txt
├── .gitignore
├── README.md
└── src/
    ├── config.py        # Spotify credential storage
    ├── spotify.py       # Spotify API client
    └── apple_music.py   # Apple Music client via AppleScript
```

---

## Security

Your Spotify Client ID and Secret are stored in `~/.music-sync/config.json` with permissions set to `600` (owner-read only). This file is outside the repo and will not be committed. The Spotify OAuth token cache is stored in the same directory.

---

## License

MIT
