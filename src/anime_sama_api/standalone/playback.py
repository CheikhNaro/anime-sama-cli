# -*- coding: utf-8 -*-
"""Lecture : résolution du flux, lancement du lecteur (mpv/vlc)."""

from __future__ import annotations

import subprocess

from . import constants


def resolve_stream_url(embed_url: str) -> str | None:
    """Résout l'URL d'une page embed en URL de flux directe via yt-dlp."""
    try:
        out = subprocess.run(
            ["yt-dlp", "-g", "--no-warnings", "--no-check-certificate", embed_url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode == 0 and out.stdout and out.stdout.strip():
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def play_episode_url(url: str, player: str) -> subprocess.Popen | None:
    """Lance le lecteur sur l'URL (résout l'embed avec yt-dlp si nécessaire)."""
    play_url = resolve_stream_url(url)
    if not play_url:
        play_url = url
    ua = "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0"
    if "sibnet" in play_url or "sibnet" in url:
        referer = "https://video.sibnet.ru/"
    elif "vidmoly" in play_url or "vidmoly" in url:
        referer = "https://vidmoly.net/"
    else:
        referer = "https://anime-sama.to/"
    if player.upper() == "MPV":
        cmd = ["mpv", play_url, "--fullscreen", f"--referrer={referer}", f"--user-agent={ua}"]
        if play_url == url and ("vidmoly" in url or "sibnet" in url or "embed" in url.lower()):
            cmd.insert(-1, "--ytdl-format=best")
    else:
        # --no-one-instance : une nouvelle instance VLC à chaque épisode (pas d'ajout à une fenêtre existante).
        # --no-qt-system-tray : à la fermeture de la fenêtre, VLC quitte complètement (pas de minimisation en tray).
        # Ainsi : fermer VLC → processus terminé → le script affiche le menu → choix d'un autre épisode → VLC se rouvre.
        cmd = [
            "vlc", play_url, "--fullscreen", "--no-one-instance", "--no-qt-system-tray",
            f"--http-referrer={referer}",
            f"--http-user-agent={ua}",
        ]
    try:
        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return None


def play_episode_api(episode, prefer_languages: list[str], player: str):
    """Joue un épisode via l'API (Episode) ou via URL."""
    try:
        from anime_sama_api.episode import Episode
        if not isinstance(episode, Episode):
            return None
        lang_list = [l for l in prefer_languages if l in ("VF", "VOSTFR", "VJSTFR", "VASTFR", "VCN", "VKR", "VQC")]
        if not lang_list:
            lang_list = ["VOSTFR", "VF"]
        best = episode.best(lang_list)
        if not best:
            best = episode.best(["VOSTFR", "VF"])
        if not best:
            # Dernier recours : première URL disponible (toutes langues)
            try:
                best = next(episode.consume_player(["VOSTFR", "VF", "VJSTFR"]), None)
            except StopIteration:
                best = None
        if not best:
            return None
        return play_episode_url(best, player)
    except Exception:
        return None
