# -*- coding: utf-8 -*-
"""Configuration utilisateur (lecteur, langue) et premier lancement."""

from __future__ import annotations

import json

from . import constants
from . import terminal
from . import fzf_utils


def load_config() -> dict[str, str] | None:
    """Charge la config utilisateur (lecteur, langue)."""
    if not constants.CONFIG_FILE.exists():
        return None
    try:
        with open(constants.CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_config(player: str, language: str) -> None:
    """Sauvegarde la config et synchronise avec anime-sama_api."""
    constants.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {"player": player, "language": language}
    with open(constants.CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    constants.ANIME_SAMA_API_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lang_list = [language]
    player_cmd = "mpv" if player.upper() == "MPV" else "vlc"
    toml_content = f'''# Généré par anime-sama-cli - ne pas modifier à la main
prefer_languages = {json.dumps(lang_list)}
download_path = "{terminal.get_downloads_path()}"
episode_path = "{{serie}}/{{season}}/{{episode}}"
download = true
show_players = false
max_retry_time = 1024
format = "best"
format_sort = ""
internal_player_command = "{player_cmd}"
url = "{constants.SITE_URL}"
provider_url = "https://anime-sama.pw/"

[concurrent_downloads]
fragment = 3
video = 5

[players_hostname]
prefers = []
bans = []
'''
    with open(constants.ANIME_SAMA_API_CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(toml_content)


def first_run_wizard() -> None:
    """Premier lancement : demande lecteur et langue."""
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.BOLD + constants.CYAN + "  🎬 ANIME-SAMA CLI" + constants.RESET + " v" + constants.__version__)
    print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
    print(constants.YELLOW + "  Premier lancement : définissez vos préférences." + constants.RESET)
    print()
    items_player = ["MPV", "VLC"]
    choice_player = fzf_utils.fzf_select(items_player, "Lecteur préféré : ")
    if not choice_player:
        terminal.die("Aucune sélection.")
    player = choice_player.strip()
    items_lang = ["VF", "VOSTFR"]
    choice_lang = fzf_utils.fzf_select(items_lang, "Langue préférée : ")
    if not choice_lang:
        terminal.die("Aucune sélection.")
    language = choice_lang.strip()
    save_config(player, language)
    print(constants.GREEN + "  ✓ Préférences enregistrées." + constants.RESET)
