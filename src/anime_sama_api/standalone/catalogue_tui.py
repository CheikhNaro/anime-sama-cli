# -*- coding: utf-8 -*-
"""Interface fzf pour le catalogue : sélection avec preview cover + infos.

  ┌──────────────────────────────┬────────────────────────────┐
  │  Liste fzf (noms d'animés)   │  Cover (sixels) + Titre,   │
  │                              │  Genre, Type, Synopsis      │
  └──────────────────────────────┴────────────────────────────┘
"""

from __future__ import annotations

from typing import Any

from . import fzf_utils
from . import terminal


def _load_ascii_art() -> str:
    """Charge l'ASCII art pour affichage avant le prompt."""
    try:
        from importlib.resources import files

        return (files("anime_sama_api") / "assets" / "ascii_art").read_text(encoding="utf-8")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Runners (mêmes signatures que l'ancienne version Textual)
# ---------------------------------------------------------------------------

def run_search_prompt_tui() -> str | None:
    """Affiche l'ASCII art et demande le titre à rechercher. Retourne la saisie ou None."""
    terminal.clear_screen()
    art = _load_ascii_art()
    if art:
        from . import constants

        for line in art.splitlines():
            print(constants.CYAN + line + constants.RESET)
        print()
    try:
        query = input("Titre de l'animé : ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    return query or None


async def run_search_prompt_tui_async() -> str | None:
    """Version async de run_search_prompt_tui."""
    import asyncio

    return await asyncio.to_thread(run_search_prompt_tui)


def run_catalogue_tui(
    catalogues: list[Any],
    is_search_results: bool = False,
) -> Any | None:
    """Sélection catalogue via fzf avec preview. Retourne le Catalogue sélectionné ou None."""
    if not catalogues:
        return None
    if len(catalogues) == 1 and not is_search_results:
        return catalogues[0]

    items = [
        (getattr(c, "name", None) or "").strip() or f"Animé #{i + 1}"
        for i, c in enumerate(catalogues)
    ]
    selected = fzf_utils.fzf_select(
        items,
        prompt="Choisir un animé : ",
        catalogues_for_preview=catalogues,
    )
    if not selected or isinstance(selected, list):
        return None
    for cat in catalogues:
        if (getattr(cat, "name", None) or "").strip() == selected:
            return cat
    return None


async def run_catalogue_tui_async(
    catalogues: list[Any],
    is_search_results: bool = False,
) -> Any | None:
    """Version async de run_catalogue_tui."""
    import asyncio

    return await asyncio.to_thread(run_catalogue_tui, catalogues, is_search_results)
