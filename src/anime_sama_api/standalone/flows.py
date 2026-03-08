# -*- coding: utf-8 -*-
"""Flux principaux : regarder un animé et télécharger."""

from __future__ import annotations

from . import constants
from . import terminal
from . import config
from . import history
from . import fzf_utils
from . import api_helpers
from . import menus
from . import playback
from . import download_utils

from anime_sama_api.cli.episode_tree import run_multi_season_episode_tree_async


async def run_watch_flow(cfg: dict[str, str]) -> bool:
    """Retourne True pour rester dans l'app, False pour quitter."""
    player = cfg.get("player", "mpv").strip()
    language = cfg.get("language", "VOSTFR").strip()
    prefer_languages = [language]

    while True:
        search_action = menus.menu_search(title_override="👀 Regarder")
        if search_action == "quitter":
            return False
        if search_action == "menu":
            return True

        catalogue = None
        if search_action == "recherche":
            terminal.clear_screen()
            try:
                q = input(constants.CYAN + "Titre de l'animé : " + constants.RESET).strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if not q:
                continue
            print(constants.BLUE + "Recherche..." + constants.RESET)
            catalogues = await api_helpers.search_catalogues(q)
            if not catalogues:
                print(constants.YELLOW + "Aucun résultat." + constants.RESET)
                input("Appuyez sur Entrée...")
                continue
            items = [c.name for c in catalogues]
            choice = fzf_utils.fzf_select(items, "Choisir un animé : ", catalogues_for_preview=catalogues)
            if not choice:
                continue
            for c in catalogues:
                if (c.name or "").strip() == (choice or "").strip():
                    catalogue = c
                    break
            if not catalogue:
                continue

        elif search_action == "catalogue":
            terminal.clear_screen()
            print(constants.BLUE + "Chargement du catalogue ..." + constants.RESET)
            catalogues = await api_helpers.get_catalogues("")
            if not catalogues:
                print(constants.YELLOW + "Aucun résultat." + constants.RESET)
                input("Appuyez sur Entrée...")
                continue
            items = [c.name for c in catalogues]
            choice = fzf_utils.fzf_select(items, "Tapez pour filtrer (↓↑ = naviguer, Esc = menu précédent) : ", catalogues_for_preview=catalogues)
            if not choice:
                continue
            for c in catalogues:
                if (c.name or "").strip() == (choice or "").strip():
                    catalogue = c
                    break
            if not catalogue:
                continue

        if not catalogue:
            continue

        try:
            seasons = await catalogue.seasons()
        except Exception as e:
            print(constants.RED + f"Erreur : {e}" + constants.RESET)
            try:
                input("Appuyez sur Entrée... ")
            except (EOFError, KeyboardInterrupt):
                pass
            continue

        if not seasons:
            action = menus.alert_scan_read_online_and_return()
            if action == "quit":
                return False
            continue

        season_items = [s.name for s in seasons]
        while True:
            choice_s = fzf_utils.fzf_select(season_items, "Choisir la saison (↑↓ = se déplacer, Entrée = valider, Backspace = retour) : ")
            if not choice_s:
                break
            selected_season = None
            for s in seasons:
                if (s.name or "").strip() == (choice_s or "").strip():
                    selected_season = s
                    break
            if not selected_season:
                continue

            try:
                episodes = await selected_season.episodes()
            except Exception as e:
                print(constants.RED + f"Erreur : {e}" + constants.RESET)
                try:
                    input("Appuyez sur Entrée... ")
                except (EOFError, KeyboardInterrupt):
                    pass
                continue

            if not episodes:
                action = menus.alert_scan_read_online_and_return()
                if action == "quit":
                    return False
                break

            episode_items = [e.name for e in episodes]
            choice_ep = fzf_utils.fzf_select(episode_items, "Choisir l'épisode (↑↓ = se déplacer, Entrée = valider, Backspace = retour) : ")
            if not choice_ep:
                continue
            selected_episode = None
            idx_ep = -1
            for i, e in enumerate(episodes):
                if (e.name or "").strip() == (choice_ep or "").strip():
                    selected_episode = e
                    idx_ep = i
                    break
            if not selected_episode:
                continue

            season_index = next((i for i, s in enumerate(seasons) if s.name == selected_season.name), 0)
            ep_num = idx_ep + 1
            anime_name = (catalogue.name or "").strip()
            history.add_to_history(anime_name, season_index + 1, ep_num)
            print()
            print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_num} en cours de visionnage ..." + constants.RESET)
            print()
            proc = playback.play_episode_api(selected_episode, prefer_languages, player)
            if not proc:
                print(constants.RED + "Impossible de lancer la lecture." + constants.RESET)
                input("Appuyez sur Entrée...")
                continue
            proc.wait()

            has_next = idx_ep < len(episodes) - 1
            has_prev = idx_ep > 0
            is_last_ep = idx_ep == len(episodes) - 1
            has_next_season = season_index < len(seasons) - 1

            while True:
                after = menus.menu_after_play(ep_num, has_next, has_prev, is_last_ep, has_next_season, anime_name)
                if after == "quitter":
                    return False
                if after == "menu":
                    return True
                if after == "replay":
                    print()
                    print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_num} en cours de visionnage ..." + constants.RESET)
                    print()
                    proc = playback.play_episode_api(selected_episode, prefer_languages, player)
                    if proc:
                        proc.wait()
                    else:
                        print(constants.RED + "Impossible de relancer l'épisode." + constants.RESET)
                    continue
                if after == "suivant":
                    idx_ep += 1
                    selected_episode = episodes[idx_ep]
                    ep_num = idx_ep + 1
                    has_prev = True
                    has_next = idx_ep < len(episodes) - 1
                    is_last_ep = idx_ep == len(episodes) - 1
                    history.add_to_history(anime_name, season_index + 1, ep_num)
                    print()
                    print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_num} en cours de visionnage ..." + constants.RESET)
                    print()
                    proc = playback.play_episode_api(selected_episode, prefer_languages, player)
                    if proc:
                        proc.wait()
                    else:
                        print(constants.RED + "Impossible de lancer l'épisode suivant." + constants.RESET)
                    break
                elif after == "précédent":
                    idx_ep -= 1
                    selected_episode = episodes[idx_ep]
                    ep_num = idx_ep + 1
                    has_next = True
                    has_prev = idx_ep > 0
                    is_last_ep = False
                    history.add_to_history(anime_name, season_index + 1, ep_num)
                    print()
                    print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_num} en cours de visionnage ..." + constants.RESET)
                    print()
                    proc = playback.play_episode_api(selected_episode, prefer_languages, player)
                    if proc:
                        proc.wait()
                    else:
                        print(constants.RED + "Impossible de lancer l'épisode précédent." + constants.RESET)
                    break
                elif after == "saison_suivante":
                    if not has_next_season:
                        break
                    selected_season = seasons[season_index + 1]
                    season_index += 1
                    try:
                        episodes = await selected_season.episodes()
                    except Exception:
                        break
                    if not episodes:
                        break
                    idx_ep = 0
                    selected_episode = episodes[0]
                    ep_num = 1
                    has_prev = False
                    has_next = len(episodes) > 1
                    is_last_ep = len(episodes) == 1
                    has_next_season = season_index < len(seasons) - 1
                    history.add_to_history(anime_name, season_index + 1, ep_num)
                    print()
                    print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_num} en cours de visionnage ..." + constants.RESET)
                    print()
                    proc = playback.play_episode_api(selected_episode, prefer_languages, player)
                    if proc:
                        proc.wait()
                    else:
                        break
            break
        return True


async def run_download_flow_for_catalogue(cfg: dict[str, str], catalogue) -> None:
    """Télécharger : choisir saison/film ou épisode(s)."""
    language = cfg.get("language", "VOSTFR").strip()
    prefer_languages = [language] if language in ("VF", "VOSTFR") else ["VOSTFR"]

    try:
        seasons = await catalogue.seasons()
    except Exception as e:
        print(constants.RED + f"Erreur : {e}" + constants.RESET)
        return

    if not seasons:
        is_scan = getattr(catalogue, "is_manga", False) or (
            getattr(catalogue, "categories", set()) and "Scans" in getattr(catalogue, "categories", set())
        )
        terminal.clear_screen()
        if is_scan:
            print(constants.YELLOW + "Le téléchargement des scans n'est pas pris en charge." + constants.RESET)
            print()
            print("Consultez le site anime-sama.to pour lire les scans en ligne.")
        else:
            print(constants.YELLOW + "Aucun épisode ni film disponible pour le téléchargement." + constants.RESET)
        print()
        try:
            input("Appuyez sur Entrée... ")
        except (EOFError, KeyboardInterrupt):
            pass
        return

    seasons_with_episodes: list[tuple] = []
    for s in seasons:
        try:
            eps = await s.episodes()
        except Exception:
            eps = []
        seasons_with_episodes.append((s, eps))

    if not seasons_with_episodes or all(not eps for _, eps in seasons_with_episodes):
        print(constants.YELLOW + "Aucun épisode disponible pour le téléchargement." + constants.RESET)
        return

    title = (getattr(catalogue, "name", None) or "Saisons").strip()
    selected_episodes = await run_multi_season_episode_tree_async(
        seasons_with_episodes,
        title=title,
    )
    if not selected_episodes:
        return

    episodes_only = [e for _, e in selected_episodes]
    seasons_involved = {s for s, _ in selected_episodes}
    if len(seasons_involved) == 1:
        base_path = download_utils.download_folder_anime(catalogue, next(iter(seasons_involved)).name)
        base_path.mkdir(parents=True, exist_ok=True)
        download_utils.download_episodes(
            episodes_only,
            catalogue,
            base_path,
            "{episode}",
            prefer_languages,
            zip_if_multiple=len(episodes_only) > 1,
        )
    else:
        base_path = terminal.get_downloads_path()
        download_utils.download_episodes(
            episodes_only,
            catalogue,
            base_path,
            "{serie}/{season}/{episode}",
            prefer_languages,
            zip_if_multiple=True,
        )


async def run_download_flow(cfg: dict[str, str]) -> bool:
    """Flux télécharger : recherche puis téléchargement."""
    while True:
        search_action = menus.menu_search(title_override="📥 Télécharger")
        if search_action == "quitter":
            return False
        if search_action == "menu":
            return True

        catalogue = None
        if search_action == "recherche":
            terminal.clear_screen()
            try:
                q = input(constants.CYAN + "Titre de l'animé : " + constants.RESET).strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if not q:
                continue
            print(constants.BLUE + "Recherche..." + constants.RESET)
            catalogues = await api_helpers.search_catalogues(q)
            if not catalogues:
                print(constants.YELLOW + "Aucun résultat." + constants.RESET)
                input("Appuyez sur Entrée...")
                continue
            items = [c.name for c in catalogues]
            choice = fzf_utils.fzf_select(items, "Choisir un animé : ", catalogues_for_preview=catalogues)
            if not choice:
                continue
            for c in catalogues:
                if (c.name or "").strip() == (choice or "").strip():
                    catalogue = c
                    break
        elif search_action == "catalogue":
            terminal.clear_screen()
            print(constants.BLUE + "Chargement du catalogue..." + constants.RESET)
            catalogues = await api_helpers.get_catalogues("")
            if not catalogues:
                print(constants.YELLOW + "Aucun résultat." + constants.RESET)
                input("Appuyez sur Entrée...")
                continue
            items = [c.name for c in catalogues]
            choice = fzf_utils.fzf_select(items, "Recherche dynamique : ", catalogues_for_preview=catalogues)
            if not choice:
                continue
            for c in catalogues:
                if (c.name or "").strip() == (choice or "").strip():
                    catalogue = c
                    break

        if not catalogue:
            continue
        await run_download_flow_for_catalogue(cfg, catalogue)
