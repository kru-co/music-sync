# music-sync

A free, open-source CLI tool to transfer liked songs, playlists, and saved albums between Spotify and Apple Music. Run it manually whenever you want to sync.

No subscription. No third-party service. Your credentials stay on your machine.

---

## What it transfers

- Liked songs / saved songs
- Playlists (your own, not followed ones)
- Saved albums

Both directions: Spotify → Apple Music and Apple Music → Spotify.

---

## How matching works

The tool tries to match tracks using their ISRC code first. ISRC is a universal identifier that most tracks carry, so matches are accurate even when titles differ slightly between platforms. If no ISRC is available, it falls back to a title + artist search. Unmatched tracks are listed at the end so you know exactly what didn't make it across.

---

## Requirements

- Python 3.9 or later
- A Spotify developer account (free)
- An Apple Developer account ($99/year) with a MusicKit key

---

## Installation

```bash
git clone https://github.com/your-username/music-sync.git
cd music-sync
pip install -r requirements.txt
```

---

## Getting your API credentials

### Spotify

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Click **Create app**
3. Set the redirect URI to `http://localhost:8888/callback`
4. Copy your **Client ID** and **Client Secret**

### Apple Music

Apple Music requires a MusicKit key from an Apple Developer account.

**Step 1: Get a MusicKit private key**

1. Sign in to [developer.apple.com](https://developer.apple.com)
2. Go to **Certificates, Identifiers & Profiles → Keys**
3. Click **+** to create a new key
4. Enable **MusicKit** and click **Continue**
5. Download the `.p8` file — you can only download it once, so keep it safe
6. Note the **Key ID** shown after creation

**Step 2: Find your Team ID**

Your Team ID is visible in the top-right corner of the Apple Developer portal, or under **Membership** in your account settings.

**Step 3: Get a user token**

Apple Music user tokens are short-lived tokens that authorize access to your personal library. The easiest way to get one:

1. Open [music.apple.com](https://music.apple.com) in Safari while signed into your Apple ID
2. Open Developer Tools → Console
3. Paste this snippet:

```javascript
MusicKit.getInstance().authorize().then(token => console.log(token))
```

4. Copy the token that appears. It is valid for 6 months.

Alternatively, apps like [MusicKit Token Generator](https://github.com/nickvdyck/musickit-token-generator) can generate one from the command line.

---

## Setup

Run the setup wizard on first use:

```bash
python sync.py --setup
```

This prompts for your credentials and saves them to `~/.music-sync/config.json` with permissions set to owner-read-only (chmod 600).

---

## Usage

```
python sync.py <direction> [options]
```

**Directions**

| Direction | Description |
|---|---|
| `spotify-to-apple` | Transfer from Spotify to Apple Music |
| `apple-to-spotify` | Transfer from Apple Music to Spotify |

**Options**

| Flag | Description |
|---|---|
| `--liked-songs` | Transfer liked/saved songs |
| `--playlists` | Transfer playlists |
| `--albums` | Transfer saved albums |
| `--all` | Transfer everything |
| `--dry-run` | Preview what would be transferred without making changes |
| `--setup` | Re-run the credential setup wizard |

---

## Examples

Transfer everything from Spotify to Apple Music:

```bash
python sync.py spotify-to-apple --all
```

Transfer only playlists from Apple Music to Spotify:

```bash
python sync.py apple-to-spotify --playlists
```

Preview a full transfer without making changes:

```bash
python sync.py spotify-to-apple --all --dry-run
```

Transfer liked songs and albums only:

```bash
python sync.py apple-to-spotify --liked-songs --albums
```

---

## Understanding the output

After each transfer, the tool prints a summary:

```
Transferring liked songs (spotify -> apple)...
  Spotify: found 312 liked songs
  298/312 liked songs transferred successfully.

  Could not match 14 liked songs:
    - Some Regional Track by Artist Name
    - Live at Somewhere by Another Artist
    ...

  Tip: These tracks may not be available in the destination catalog,
  or the metadata may differ enough to prevent a match.
```

Unmatched tracks are almost always songs that exist on one platform but not the other due to licensing differences or regional availability. There is no way to automate around this.

---

## Limitations

- **Followed playlists** are not transferred. Only playlists you created are included.
- **Spotify Wrapped** and other auto-generated playlists owned by Spotify are skipped.
- **Apple Music user tokens expire** after 6 months. Re-run `--setup` or generate a new token when yours expires.
- **Rate limits**: Both APIs have rate limits. If you have very large libraries (thousands of songs), the tool may slow down or pause. This is expected behavior.
- **Catalog differences**: Some tracks exist on one platform but not the other. Regional licensing causes most of these gaps.
- **Apple Music catalog country**: The tool defaults to the US catalog (`/catalog/us`). If you are in another country, edit the `_search_track` and `_search_album` methods in `src/apple_music.py` and replace `us` with your country code (e.g., `gb`, `de`, `au`).

---

## Project structure

```
music-sync/
├── sync.py              # CLI entry point
├── requirements.txt
├── .gitignore
├── README.md
└── src/
    ├── config.py        # Credential storage and setup wizard
    ├── spotify.py       # Spotify API client
    ├── apple_music.py   # Apple Music API client
    └── transfer.py      # Transfer logic and reporting
```

---

## Security note

Your credentials are stored in `~/.music-sync/config.json`. The file is created with `chmod 600` so only your user account can read it. Never commit this file to version control. It is listed in `.gitignore` but worth double-checking before you push.

---

## License

MIT
