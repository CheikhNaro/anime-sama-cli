# -*- coding: utf-8 -*-
"""Affichage du planning des sorties et lecture depuis le planning."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from . import constants
from . import terminal
from . import config
from . import fzf_utils
from . import api_helpers
from . import menus
from . import playback


async def show_planning() -> None:
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.BOLD + constants.CYAN + "  📅 Planning des sorties" + constants.RESET)
    print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
    print()
    print(constants.BLUE + "  Chargement du planning..." + constants.RESET)
    from anime_sama_api import AnimeSama
    from anime_sama_api.top_level import PlanningDay, PlanningEntry
    from anime_sama_api.season import Season

    client = api_helpers.get_client()
    api = AnimeSama(constants.SITE_URL, client=client)
    try:
        days = await api.planning()
    except Exception as e:
        print(constants.RED + f"  Erreur : {e}" + constants.RESET)
        print()
        print("  Appuyez sur une touche pour revenir au menu...")
        terminal.read_key()
        return

    if not days:
        terminal.clear_screen()
        terminal.print_ascii_art()
        print(constants.BOLD + constants.CYAN + "  📅 Planning des sorties" + constants.RESET)
        print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
        print()
        print(constants.YELLOW + "  Aucune donnée de planning disponible." + constants.RESET)
        print()
        print("  Appuyez sur une touche pour revenir au menu...")
        terminal.read_key()
        return

    # Ordre des jours pour affichage en arbre
    day_order = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")
    day_rank = {d: i for i, d in enumerate(day_order)}
    sorted_days = sorted(days, key=lambda d: day_rank.get(d.day_name.strip(), 99))
    today_str = date.today().strftime("%d/%m")

    # Arbre : "Jour (DD/MM)" (couleur si jour courant), puis "   • heure titre"
    lines_and_entries: list[tuple[str, PlanningDay | None, PlanningEntry | None]] = []
    for day in sorted_days:
        day_label = f"{day.day_name.strip()} ({day.date})" if day.date else day.day_name.strip()
        if day.date == today_str:
            day_label = constants.YELLOW + day_label + constants.RESET
        lines_and_entries.append((day_label, day, None))
        for entry in day.entries:
            time_part = (entry.time or "").strip()
            title_part = (entry.title or "").strip()
            line = f"   • {time_part} — {title_part}" if time_part else "   • " + title_part
            lines_and_entries.append((line, day, entry))

    items = [t[0] for t in lines_and_entries]
    planning_prompt = "Choisir un animé (↓↑ pour naviguer, Esc pour revenir au menu principal) : "
    print(constants.BLUE + "  Chargement des couvertures..." + constants.RESET)
    slug_to_cover: dict[str, str] = {}
    try:
        catalogues = await api.all_catalogues()
        for c in catalogues:
            slug = c.url.rstrip("/").split("/")[-1]
            if slug:
                slug_to_cover[slug] = getattr(c, "image_url", "") or ""
    except Exception:
        pass

    preview_objects = [
        SimpleNamespace(
            name=line,
            image_url=slug_to_cover.get(menus.slug_from_planning_url(entry.url), "") if entry else "",
            site_url=constants.SITE_URL,
        )
        for line, _day, entry in lines_and_entries
    ]

    while True:
        choice = fzf_utils.fzf_select(
            items,
            planning_prompt,
            catalogues_for_preview=preview_objects,
        )
        if not choice:
            return
        selected = next((t for t in lines_and_entries if t[0] == choice), None)
        if not selected:
            return
        _line, _day, entry = selected
        if entry is not None:
            break
        # Sélection d’un en-tête de jour : on réaffiche pour choisir un animé

    cfg = config.load_config() or {}
    player = cfg.get("player", "mpv").strip()
    prefer_lang = [entry.lang] if entry.lang in ("VF", "VOSTFR") else ["VOSTFR"]

    season = Season(entry.url, client=client)
    try:
        episodes = await season.episodes()
    except Exception:
        episodes = []

    ep_idx = len(episodes) - 1 if episodes else 0
    while True:
        if not episodes:
            action = menus.menu_planning_episode_not_available(has_prev=False)
        else:
            ep_idx = min(max(ep_idx, 0), len(episodes) - 1)
            episode = episodes[ep_idx]
            try:
                stream_url = episode.best(prefer_lang) if hasattr(episode, "best") else None
            except Exception:
                stream_url = None

            if not stream_url:
                action = menus.menu_planning_episode_not_available(has_prev=(ep_idx > 0))
                if action == "prev":
                    ep_idx -= 1
                    if ep_idx >= 0:
                        episode = episodes[ep_idx]
                        print()
                        print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_idx + 1} en cours de visionnage ..." + constants.RESET)
                        print()
                        proc = playback.play_episode_api(episode, prefer_lang, player)
                        if proc:
                            proc.wait()
                        action = menus.menu_planning_after_play(has_prev=(ep_idx > 0))
            else:
                print()
                print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_idx + 1} en cours de visionnage ..." + constants.RESET)
                print()
                proc = playback.play_episode_api(episode, prefer_lang, player)
                if proc:
                    proc.wait()
                action = menus.menu_planning_after_play(has_prev=(ep_idx > 0))

        while True:
            if action == "quitter":
                return
            if action == "menu":
                return
            if action == "planning":
                break
            if action == "prev":
                ep_idx -= 1
                if ep_idx >= 0:
                    episode = episodes[ep_idx]
                    print()
                    print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_idx + 1} en cours de visionnage ..." + constants.RESET)
                    print()
                    proc = playback.play_episode_api(episode, prefer_lang, player)
                    if proc:
                        proc.wait()
                    action = menus.menu_planning_after_play(has_prev=(ep_idx > 0))
                else:
                    ep_idx = 0
                    action = menus.menu_planning_after_play(has_prev=False)
                continue
            break

        if action != "planning":
            break

        while True:
            choice = fzf_utils.fzf_select(
                items,
                planning_prompt,
                catalogues_for_preview=preview_objects,
            )
            if not choice:
                return
            selected = next((t for t in lines_and_entries if t[0] == choice), None)
            if not selected:
                return
            _line, _day, entry = selected
            if entry is not None:
                break
        season = Season(entry.url, client=client)
        try:
            episodes = await season.episodes()
        except Exception:
            episodes = []
        ep_idx = len(episodes) - 1 if episodes else 0
