# -*- coding: utf-8 -*-
"""Point d'entrée : main(), async_main(), options --help / --set-player / --set-lang."""

from __future__ import annotations

import asyncio
import logging
import sys

from . import constants
from . import terminal
from . import config
from . import fzf_utils
from . import menus
from . import planning
from . import flows


def print_help() -> None:
    print("""
Usage: anime-sama [OPTIONS]

  Lance l'interface pour regarder ou télécharger des animés depuis anime-sama.to.

OPTIONS:
  -h, --help        Affiche cette aide
  --set-player      Changer le lecteur vidéo par défaut (MPV / VLC)
  --set-lang        Changer la langue par défaut (VF / VOSTFR)

COMMANDES:
  anilist login     Se connecter à AniList et importer l'historique (déjà vus / à regarder)
  completions SHELL Génère les complétions shell (bash, zsh, fish). Ex. : source <(anime-sama completions bash)

SANS OPTION:
  anime-sama        Lance le menu principal (Regarder / Télécharger / Quitter)

EXEMPLES:
  anime-sama
  anime-sama --set-player
  anime-sama --set-lang
  anime-sama --help
""")


def handle_set_player() -> None:
    cfg = config.load_config() or {}
    items = ["MPV", "VLC"]
    choice = fzf_utils.fzf_select(items, "Nouveau lecteur par défaut : ")
    if not choice:
        print(constants.YELLOW + "Aucune modification." + constants.RESET)
        return
    player = choice.strip().upper()
    config.save_config(player, cfg.get("language", "VOSTFR"))
    print(constants.GREEN + f"Lecteur par défaut : {player}" + constants.RESET)


def handle_set_lang() -> None:
    cfg = config.load_config() or {}
    items = ["VF", "VOSTFR"]
    choice = fzf_utils.fzf_select(items, "Nouvelle langue par défaut : ")
    if not choice:
        return
    config.save_config(cfg.get("player", "mpv"), choice.strip())
    print(constants.GREEN + f"Langue par défaut : {choice.strip()}" + constants.RESET)


async def async_main() -> None:
    cfg = config.load_config()
    if not cfg:
        config.first_run_wizard()
        cfg = config.load_config()
    if not cfg:
        terminal.die("Configuration manquante.")
    fzf_utils.check_deps(cfg.get("player", "mpv"))
    terminal.switch_to_alternate_buffer()

    while True:
        action = menus.menu_main()
        if action == "quitter" or not action:
            terminal.switch_from_alternate_buffer()
            terminal.clear_screen()
            print(constants.GREEN + "À bientôt !" + constants.RESET)
            return
        if action == "regarder":
            stay = await flows.run_watch_flow(cfg)
            if not stay:
                terminal.switch_from_alternate_buffer()
                terminal.clear_screen()
                print(constants.GREEN + "À bientôt !" + constants.RESET)
                return
        elif action == "historique_anilist":
            menus.show_history_anilist()
        elif action == "historique_local":
            menus.show_history_local()
        elif action == "recherche_historique":
            await menus.show_search_history()
        elif action == "update_anilist":
            from . import anilist
            ok, msg = anilist.push_local_to_anilist()
            menus.show_update_anilist_result(ok, msg)
        elif action == "planning":
            await planning.show_planning()
        elif action == "télécharger":
            stay = await flows.run_download_flow(cfg)
            if not stay:
                terminal.switch_from_alternate_buffer()
                terminal.clear_screen()
                print(constants.GREEN + "À bientôt !" + constants.RESET)
                return


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == "--preview-cover":
        fzf_utils.run_preview_cover(sys.argv[2], " ".join(sys.argv[3:]))
        sys.exit(0)

    if len(sys.argv) >= 3 and sys.argv[1] == "anilist" and sys.argv[2] == "login":
        from . import anilist
        terminal.switch_to_alternate_buffer()
        anilist.login_flow()
        terminal.switch_from_alternate_buffer()
        sys.exit(0)

    if len(sys.argv) >= 3 and sys.argv[1] == "completions":
        from . import completions
        if completions.main(sys.argv[2].lower()):
            sys.exit(0)
        print("Usage: anime-sama completions {bash|zsh|fish}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    args = [a for a in sys.argv[1:] if a in ("-h", "--help", "--set-player", "--set-lang")]
    if "--help" in args or "-h" in args:
        print_help()
        sys.exit(0)
    if "--set-player" in args:
        if not fzf_utils.check_fzf_version():
            terminal.die("fzf >= 0.53.0 est requis. Installez-le : sudo apt install fzf")
        cfg = config.load_config() or {}
        terminal.switch_to_alternate_buffer()
        terminal.clear_screen()
        terminal.print_ascii_art()
        handle_set_player()
        terminal.switch_from_alternate_buffer()
        sys.exit(0)
    if "--set-lang" in args:
        if not fzf_utils.check_fzf_version():
            terminal.die("fzf >= 0.53.0 est requis. Installez-le : sudo apt install fzf")
        terminal.switch_to_alternate_buffer()
        terminal.clear_screen()
        terminal.print_ascii_art()
        handle_set_lang()
        terminal.switch_from_alternate_buffer()
        sys.exit(0)

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        terminal.switch_from_alternate_buffer()
        terminal.clear_screen()
        print(constants.YELLOW + "Interruption." + constants.RESET)
        sys.exit(0)
    except Exception as e:
        terminal.switch_from_alternate_buffer()
        print(constants.RED + f"Erreur : {e}" + constants.RESET, file=sys.stderr)
        sys.exit(1)
    finally:
        terminal.switch_from_alternate_buffer()
