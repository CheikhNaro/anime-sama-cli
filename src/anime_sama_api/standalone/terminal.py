# -*- coding: utf-8 -*-
"""Affichage terminal : clear_screen, ASCII art, buffer, lecture de touches."""

from __future__ import annotations

import sys
from pathlib import Path

from .constants import CYAN, RESET


def clear_screen() -> None:
    """Efface le terminal avant d'afficher un menu."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def print_ascii_art() -> None:
    """Affiche le bandeau ASCII art au-dessus des menus (avec marge à gauche)."""
    try:
        from importlib.resources import files
        content = (files("anime_sama_api") / "assets" / "ascii_art").read_text(encoding="utf-8")
        margin = "  "
        # splitlines() sans strip() pour préserver l'indentation de la première ligne
        for line in content.splitlines():
            print(CYAN + margin + line + RESET)
        print()
    except Exception:
        pass


def switch_to_alternate_buffer() -> None:
    """Passe en buffer alterné."""
    sys.stdout.write("\033[?1049h")
    sys.stdout.flush()


def switch_from_alternate_buffer() -> None:
    """Revient au buffer normal."""
    sys.stdout.write("\033[?1049l")
    sys.stdout.flush()


def get_downloads_path() -> Path:
    """Dossier Téléchargements de l'utilisateur."""
    from .constants import DOWNLOADS_DIR_NAME
    home = Path.home()
    for name in (DOWNLOADS_DIR_NAME, "Downloads", "Téléchargements"):
        p = home / name
        if p.is_dir():
            return p
    try:
        from platformdirs import user_downloads_dir
        return Path(user_downloads_dir())
    except ImportError:
        return home / "Downloads"


def read_key() -> str:
    """Lit une touche : caractère en minuscule, ou 'up', 'down', 'enter'."""
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                n = sys.stdin.read(1)
                if n == "[" or n == "O":
                    code = sys.stdin.read(1)
                    if code == "A":
                        return "up"
                    if code == "B":
                        return "down"
                    if code == "C":
                        return "right"
                    if code == "D":
                        return "left"
            if ch in ("\r", "\n"):
                return "enter"
            if ch in ("\x7f", "\x08"):
                return "backspace"
            return ch.lower() if ch else ""
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except (ImportError, OSError):
        try:
            line = input("Votre choix : ").strip().lower()
            return line[0] if line else ""
        except (EOFError, IndexError):
            return ""


def die(msg: str, code: int = 1) -> None:
    """Affiche un message d'erreur et quitte."""
    from .constants import RED
    print(RED + "✗ " + msg + RESET, file=sys.stderr)
    sys.exit(code)
