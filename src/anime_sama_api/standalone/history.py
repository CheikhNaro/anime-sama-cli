# -*- coding: utf-8 -*-
"""Historique des animés regardés."""

from __future__ import annotations

import json
from typing import Any

from . import constants


def load_history() -> list[dict[str, Any]]:
    """Charge l'historique des animés regardés."""
    if not constants.HISTORY_FILE.exists():
        return []
    try:
        with open(constants.HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_history(entries: list[dict[str, Any]]) -> None:
    """Sauvegarde l'historique."""
    constants.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(constants.HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def add_to_history(anime_name: str, season: int, episode: int) -> None:
    """Ajoute ou met à jour l'entrée pour cet animé."""
    name = (anime_name or "").strip()
    if not name:
        return
    entries = load_history()
    entries = [e for e in entries if (e.get("anime") or "").strip() != name]
    entries.insert(0, {"anime": name, "season": season, "episode": episode})
    save_history(entries)
