# -*- coding: utf-8 -*-
"""TUI Textual pour le planning : liste à gauche, cover fixe + infos scrollables à droite.

Layout :
  ┌──────────────────────────────┬────────────────────────────┐
  │  Liste planning (OptionList) │  Cover (titre + genres)    │  ← fixe
  │  • Day headers (disabled)    ├────────────────────────────┤
  │  • Anime entries             │  Infos (synopsis, etc.)    │  ← scrollable
  └──────────────────────────────┴────────────────────────────┘
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, OptionList
from textual.widgets.option_list import Option

# ---------------------------------------------------------------------------
# Constantes d'UI
# ---------------------------------------------------------------------------
_FOOTER_HINTS = (
    "↓↑ naviguer  ·  Entrée = sélectionner  ·  Esc = retour au menu"
)
_PLACEHOLDER_COVER = "[dim]Sélectionnez un animé pour voir sa fiche.[/dim]"

_CSS = """
Screen {
    background: #0c0c0c;
}
Header {
    display: none;
}
Footer {
    display: none;
}
#main-container {
    height: 1fr;
}
#list-panel {
    width: 55%;
    background: #0c0c0c;
    border-right: tall #1e1e2e;
}
#planning-list {
    background: #0c0c0c;
    height: 1fr;
    border: none;
    padding: 0 0;
}
#preview-panel {
    width: 45%;
    layout: vertical;
    background: #0c0c0c;
}
#cover-panel {
    height: 10;
    background: #0d1117;
    padding: 1 2;
    color: #e0e0e0;
    border-bottom: tall #1e1e2e;
}
#info-scroll {
    height: 1fr;
    background: #0c0c0c;
}
#info-content {
    background: #0c0c0c;
    padding: 1 2;
    color: #c0c0c0;
}
#tui-footer {
    dock: bottom;
    height: 1;
    background: #0d1117;
    color: #606060;
    content-align: center middle;
    text-align: center;
    padding: 0 1;
}
OptionList > .option-list--option-disabled {
    color: #7090b0;
    text-style: bold;
    background: #101828;
}
OptionList > .option-list--option {
    color: #c0c0c0;
}
OptionList > .option-list--option-highlighted {
    background: #1e2a3a;
    color: #e0e0e0;
}
"""


# ---------------------------------------------------------------------------
# Helpers de markup Rich
# ---------------------------------------------------------------------------

def _cover_markup(obj: SimpleNamespace) -> str:
    """Génère le markup Rich pour le panneau cover (titre + genres/catégories)."""
    title = (obj.title or "").strip() or "—"
    cats = list(obj.categories or [])
    genres = obj.genres or []

    lines = [f"[bold cyan]{title}[/bold cyan]"]
    if cats:
        lines.append("[#909090]" + "  ·  ".join(str(c) for c in cats[:3]) + "[/#909090]")
    if genres:
        lines.append("[green]" + "  ·  ".join(str(g) for g in genres[:4]) + "[/green]")

    return "\n".join(lines)


def _info_markup(obj: SimpleNamespace, synopsis: str | None = None) -> str:
    """Génère le markup Rich pour le panneau infos.

    synopsis=None  → "Chargement…"
    synopsis=""    → rien (absent ou non disponible)
    synopsis="…"   → affichage du texte
    """
    title = (obj.title or "").strip() or "—"
    cats = list(obj.categories or [])
    genres = obj.genres or []
    page_url = (getattr(obj, "page_url", "") or "").strip()

    parts: list[str] = [f"[bold white]{title}[/bold white]\n\n"]

    if genres:
        parts.append(f"[yellow]Genres :[/yellow]  {', '.join(str(g) for g in genres)}\n")
    if cats:
        parts.append(f"[yellow]Type   :[/yellow]  {', '.join(str(c) for c in cats)}\n")

    if synopsis:
        parts.append(f"\n[dim]Synopsis[/dim]\n{synopsis}\n")
    elif synopsis is None:
        parts.append("\n[dim]Chargement du synopsis…[/dim]\n")

    if page_url:
        parts.append(f"\n[dim]{page_url}[/dim]\n")

    return "".join(parts) if len(parts) > 1 else "[dim]Aucune information disponible.[/dim]"


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
# Application Textual
# ---------------------------------------------------------------------------

class PlanningApp(App[tuple | None]):
    """TUI planning : liste à gauche, cover fixe + infos scrollables à droite."""

    TITLE = ""
    SUB_TITLE = ""
    CSS = _CSS

    BINDINGS = [
        Binding("escape", "quit", "Retour", show=False),
        Binding("q", "quit", "Quitter", show=False),
    ]

    def __init__(
        self,
        lines_and_entries: list,
        preview_objects: list[SimpleNamespace],
    ) -> None:
        super().__init__()
        self._rows = lines_and_entries
        # name (= line formatée) → SimpleNamespace pour la preview
        self._preview_map: dict[str, SimpleNamespace] = {
            obj.name: obj for obj in preview_objects
        }
        # opt_id → index dans self._rows (uniquement pour les entrées animé)
        self._opt_to_row_idx: dict[str, int] = {}
        self._current_opt_id: str | None = None
        self._synopsis_cache: dict[str, str] = {}

    # ------------------------------------------------------------------ compose

    def compose(self) -> ComposeResult:
        option_list = OptionList(id="planning-list")

        for i, row in enumerate(self._rows):
            line, _day, entry, _info = row[0], row[1], row[2], row[3]
            opt_id = f"opt_{i}"
            is_header = entry is None
            option_list.add_option(Option(line, id=opt_id, disabled=is_header))
            if not is_header:
                self._opt_to_row_idx[opt_id] = i

        with Horizontal(id="main-container"):
            with Vertical(id="list-panel"):
                yield option_list
            with Vertical(id="preview-panel"):
                yield Static(_PLACEHOLDER_COVER, id="cover-panel")
                with ScrollableContainer(id="info-scroll"):
                    yield Static("", id="info-content")

        yield Static(_FOOTER_HINTS, id="tui-footer")

    # ---------------------------------------------------------------- navigation

    def on_option_list_option_highlighted(self, msg: OptionList.OptionHighlighted) -> None:
        """Met à jour le panneau preview quand le curseur change."""
        opt_id = msg.option.id
        self._current_opt_id = opt_id

        cover = self.query_one("#cover-panel", Static)
        info_widget = self.query_one("#info-content", Static)

        # En-tête de jour : pas de preview
        if opt_id not in self._opt_to_row_idx:
            cover.update(_PLACEHOLDER_COVER)
            info_widget.update("")
            return

        row = self._rows[self._opt_to_row_idx[opt_id]]
        obj = self._preview_map.get(row[0])

        if obj is None:
            cover.update(_PLACEHOLDER_COVER)
            info_widget.update("")
            return

        cover.update(_cover_markup(obj))

        page_url = (getattr(obj, "page_url", "") or "").strip()
        if page_url in self._synopsis_cache:
            info_widget.update(_info_markup(obj, self._synopsis_cache[page_url]))
        else:
            # Affiche d'abord les infos disponibles, puis charge le synopsis
            info_widget.update(_info_markup(obj, synopsis=None))
            if page_url:
                self.run_worker(
                    self._load_synopsis(opt_id, obj, page_url),
                    exclusive=True,
                    group="synopsis",
                )

    # ----------------------------------------------------------------- selection

    def on_option_list_option_selected(self, msg: OptionList.OptionSelected) -> None:
        """Valide la sélection si l'épisode est disponible."""
        opt_id = msg.option.id
        if opt_id not in self._opt_to_row_idx:
            return

        row = self._rows[self._opt_to_row_idx[opt_id]]
        _line, _day, entry, info = row[0], row[1], row[2], row[3]

        if entry is None:
            return

        _season_label, available = info or ("Saison 1", False)
        if not available:
            self.notify(
                "Cet épisode n'est pas encore disponible.",
                title="Non disponible",
                severity="warning",
                timeout=3,
            )
            return

        self.exit(row)

    # --------------------------------------------------------- synopsis async

    async def _load_synopsis(
        self,
        opt_id: str,
        obj: SimpleNamespace,
        page_url: str,
    ) -> None:
        """Télécharge le synopsis en arrière-plan et met à jour le panneau infos."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    page_url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; anime-sama-cli)"},
                    follow_redirects=True,
                )
                synopsis = _extract_synopsis_from_html(resp.text)
        except Exception:
            synopsis = ""

        self._synopsis_cache[page_url] = synopsis

        # Met à jour l'UI uniquement si c'est encore l'option courante
        if self._current_opt_id == opt_id:
            info_widget = self.query_one("#info-content", Static)
            info_widget.update(_info_markup(obj, synopsis))


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def run_planning_tui(
    lines_and_entries: list,
    preview_objects: list[SimpleNamespace],
) -> tuple | None:
    """Lance le TUI planning de manière synchrone."""
    app = PlanningApp(lines_and_entries, preview_objects)
    app.run()
    return app.return_value


async def run_planning_tui_async(
    lines_and_entries: list,
    preview_objects: list[SimpleNamespace],
) -> tuple | None:
    """Lance le TUI planning de manière asynchrone (boucle asyncio en cours)."""
    app = PlanningApp(lines_and_entries, preview_objects)
    await app.run_async()
    return app.return_value
