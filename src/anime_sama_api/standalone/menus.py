# -*- coding: utf-8 -*-
"""Menus interactifs : principal, recherche, après lecture, historique, planning, alerte scan."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

from . import constants
from . import terminal
from . import fzf_utils
from . import history


def menu_main() -> Literal["regarder", "télécharger", "planning", "historique_anilist", "historique_local", "recherche_historique", "update_anilist", "quitter"] | None:
    options = [
        ("👀 Regarder un animé", "regarder"),
        ("📥 Télécharger un animé", "télécharger"),
        ("📅 Planning de la semaine", "planning"),
        ("📜 Historique AniList", "historique_anilist"),
        ("📃 Historique local", "historique_local"),
        ("🔍 Rechercher dans l'historique", "recherche_historique"),
        ("🔄 Mise à jour AniList", "update_anilist"),
        ("❌ Quitter", "quitter"),
    ]
    index = 0
    shortcut_map = {
        "regarder": "R", "télécharger": "T", "planning": "P",
        "historique_anilist": "H", "historique_local": "L", "recherche_historique": "S",
        "update_anilist": "U", "quitter": "q",
    }
    while True:
        terminal.clear_screen()
        terminal.print_ascii_art()
        print(constants.BOLD + constants.CYAN + "  Choisissez une action ⤵" + constants.RESET)
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
            return "historique_anilist"
        elif ch == "l":
            return "historique_local"
        elif ch == "s":
            return "recherche_historique"
        elif ch == "u":
            return "update_anilist"
        elif ch == "q":
            return "quitter"


def menu_search(title_override: str | None = None) -> Literal["recherche", "catalogue", "menu", "quitter"] | None:
    options = [
        ("🔍 Rechercher un animé", "recherche"),
        ("📚 Accéder au catalogue", "catalogue"),
        ("🔙 Revenir au menu principal", "menu"),
        ("❌ Quitter", "quitter"),
    ]
    menu_title = title_override if title_override is not None else "🔍 Recherche"
    index = 0
    while True:
        terminal.clear_screen()
        terminal.print_ascii_art()
        print(constants.BOLD + constants.CYAN + "  " + menu_title + constants.RESET)
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
        elif ch == "m" or ch == "backspace":
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
        elif ch == "m" or ch == "backspace":
            return "menu"
        elif ch == "q":
            return "quitter"


def show_history_anilist() -> None:
    """Affiche uniquement l'historique importé depuis AniList."""
    from . import anilist
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.BOLD + constants.CYAN + "📜 Historique AniList" + constants.RESET)
    print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
    print()
    entries = anilist.load_anilist_history()
    if not entries:
        print(constants.YELLOW + "  Aucun animé dans l'historique AniList. Exécutez 'anime-sama anilist import' pour importer votre historique." + constants.RESET)
    else:
        for e in entries[:50]:
            anime = (e.get("anime") or "").strip()
            s = e.get("season", 1)
            ep = e.get("episode", 1)
            print(f"  • {anime} — S{s}, Ep{ep}")
    print()
    print("  Appuyez sur une touche pour revenir au menu...")
    terminal.read_key()


def show_history_local() -> None:
    """Affiche uniquement l'historique local (animés regardés via l'app)."""
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.BOLD + constants.CYAN + "  📃 Historique local" + constants.RESET)
    print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
    print()
    entries = history.load_history()
    if not entries:
        print(constants.YELLOW + "  Aucun animé dans l'historique local." + constants.RESET)
    else:
        for e in entries[:50]:
            anime = (e.get("anime") or "").strip()
            s = e.get("season", 1)
            ep = e.get("episode", 1)
            print(f"  • {anime} — S{s}, Ep{ep}")
    print()
    print("  Appuyez sur une touche pour revenir au menu...")
    terminal.read_key()


async def show_search_history() -> None:
    """Recherche dans l'historique local et AniList via fzf, avec preview comme au catalogue."""
    from . import anilist
    from . import api_helpers
    local_entries = history.load_history()
    anilist_entries = anilist.load_anilist_history()
    items = []
    entries_with_anime = []
    for e in local_entries:
        anime = (e.get("anime") or "").strip()
        if not anime:
            continue
        s, ep = e.get("season", 1), e.get("episode", 1)
        display_str = f"{anime} — S{s}, Ep{ep} (local)"
        items.append(display_str)
        entries_with_anime.append((display_str, anime))
    for e in anilist_entries:
        anime = (e.get("anime") or "").strip()
        if not anime:
            continue
        s, ep = e.get("season", 1), e.get("episode", 1)
        display_str = f"{anime} — S{s}, Ep{ep} (AniList)"
        items.append(display_str)
        entries_with_anime.append((display_str, anime))
    if not items:
        terminal.clear_screen()
        terminal.print_ascii_art()
        print(constants.BOLD + constants.CYAN + "  🔍 Rechercher dans l'historique" + constants.RESET)
        print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
        print()
        print(constants.YELLOW + "  Aucune entrée dans l'historique local ni AniList." + constants.RESET)
        print()
        print("  Appuyez sur une touche pour revenir au menu...")
        terminal.read_key()
        return
    cache = {}
    preview_objects = []
    for display_str, anime_name in entries_with_anime:
        if anime_name not in cache:
            try:
                catalogues = await api_helpers.search_catalogues(anime_name)
                cache[anime_name] = catalogues[0] if catalogues else None
            except Exception:
                cache[anime_name] = None
        c = cache[anime_name]
        if c:
            preview_objects.append(SimpleNamespace(
                name=display_str,
                title=(getattr(c, "name", None) or anime_name).strip(),
                image_url=getattr(c, "image_url", "") or "",
                page_url=(getattr(c, "url", None) or getattr(c, "page_url", "") or "").strip(),
                genre="",
                type="",
            ))
        else:
            preview_objects.append(SimpleNamespace(
                name=display_str,
                title=anime_name,
                image_url="",
                page_url="",
                genre="",
                type="",
            ))
    choice = fzf_utils.fzf_select(
        items,
        "Rechercher dans l'historique (↑↓ = naviguer, Entrée = valider, Backspace = retour) : ",
        catalogues_for_preview=preview_objects,
    )
    if not choice:
        return
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.BOLD + constants.CYAN + "  🔍 Rechercher dans l'historique" + constants.RESET)
    print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
    print()
    print(constants.WHITE + "  " + choice.strip() + constants.RESET)
    print()
    print("  Appuyez sur une touche pour revenir au menu...")
    terminal.read_key()


def show_update_anilist_result(success: bool, message: str) -> None:
    """Affiche le résultat de la mise à jour AniList puis attend une touche."""
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.BOLD + constants.CYAN + "  ♻️ Mettre à jour mon AniList" + constants.RESET)
    print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
    print()
    if success:
        print(constants.GREEN + "  " + message + constants.RESET)
    else:
        print(constants.YELLOW + "  " + message + constants.RESET)
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


def alert_planning_episode_not_yet_released() -> None:
    """Affiche l'alerte « Épisode non disponible » puis attend une touche (retour au planning)."""
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.YELLOW + "  Épisode non disponible, veuillez patienter jusqu'à la sortie" + constants.RESET)
    print()
    print("  Appuyez sur une touche pour revenir au planning...")
    terminal.read_key()


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
        print(constants.YELLOW + "  Épisode non disponible, veuillez patienter jusqu'à la sortie" + constants.RESET)
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
        if ch == "backspace":
            return "planning"
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
        if ch == "backspace":
            return "planning"
        if ch == "q":
            return "quitter"
    return None


def alert_scan_read_online_and_return() -> Literal["menu", "quit"]:
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.YELLOW + "Ceci est un scan à lire sur le site officiel." + constants.RESET)
    print()
    items = ["Revenir au menu principal", "Quitter"]
    choice = fzf_utils.fzf_select(items, "Que faire ? ")
    if not choice or "Quitter" in choice:
        return "quit"
    return "menu"
