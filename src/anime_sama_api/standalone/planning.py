# -*- coding: utf-8 -*-
"""Affichage du planning des sorties et lecture depuis le planning."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from types import SimpleNamespace
from typing import Any

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
    print(constants.BOLD + constants.CYAN + "  📅 Planning de la semaine" + constants.RESET)
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
        print(constants.BOLD + constants.CYAN + "  📅 Planning de la semaine" + constants.RESET)
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

    def _season_label_from_url(url: str) -> str:
        """Extrait 'Saison N' depuis une URL type .../saison2 ou .../saison-1"""
        if not url:
            return "Saison 1"
        m = re.search(r"saison-?(\d+)", url, re.IGNORECASE)
        return f"Saison {m.group(1)}" if m else "Saison 1"

    def _season_number_from_url(url: str) -> int | None:
        """Extrait le numéro de saison (1, 2, ...) depuis l'URL du planning."""
        if not url:
            return None
        m = re.search(r"saison-?(\d+)", url, re.IGNORECASE)
        return int(m.group(1)) if m else None

    def _slot_datetime(day_date: str, time_str: str) -> datetime | None:
        """Construit datetime (année courante) depuis 'DD/MM' ou 'JJ/MM' et '14h20'."""
        if not day_date or "/" not in day_date:
            return None
        parts = day_date.strip().split("/")
        if len(parts) != 2:
            return None
        try:
            a, b = int(parts[0]), int(parts[1])
            hour, minute = 0, 0
            if time_str:
                tm = re.match(r"(\d{1,2})h(\d{2})", time_str.strip(), re.IGNORECASE)
                if tm:
                    hour, minute = int(tm.group(1)), int(tm.group(2))
            now = datetime.now()
            # DD/MM (français) : si le 2e nombre > 12, c’est le jour (ambiguïté MM/DD)
            day_num, month = a, b
            if month > 12:
                day_num, month = b, a
            return datetime(now.year, month, day_num, hour, minute)
        except (ValueError, IndexError):
            return None

    # Disponibilité et saison sans fetch : uniquement date/heure et URL (rapide)
    now = datetime.now()
    entry_to_info: dict[str, tuple[str, bool]] = {}  # url -> (season_label, available)
    for day in sorted_days:
        for entry in day.entries:
            season_label = _season_label_from_url(entry.url)
            time_str = (entry.time or "").strip()
            # Voyant rouge si heure "Retardé" ou "?" (indisponible)
            if time_str and (re.search(r"retardé", time_str, re.IGNORECASE) or time_str.strip() == "?"):
                available = False
            else:
                slot_dt = _slot_datetime(day.date or "", time_str)
                available = slot_dt is not None and slot_dt <= now
            entry_to_info[entry.url] = (season_label, available)

    # Arbre : "   • 🟢/🔴 heure - titre | Saison N" (sans numéro d'épisode)
    lines_and_entries: list[tuple[str, PlanningDay | None, PlanningEntry | None, tuple[str, bool] | None]] = []
    for day in sorted_days:
        day_label = f"{day.day_name.strip()} ({day.date})" if day.date else day.day_name.strip()
        lines_and_entries.append((day_label, day, None, None))
        for entry in day.entries:
            info = entry_to_info.get(entry.url, ("Saison 1", False))
            season_label, available = info
            time_part = (entry.time or "").strip()
            title_part = (entry.title or "").strip()
            icon = "🟢" if available else "🔴"
            mid = f"{icon}{time_part} - " if time_part else f"{icon} "
            suffix = f" | {season_label}"
            line = f"   • {mid}{title_part}{suffix}"
            lines_and_entries.append((line, day, entry, info))

    items = [t[0] for t in lines_and_entries]
    planning_prompt = "Choisir un animé (↓↑ pour naviguer, Esc pour revenir au menu principal) : "
    base = constants.SITE_URL.rstrip("/")

    def _catalogue_page_url(entry_url: str) -> str:
        """URL de la page catalogue (synopsis/genre/type), pas la page saison."""
        if not entry_url:
            return ""
        slug = menus.slug_from_planning_url(entry_url)
        if slug:
            return f"{base}/catalogue/{slug}"
        if entry_url.startswith("http"):
            url = entry_url
        else:
            url = base + "/" + entry_url.lstrip("/")
        if "/saison-" in url:
            url = url.split("/saison-")[0]
        return url

    slug_to_cover: dict[str, str] = {}
    slug_to_catalogue: dict[str, Any] = {}
    try:
        catalogues = await api.all_catalogues()
        for c in catalogues:
            slug = (c.url or "").rstrip("/").split("/")[-1]
            if slug:
                slug_to_cover[slug] = getattr(c, "image_url", "") or ""
                slug_to_catalogue[slug] = c
    except Exception:
        pass

    def _catalogue_for_entry(entry: PlanningEntry | None) -> Any:
        if not entry:
            return None
        return slug_to_catalogue.get(menus.slug_from_planning_url(entry.url))

    # Cache : nom animé -> catalogue (recherche site) pour la preview ; chargement en parallèle
    unique_titles_list = list({(row[2].title or "").strip() for row in lines_and_entries if row[2] is not None and (row[2].title or "").strip()})
    title_to_catalogue: dict[str, Any] = {}
    if unique_titles_list:
        print(constants.BLUE + "  Chargement des infos..." + constants.RESET)
        tasks = [api_helpers.get_catalogue_for_planning_entry(title) for title in unique_titles_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for title, result in zip(unique_titles_list, results):
            title_to_catalogue[title] = result if not isinstance(result, Exception) else None

    # Preview uniquement pour les lignes animé (pas pour les en-têtes de date type "Lundi (02/03)")
    preview_objects = []
    for row in lines_and_entries:
        line, _day, entry = row[0], row[1], row[2]
        if entry is None:
            continue
        cat = title_to_catalogue.get((entry.title or "").strip()) or _catalogue_for_entry(entry)
        genres = list(getattr(cat, "genres", None) or []) if cat else []
        categories = set(getattr(cat, "categories", None) or set()) if cat else set()
        image_url = (getattr(cat, "image_url", None) or "") if cat else slug_to_cover.get(menus.slug_from_planning_url(entry.url), "")
        page_url = (getattr(cat, "url", None) or "").strip().rstrip("/")
        if not page_url or not page_url.startswith("http"):
            page_url = _catalogue_page_url(entry.url) if entry else ""
        preview_objects.append(
            SimpleNamespace(
                name=line,
                title=(getattr(cat, "name", None) or entry.title or line) if cat else (entry.title or line),
                image_url=image_url,
                site_url=constants.SITE_URL,
                page_url=page_url,
                genres=genres,
                categories=categories,
            )
        )

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
        _line, _day, entry, info = selected[0], selected[1], selected[2], selected[3]
        if entry is None:
            continue
        _season_label, available = info or ("Saison 1", False)
        if not available:
            menus.alert_planning_episode_not_yet_released()
            continue
        break
        # Sélection d’un en-tête de jour : on réaffiche pour choisir un animé

    cfg = config.load_config() or {}
    player = cfg.get("player", "mpv").strip()
    prefer_lang = [entry.lang] if entry.lang in ("VF", "VOSTFR") else ["VOSTFR"]

    # Lancer le dernier épisode de la saison du planning : nom → recherche catalogue → saison de l’entry → dernier épisode
    def _season_base_url(entry_url: str) -> str:
        """Retire le segment de langue (vostfr, vf, ...) de l'URL planning pour avoir la base saison."""
        u = (entry_url or "").rstrip("/")
        if not u:
            return u
        parts = u.split("/")
        if parts and parts[-1].lower() in ("vostfr", "vf", "vj", "va", "vcn", "vkr", "vqc"):
            u = "/".join(parts[:-1])
        return u + "/" if u else ""

    async def _load_episodes_for_planning_entry(entry: PlanningEntry) -> tuple[list, int]:
        # Même approche que le flux Regarder : catalogue -> saisons -> épisodes (comme flows.run_watch_flow)
        entry_url = (getattr(entry, "url", None) or "").strip()
        if not entry_url or "catalogue" not in entry_url:
            return [], 0
        season_base = _season_base_url(entry_url)
        catalogue = slug_to_catalogue.get(menus.slug_from_planning_url(entry_url))
        if not catalogue and entry.title:
            try:
                catalogues = await api_helpers.search_catalogues((entry.title or "").strip())
                catalogue = catalogues[0] if catalogues else None
            except Exception:
                catalogue = None
        if catalogue:
            try:
                seasons = await catalogue.seasons()
                for s in seasons:
                    su = (getattr(s, "url", "") or "").rstrip("/") + "/"
                    if su == season_base or entry_url.startswith(su.rstrip("/")):
                        episodes = await s.episodes()
                        if episodes:
                            return episodes, len(episodes) - 1
                        break
                if seasons:
                    episodes = await seasons[-1].episodes()
                    if episodes:
                        return episodes, len(episodes) - 1
            except Exception:
                pass
        # Repli : Season depuis l'URL du planning
        try:
            season = Season(season_base, client=client)
            episodes = await season.episodes()
        except Exception:
            return [], 0
        if not episodes:
            return [], 0
        return episodes, len(episodes) - 1

    episodes, ep_idx = await _load_episodes_for_planning_entry(entry)

    while True:
        if not episodes:
            action = menus.menu_planning_episode_not_available(has_prev=False)
        else:
            ep_idx = min(max(ep_idx, 0), len(episodes) - 1)
            episode = episodes[ep_idx]
            print()
            print(constants.BOLD + constants.CYAN + f"Épisode N°{ep_idx + 1} en cours de visionnage ..." + constants.RESET)
            print()
            proc = playback.play_episode_api(episode, prefer_lang, player)
            if proc:
                proc.wait()
                action = menus.menu_planning_after_play(has_prev=(ep_idx > 0))
            else:
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
            _line, _day, entry, info = selected[0], selected[1], selected[2], selected[3]
            if entry is None:
                continue
            _sl, available = info or ("Saison 1", False)
            if not available:
                menus.alert_planning_episode_not_yet_released()
                continue
            break
        episodes, ep_idx = await _load_episodes_for_planning_entry(entry)
