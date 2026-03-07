# -*- coding: utf-8 -*-
"""Menus interactifs : principal, recherche, après lecture, historique, planning, alerte scan."""

from __future__ import annotations

from typing import Literal

from . import constants
from . import terminal
from . import fzf_utils
from . import history


def menu_main() -> Literal["regarder", "télécharger", "planning", "historique", "quitter"] | None:
    options = [
        ("Regarder un animé", "regarder"),
        ("Télécharger un animé", "télécharger"),
        ("Planning des sorties", "planning"),
        ("Voir l'historique", "historique"),
        ("Quitter", "quitter"),
    ]
    index = 0
    shortcut_map = {"regarder": "R", "télécharger": "T", "planning": "P", "historique": "H", "quitter": "q"}
    while True:
        terminal.clear_screen()
        terminal.print_ascii_art()
        print(constants.BOLD + constants.CYAN + "  Choisir une action ⤵" + constants.RESET)
        print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
        print()
        for i, (label, _) in enumerate(options):
            prefix = "  " + constants.GREEN + "▶ " + constants.RESET if i == index else "    "
            shortcut = shortcut_map[options[i][1]]
            print(prefix + constants.GREEN + f"({shortcut})" + constants.RESET + f" {label}")
        print()
        ch = terminal.read_key()
        if ch == "up":
            index = (index - 1) % len(options)
        elif ch == "down":
            index = (index + 1) % len(options)
        elif ch == "enter":
            return options[index][1]
        elif ch == "r":
            return "regarder"
        elif ch == "t":
            return "télécharger"
        elif ch == "p":
            return "planning"
        elif ch == "h":
            return "historique"
        elif ch == "q":
            return "quitter"


def menu_search() -> Literal["recherche", "catalogue", "menu", "quitter"] | None:
    options = [
        ("Rechercher directement le nom de l'animé", "recherche"),
        ("Recherche dynamique dans le catalogue", "catalogue"),
        ("Revenir au menu principal", "menu"),
        ("Quitter", "quitter"),
    ]
    index = 0
    while True:
        terminal.clear_screen()
        terminal.print_ascii_art()
        print(constants.BOLD + constants.CYAN + "  🔍 Recherche" + constants.RESET)
        print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
        print()
        for i, (label, _) in enumerate(options):
            prefix = "  " + constants.GREEN + "▶ " + constants.RESET if i == index else "    "
            shortcut = {"recherche": "S", "catalogue": "C", "menu": "m", "quitter": "q"}[options[i][1]]
            print(prefix + constants.GREEN + f"({shortcut})" + constants.RESET + f" {label}")
        print()
        ch = terminal.read_key()
        if ch == "up":
            index = (index - 1) % len(options)
        elif ch == "down":
            index = (index + 1) % len(options)
        elif ch == "enter":
            return options[index][1]
        elif ch == "s":
            return "recherche"
        elif ch == "c":
            return "catalogue"
        elif ch == "m":
            return "menu"
        elif ch == "q":
            return "quitter"


def menu_after_play(
    episode_number: int,
    has_next: bool,
    has_prev: bool,
    is_last_ep_of_season: bool,
    has_next_season: bool,
    anime_name: str = "",
) -> Literal["suivant", "replay", "précédent", "saison_suivante", "menu", "quitter"] | None:
    options: list[tuple[str, str]] = []
    if has_next:
        options.append(("Épisode suivant", "suivant"))
    options.append(("Rejouer l'épisode actuel", "replay"))
    if has_prev:
        options.append(("Épisode précédent", "précédent"))
    elif is_last_ep_of_season and has_next_season:
        options.append(("Saison suivante", "saison_suivante"))
    options.append(("Revenir au menu principal", "menu"))
    options.append(("Quitter", "quitter"))
    index = 0
    shortcuts = {"suivant": "n", "replay": "r", "précédent": "p", "saison_suivante": "s", "menu": "m", "quitter": "q"}
    while True:
        terminal.clear_screen()
        terminal.print_ascii_art()
        if anime_name.strip():
            msg = f"Vous venez de regarder l'épisode {episode_number} de {anime_name.strip()}."
        else:
            msg = f"Vous venez de regarder l'épisode {episode_number}."
        print(constants.CYAN + msg + constants.RESET)
        print(constants.CYAN + "Que faire maintenant ?" + constants.RESET)
        print()
        for i, (label, action) in enumerate(options):
            prefix = "  " + constants.GREEN + "▶ " + constants.RESET if i == index else "    "
            short = shortcuts.get(action, "")
            print(prefix + constants.GREEN + f"({short})" + constants.RESET + f" {label}")
        print()
        ch = terminal.read_key()
        if ch == "up":
            index = (index - 1) % len(options)
        elif ch == "down":
            index = (index + 1) % len(options)
        elif ch == "enter":
            return options[index][1]
        elif ch == "n" and has_next:
            return "suivant"
        elif ch == "r":
            return "replay"
        elif ch == "p" and has_prev:
            return "précédent"
        elif ch == "s" and is_last_ep_of_season and has_next_season:
            return "saison_suivante"
        elif ch == "m":
            return "menu"
        elif ch == "q":
            return "quitter"


def show_history() -> None:
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.BOLD + constants.CYAN + "  📜 Historique des animés regardés" + constants.RESET)
    print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
    print()
    entries = history.load_history()
    if not entries:
        print(constants.YELLOW + "  Aucun animé dans l'historique." + constants.RESET)
    else:
        for e in entries[:50]:
            anime = (e.get("anime") or "").strip()
            s = e.get("season", 1)
            ep = e.get("episode", 1)
            print(f"  • {anime} — S{s}, Ep{ep}")
    print()
    print("  Appuyez sur une touche pour revenir au menu...")
    terminal.read_key()


def slug_from_planning_url(url: str) -> str:
    from urllib.parse import urlparse
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if "catalogue" in parts:
        i = parts.index("catalogue")
        if i + 1 < len(parts):
            return parts[i + 1]
    return ""


def menu_planning_episode_not_available(has_prev: bool) -> Literal["prev", "planning", "menu", "quitter"] | None:
    options = []
    if has_prev:
        options.append(("Regarder l'épisode précédent", "prev"))
    options.append(("Revenir au planning", "planning"))
    options.append(("Revenir au menu principal", "menu"))
    options.append(("Quitter", "quitter"))
    index = 0
    while True:
        terminal.clear_screen()
        terminal.print_ascii_art()
        print(constants.YELLOW + "  Épisode non disponible. Veuillez patienter jusqu'à sa sortie !" + constants.RESET)
        print()
        for i, (label, action) in enumerate(options):
            prefix = "  " + constants.GREEN + "▶ " + constants.RESET if i == index else "    "
            print(prefix + label)
        print()
        ch = terminal.read_key()
        if ch == "up":
            index = (index - 1) % len(options)
        elif ch == "down":
            index = (index + 1) % len(options)
        elif ch == "enter":
            return options[index][1]
        if has_prev and ch == "p":
            return "prev"
        if ch == "q":
            return "quitter"
    return None


def menu_planning_after_play(has_prev: bool) -> Literal["prev", "planning", "menu", "quitter"] | None:
    options = []
    if has_prev:
        options.append(("Regarder l'épisode précédent", "prev"))
    options.append(("Revenir au planning", "planning"))
    options.append(("Revenir au menu principal", "menu"))
    options.append(("Quitter", "quitter"))
    index = 0
    while True:
        terminal.clear_screen()
        terminal.print_ascii_art()
        print(constants.CYAN + "  Que faire maintenant ?" + constants.RESET)
        print()
        for i, (label, action) in enumerate(options):
            prefix = "  " + constants.GREEN + "▶ " + constants.RESET if i == index else "    "
            print(prefix + label)
        print()
        ch = terminal.read_key()
        if ch == "up":
            index = (index - 1) % len(options)
        elif ch == "down":
            index = (index + 1) % len(options)
        elif ch == "enter":
            return options[index][1]
        if has_prev and ch == "p":
            return "prev"
        if ch == "q":
            return "quitter"
    return None


def alert_scan_read_online_and_return() -> Literal["menu", "quit"]:
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.YELLOW + "Aucun épisode disponible — c'est un scan." + constants.RESET)
    print()
    print("Consultez le site anime-sama.to pour lire les scans en ligne.")
    print()
    items = ["Revenir au menu principal", "Quitter"]
    choice = fzf_utils.fzf_select(items, "Que faire ? ")
    if not choice or "Quitter" in choice:
        return "quit"
    return "menu"
