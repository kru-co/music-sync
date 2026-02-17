#!/usr/bin/env python3
"""
music-sync: Transfer music between Spotify and Apple Music.
Mac GUI — no API keys required for Apple Music.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import os
import sys

from src.config import load_config, save_config, config_exists
from src.spotify import SpotifyClient
from src.apple_music import AppleMusicClient

# ------------------------------------------------------------------ #
# Colors & fonts                                                       #
# ------------------------------------------------------------------ #
BG = "#111111"
SURFACE = "#1a1a1a"
BORDER = "#2a2a2a"
TEXT = "#f0f0f0"
SUBTEXT = "#888888"
SPOTIFY_GREEN = "#1DB954"
APPLE_RED = "#fc3c44"
WHITE = "#ffffff"
PROGRESS_BG = "#222222"


def hex_blend(c1, c2, t):
    """Blend two hex colors by factor t (0=c1, 1=c2)."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ------------------------------------------------------------------ #
# Setup dialog                                                         #
# ------------------------------------------------------------------ #

class SetupDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Spotify Setup")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.result = None

        self.grab_set()
        self._build()
        self.wait_window()

    def _build(self):
        pad = {"padx": 24, "pady": 8}

        tk.Label(self, text="Connect Spotify", font=("SF Pro Display", 18, "bold"),
                 bg=BG, fg=TEXT).pack(pady=(28, 4))
        tk.Label(self,
                 text="Enter your Spotify app credentials.\nSee README for how to get these.",
                 font=("SF Pro Text", 12), bg=BG, fg=SUBTEXT, justify="center").pack(**pad)

        self._client_id = self._field("Client ID")
        self._client_secret = self._field("Client Secret", show="•")

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=(16, 24))

        tk.Button(btn_frame, text="Cancel", font=("SF Pro Text", 13),
                  bg=SURFACE, fg=SUBTEXT, relief="flat", bd=0,
                  padx=20, pady=10, cursor="hand2",
                  command=self.destroy).pack(side="left", padx=8)

        tk.Button(btn_frame, text="Connect", font=("SF Pro Text", 13, "bold"),
                  bg=SPOTIFY_GREEN, fg=WHITE, relief="flat", bd=0,
                  padx=20, pady=10, cursor="hand2",
                  command=self._submit).pack(side="left", padx=8)

    def _field(self, label, show=None):
        tk.Label(self, text=label, font=("SF Pro Text", 12),
                 bg=BG, fg=SUBTEXT, anchor="w").pack(padx=24, anchor="w")
        var = tk.StringVar()
        entry = tk.Entry(self, textvariable=var, font=("SF Pro Text", 13),
                         bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=SPOTIFY_GREEN,
                         show=show or "")
        entry.pack(padx=24, pady=(2, 8), ipady=8, fill="x")
        return var

    def _submit(self):
        cid = self._client_id.get().strip()
        secret = self._client_secret.get().strip()
        if not cid or not secret:
            messagebox.showerror("Missing fields", "Both fields are required.", parent=self)
            return
        self.result = {"client_id": cid, "client_secret": secret}
        self.destroy()


# ------------------------------------------------------------------ #
# Main app                                                             #
# ------------------------------------------------------------------ #

class MusicSyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("music-sync")
        self.configure(bg=BG)
        self.resizable(False, False)

        # State
        self._direction = tk.StringVar(value="spotify-to-apple")
        self._liked = tk.BooleanVar(value=True)
        self._playlists = tk.BooleanVar(value=True)
        self._albums = tk.BooleanVar(value=True)
        self._running = False
        self._spotify = None
        self._apple = AppleMusicClient()

        self._build()
        self._check_spotify_auth()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #

    def _build(self):
        # Header
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=32, pady=(28, 0))

        tk.Label(header, text="music-sync", font=("SF Pro Display", 22, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")

        self._auth_badge = tk.Label(header, text="● Spotify disconnected",
                                    font=("SF Pro Text", 11), bg=BG, fg=SUBTEXT)
        self._auth_badge.pack(side="right", pady=4)

        # Direction selector
        dir_frame = tk.Frame(self, bg=SURFACE, highlightthickness=1,
                             highlightbackground=BORDER)
        dir_frame.pack(padx=32, pady=20, fill="x")

        self._build_direction(dir_frame)

        # What to transfer
        options_frame = tk.Frame(self, bg=BG)
        options_frame.pack(padx=32, fill="x")

        tk.Label(options_frame, text="TRANSFER", font=("SF Pro Text", 10),
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(0, 8))

        checks = tk.Frame(options_frame, bg=BG)
        checks.pack(fill="x")

        self._liked_btn = self._toggle_btn(checks, "Liked Songs", self._liked)
        self._liked_btn.pack(side="left", padx=(0, 8))

        self._playlists_btn = self._toggle_btn(checks, "Playlists", self._playlists)
        self._playlists_btn.pack(side="left", padx=(0, 8))

        self._albums_btn = self._toggle_btn(checks, "Albums", self._albums)
        self._albums_btn.pack(side="left")

        # Progress area
        prog_frame = tk.Frame(self, bg=BG)
        prog_frame.pack(padx=32, pady=20, fill="x")

        self._status_label = tk.Label(prog_frame, text="Ready",
                                      font=("SF Pro Text", 12), bg=BG, fg=SUBTEXT)
        self._status_label.pack(anchor="w")

        self._prog_bar_bg = tk.Frame(prog_frame, bg=PROGRESS_BG, height=4)
        self._prog_bar_bg.pack(fill="x", pady=(6, 0))
        self._prog_bar = tk.Frame(self._prog_bar_bg, bg=SPOTIFY_GREEN, height=4, width=0)
        self._prog_bar.place(x=0, y=0, relheight=1, relwidth=0)

        self._log_text = tk.Text(self, height=7, font=("SF Mono", 11),
                                 bg=SURFACE, fg=SUBTEXT, relief="flat", bd=0,
                                 padx=12, pady=10, state="disabled",
                                 highlightthickness=0, wrap="word")
        self._log_text.pack(padx=32, fill="x")

        # Sync button
        self._sync_btn = tk.Button(
            self, text="Sync", font=("SF Pro Display", 15, "bold"),
            bg=SPOTIFY_GREEN, fg=WHITE, relief="flat", bd=0,
            padx=0, pady=14, cursor="hand2",
            activebackground="#18a349", activeforeground=WHITE,
            command=self._start_sync,
        )
        self._sync_btn.pack(padx=32, pady=(16, 28), fill="x")

    def _build_direction(self, parent):
        inner = tk.Frame(parent, bg=SURFACE)
        inner.pack(padx=20, pady=16)

        # Spotify pill
        self._spotify_pill = tk.Label(
            inner, text="Spotify", font=("SF Pro Text", 13, "bold"),
            bg=SPOTIFY_GREEN, fg=WHITE, padx=16, pady=6, relief="flat"
        )
        self._spotify_pill.pack(side="left")

        # Arrow button — clicking flips direction
        self._arrow_btn = tk.Button(
            inner, text="→", font=("SF Pro Display", 18),
            bg=SURFACE, fg=TEXT, relief="flat", bd=0,
            padx=12, cursor="hand2",
            activebackground=SURFACE,
            command=self._flip_direction,
        )
        self._arrow_btn.pack(side="left", padx=8)

        # Apple pill
        self._apple_pill = tk.Label(
            inner, text="Apple Music", font=("SF Pro Text", 13, "bold"),
            bg=APPLE_RED, fg=WHITE, padx=16, pady=6, relief="flat"
        )
        self._apple_pill.pack(side="left")

        self._dir_label = tk.Label(
            parent, text="Spotify → Apple Music",
            font=("SF Pro Text", 11), bg=SURFACE, fg=SUBTEXT
        )
        self._dir_label.pack(pady=(0, 12))

    def _toggle_btn(self, parent, label, var):
        btn = tk.Label(
            parent, text=label, font=("SF Pro Text", 12),
            bg=BORDER, fg=SUBTEXT, padx=14, pady=8, cursor="hand2",
            relief="flat"
        )
        btn.bind("<Button-1>", lambda e: self._toggle(var, btn))
        self._update_toggle(var, btn)
        return btn

    def _toggle(self, var, btn):
        var.set(not var.get())
        self._update_toggle(var, btn)

    def _update_toggle(self, var, btn):
        if var.get():
            btn.configure(bg=BORDER, fg=TEXT)
        else:
            btn.configure(bg=SURFACE, fg=SUBTEXT)

    # ------------------------------------------------------------------ #
    # Direction                                                            #
    # ------------------------------------------------------------------ #

    def _flip_direction(self):
        if self._direction.get() == "spotify-to-apple":
            self._direction.set("apple-to-spotify")
            self._arrow_btn.configure(text="←")
            self._dir_label.configure(text="Apple Music → Spotify")
            self._sync_btn.configure(bg=APPLE_RED, activebackground="#e0333b")
            self._prog_bar.configure(bg=APPLE_RED)
        else:
            self._direction.set("spotify-to-apple")
            self._arrow_btn.configure(text="→")
            self._dir_label.configure(text="Spotify → Apple Music")
            self._sync_btn.configure(bg=SPOTIFY_GREEN, activebackground="#18a349")
            self._prog_bar.configure(bg=SPOTIFY_GREEN)

    # ------------------------------------------------------------------ #
    # Spotify auth                                                         #
    # ------------------------------------------------------------------ #

    def _check_spotify_auth(self):
        config = load_config()
        if config:
            self._connect_spotify(config["client_id"], config["client_secret"])
        else:
            self._auth_badge.configure(text="● Spotify disconnected", fg="#cc4444")
            self._prompt_spotify_setup()

    def _prompt_spotify_setup(self):
        dialog = SetupDialog(self)
        if dialog.result:
            creds = dialog.result
            save_config(creds)
            self._connect_spotify(creds["client_id"], creds["client_secret"])

    def _connect_spotify(self, client_id, client_secret):
        try:
            self._spotify = SpotifyClient(client_id, client_secret)
            user = self._spotify.sp.current_user()
            name = user.get("display_name") or user.get("id", "Connected")
            self._auth_badge.configure(
                text=f"● {name}", fg=SPOTIFY_GREEN
            )
            self._log(f"Spotify connected as {name}")
        except Exception as e:
            self._auth_badge.configure(text="● Spotify disconnected", fg="#cc4444")
            self._log(f"Spotify auth failed: {e}")

    # ------------------------------------------------------------------ #
    # Sync                                                                 #
    # ------------------------------------------------------------------ #

    def _start_sync(self):
        if self._running:
            return
        if not self._spotify:
            messagebox.showerror("Not connected", "Connect Spotify first.")
            return
        if not any([self._liked.get(), self._playlists.get(), self._albums.get()]):
            messagebox.showerror("Nothing selected", "Select at least one thing to transfer.")
            return

        self._running = True
        self._sync_btn.configure(state="disabled", text="Syncing…")
        self._set_progress(0)
        threading.Thread(target=self._run_sync, daemon=True).start()

    def _run_sync(self):
        direction = self._direction.get()
        if direction == "spotify-to-apple":
            src, dst_label = "Spotify", "Apple Music"
            read_liked = self._spotify.get_liked_songs
            read_playlists = self._spotify.get_playlists
            read_albums = self._spotify.get_saved_albums
            write_liked = self._apple.add_liked_songs
            write_playlist = lambda name, _, tracks, pcb: self._apple.create_playlist(name, tracks, pcb)
            write_albums = self._apple.save_albums
        else:
            src, dst_label = "Apple Music", "Spotify"
            read_liked = self._apple.get_liked_songs
            read_playlists = self._apple.get_playlists
            read_albums = self._apple.get_saved_albums
            write_liked = self._spotify.add_liked_songs
            write_playlist = self._spotify.create_playlist
            write_albums = self._spotify.save_albums

        try:
            tasks = []
            if self._liked.get():
                tasks.append(("liked songs", read_liked, write_liked, False))
            if self._playlists.get():
                tasks.append(("playlists", read_playlists, write_playlist, True))
            if self._albums.get():
                tasks.append(("albums", read_albums, write_albums, False))

            total_tasks = len(tasks)
            for task_i, (label, reader, writer, is_playlist) in enumerate(tasks):
                self._status(f"Reading {label} from {src}…")
                items = reader()
                self._log(f"Found {len(items)} {label}")

                self._status(f"Writing {label} to {dst_label}…")

                if is_playlist:
                    all_failed = []
                    for pl_i, pl in enumerate(items):
                        self._log(f"  Creating: {pl['name']} ({len(pl['tracks'])} tracks)")
                        tracks = pl["tracks"]

                        def pl_progress(done, total, pi=pl_i, pl_count=len(items)):
                            frac = (task_i / total_tasks) + \
                                   (pi / pl_count / total_tasks) + \
                                   (done / max(total, 1) / pl_count / total_tasks)
                            self._set_progress(frac)

                        added, failed = writer(
                            pl["name"],
                            pl.get("description", ""),
                            tracks,
                            pl_progress,
                        )
                        self._log(f"    {added}/{len(tracks)} tracks added")
                        all_failed.extend(failed)

                    if all_failed:
                        self._log(f"  {len(all_failed)} tracks could not be matched")
                else:
                    def progress(done, total, ti=task_i):
                        frac = (ti / total_tasks) + (done / max(total, 1) / total_tasks)
                        self._set_progress(frac)

                    added, failed = writer(items, progress)
                    self._log(f"  {added}/{len(items)} {label} transferred")
                    if failed:
                        self._log(f"  {len(failed)} could not be matched")

                self._set_progress((task_i + 1) / total_tasks)

            self._set_progress(1.0)
            self._status("Done.")
            self._log("✓ Transfer complete")

        except Exception as e:
            self._log(f"Error: {e}")
            self._status("Transfer failed — see log above")

        finally:
            self._running = False
            self.after(0, lambda: self._sync_btn.configure(state="normal", text="Sync"))

    # ------------------------------------------------------------------ #
    # UI helpers                                                           #
    # ------------------------------------------------------------------ #

    def _status(self, msg):
        self.after(0, lambda: self._status_label.configure(text=msg))

    def _log(self, msg):
        def _append():
            self._log_text.configure(state="normal")
            self._log_text.insert("end", msg + "\n")
            self._log_text.see("end")
            self._log_text.configure(state="disabled")
        self.after(0, _append)

    def _set_progress(self, fraction):
        fraction = max(0.0, min(1.0, fraction))
        self.after(0, lambda: self._prog_bar.place(
            x=0, y=0, relheight=1, relwidth=fraction
        ))


if __name__ == "__main__":
    app = MusicSyncApp()
    app.mainloop()
