# -*- coding: utf-8 -*-
"""Téléchargement des épisodes et nomenclature des dossiers."""

from __future__ import annotations

import re
from pathlib import Path

from . import constants
from . import terminal


def sanitize_filename(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s).strip() or "anime"


def download_folder_anime(catalogue, season_name: str) -> Path:
    base = terminal.get_downloads_path()
    name = sanitize_filename(f"{catalogue.name} {season_name}")
    return base / name


def download_folder_scan(catalogue, chapter_name: str) -> Path:
    base = terminal.get_downloads_path()
    name = sanitize_filename(f"{catalogue.name} {chapter_name}")
    return base / name


def download_episodes(
    episodes: list,
    catalogue,
    base_path: Path,
    episode_path_tpl: str,
    prefer_languages: list[str],
    zip_if_multiple: bool,
) -> None:
    """Télécharge les épisodes (API multi_download) et zippe si demandé."""
    try:
        from anime_sama_api.cli.downloader import multi_download
        from anime_sama_api.cli.episode_extra_info import convert_with_extra_info
        from anime_sama_api.cli.config import PlayersConfig
        lang_list = [l for l in prefer_languages if l in ("VF", "VOSTFR")]
        if not lang_list:
            lang_list = ["VOSTFR"]
        extra = [convert_with_extra_info(ep, catalogue) for ep in episodes]
        multi_download(
            extra,
            base_path,
            episode_path_tpl,
            {"video": 1, "fragment": 3},
            lang_list,
            PlayersConfig([], []),
            video_format="best",
        )
        if zip_if_multiple and len(episodes) > 1:
            import zipfile
            zip_name = base_path / f"{sanitize_filename(catalogue.name)}_episodes.zip"
            with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in base_path.rglob("*"):
                    if f.is_file() and f.suffix in (".mp4", ".mkv", ".webm"):
                        zf.write(f, f.relative_to(base_path))
            print(constants.GREEN + f"Archive créée : {zip_name}" + constants.RESET)
    except Exception as e:
        print(constants.RED + f"Erreur téléchargement : {e}" + constants.RESET)


def download_scan_chapters(catalogue, chapters_selected: list, base_path: Path) -> None:
    print(constants.YELLOW + "Le téléchargement des scans n'est pas pris en charge par l'API." + constants.RESET)
    print("Consultez le site anime-sama.to pour lire les scans en ligne.")
