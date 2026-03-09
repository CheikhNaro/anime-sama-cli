# -*- coding: utf-8 -*-
"""Constantes partagées par le CLI standalone."""

from __future__ import annotations

import os
from pathlib import Path

# Couleurs ANSI
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"
BOLD = "\033[1m"

SITE_URL = "https://anime-sama.to/"
CONFIG_DIR = Path(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
) / "anime-sama-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
ANILIST_AUTH_FILE = CONFIG_DIR / "anilist_auth.json"
ANILIST_HISTORY_FILE = CONFIG_DIR / "anilist_history.json"
ANILIST_GRAPHQL_URL = "https://graphql.anilist.co"
ANILIST_OAUTH_URL = "https://anilist.co/api/v2/oauth/authorize?client_id=20148&response_type=token"
ANIME_SAMA_API_CONFIG_DIR = Path(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
) / "anime-sama_api"
ANIME_SAMA_API_CONFIG_FILE = ANIME_SAMA_API_CONFIG_DIR / "config.toml"
DOWNLOADS_DIR_NAME = "Téléchargements"
__version__ = "2.0.0"

FZF_MIN_VERSION = (0, 53, 0)
COVER_CACHE_DIR = Path(
    os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
) / "anime-sama-cli" / "covers"
# Hauteur max des covers (redimensionnement ImageMagick/fzf), en pixels.
# Un renforcement de netteté (UnsharpMask / -unsharp) est appliqué après redimensionnement.
# Pour un upscale IA optionnel (hors app) : Real-ESRGAN, waifu2x, ou Upscayl.
COVER_MAX_HEIGHT = 200

# Chemin du script principal (pour la preview fzf), défini au lancement
PREVIEW_SCRIPT_PATH: str | None = None
