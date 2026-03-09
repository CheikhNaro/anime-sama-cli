# -*- coding: utf-8 -*-
"""Interface fzf pour le planning : sélection avec preview cover + infos.

  ┌──────────────────────────────┬────────────────────────────┐
  │  Liste fzf (planning)        │  Cover (sixels) + Titre,   │
  │  • En-têtes jours (désact.)  │  Genre, Type, Synopsis      │
  │  • Entrées animés            │                             │
  └──────────────────────────────┴────────────────────────────┘
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

from . import fzf_utils


# ---------------------------------------------------------------------------
# Helpers (gardés pour compatibilité avec d'autres modules)
# ---------------------------------------------------------------------------

def _extract_synopsis_from_html(html: str) -> str:
    """Extrait le synopsis depuis le HTML de la page catalogue."""
    import html as html_module

    for m in re.finditer(r"Synopsis[\W\w]+?>(.+?)<", html):
        raw = html_module.unescape(m.group(1).strip())
        if raw and raw != "Synopsis" and len(raw) > 15:
            return raw

    m2 = re.search(r"Synopsis\s*</[^>]+>\s*<[^>]+>(.+?)</[^>]+>", html, re.DOTALL)
    if m2:
        return html_module.unescape(m2.group(1).strip())

    return ""


# ---------------------------------------------------------------------------
# Runners (mêmes signatures que l'ancienne version Textual)
# ---------------------------------------------------------------------------

def run_planning_tui(
    lines_and_entries: list,
    preview_objects: list[SimpleNamespace],
) -> tuple | None:
    """Sélection planning via fzf avec preview cover + infos.

    Retourne le tuple (line, day, entry, info) sélectionné, ou None.
    Les en-têtes (jours) sont ignorés si sélectionnés.
    """
    if not lines_and_entries:
        return None

    items = [row[0] for row in lines_and_entries]
    line_to_rows: dict[str, list] = {}
    for row in lines_and_entries:
        line_to_rows.setdefault(row[0], []).append(row)

    selected = fzf_utils.fzf_select(
        items,
        prompt="Planning : ",
        catalogues_for_preview=preview_objects,
    )
    if not selected or isinstance(selected, list):
        return None

    rows = line_to_rows.get(selected)
    if not rows:
        return None
    row = rows[0]

    if row[2] is None:
        return None

    return row


async def run_planning_tui_async(
    lines_and_entries: list,
    preview_objects: list[SimpleNamespace],
) -> tuple | None:
    """Version async de run_planning_tui."""
    import asyncio

    return await asyncio.to_thread(run_planning_tui, lines_and_entries, preview_objects)
