# -*- coding: utf-8 -*-
"""Vérification des dépendances système requises (fzf, ffmpeg, yt-dlp, mpv/vlc)."""

from __future__ import annotations

import subprocess
import sys

from . import constants
from . import fzf_utils


def _command_available(cmd: str | list[str], *args: str) -> bool:
    """Retourne True si la commande est disponible et s'exécute sans erreur."""
    if isinstance(cmd, str):
        cmd = [cmd]
    full = list(cmd) + list(args)
    try:
        result = subprocess.run(
            full,
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def check_system_dependencies() -> list[str]:
    """
    Vérifie la présence des dépendances système requises.
    Retourne la liste des noms de dépendances manquantes (chaînes lisibles).
    """
    missing: list[str] = []

    if not fzf_utils.check_fzf_version():
        missing.append("fzf (>= 0.53)")

    if not _command_available("ffmpeg", "-version"):
        missing.append("ffmpeg")

    if not _command_available("yt-dlp", "--version"):
        missing.append("yt-dlp")

    has_mpv = _command_available("mpv", "--version")
    has_vlc = _command_available("vlc", "--version")
    if not has_mpv and not has_vlc:
        missing.append("MPV ou VLC (au moins un lecteur vidéo)")

    return missing


def notify_if_missing() -> None:
    """
    Vérifie les dépendances système. Si des dépendances manquent,
    affiche un message explicite et quitte le programme avec le code 1.
    """
    missing = check_system_dependencies()
    if not missing:
        return

    sep = "\n  • "
    list_str = sep + sep.join(missing)
    msg = (
        f"{constants.RED}Dépendances système manquantes :{list_str}{constants.RESET}\n\n"
        "Installez-les selon votre distribution Linux, puis relancez la commande.\n"
        "Exemples :\n"
        "  • Debian/Ubuntu : sudo apt install fzf ffmpeg mpv yt-dlp\n"
        "  • Fedora/RHEL   : sudo dnf install fzf ffmpeg mpv yt-dlp\n"
        "  • Arch Linux    : sudo pacman -S fzf ffmpeg mpv yt-dlp\n\n"
        "Voir le README du projet pour plus de détails :\n"
        "  https://github.com/CheikhNaro/anime-sama-cli#installation-des-d%C3%A9pendances-syst%C3%A8me"
    )
    print(msg, file=sys.stderr)
    sys.exit(1)
