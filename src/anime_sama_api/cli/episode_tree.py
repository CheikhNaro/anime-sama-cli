# -*- coding: utf-8 -*-
"""Affichage et sélection des épisodes via le widget Tree de Textual.
↑↓ déplacer · Espace sélection · Tab déplier/replier · Entrée valider.
"""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static, Tree

from anime_sama_api.episode import Episode
from anime_sama_api.season import Season


# Type pour les données d'un nœud : None (racine), liste d'épisodes (saison), ou un épisode (feuille)
NodeData = Episode | list[Episode] | None


class EpisodeTreeToggleSelection(Message):
    """Message émis quand l'utilisateur appuie sur Espace pour (dé)sélectionner un nœud."""

    def __init__(self, node: Any) -> None:
        self.node = node
        super().__init__()


class EpisodeTreeConfirmSelection(Message):
    """Message émis quand l'utilisateur appuie sur Entrée pour valider la sélection."""

    pass


class EpisodeTreeWidget(Tree[NodeData]):
    """Tree personnalisé : Tab = déplier/replier, Espace = sélection, Entrée = valider."""

    inherit_bindings = False

    BINDINGS = [
        Binding("up", "cursor_up", "Haut", show=False),
        Binding("down", "cursor_down", "Bas", show=False),
        Binding("tab", "toggle_node", "Déplier/Replier", show=False),
        Binding("space", "toggle_selection", "Sélection", show=False),
        Binding("enter", "confirm_selection", "Valider", show=False),
    ]

    def action_toggle_selection(self) -> None:
        """Espace : ajoute ou retire le nœud courant de la sélection."""
        node = self.cursor_node
        if node is not None:
            self.post_message(EpisodeTreeToggleSelection(node))

    def action_confirm_selection(self) -> None:
        """Entrée : valide la sélection et envoie le message à l'App."""
        self.post_message(EpisodeTreeConfirmSelection())


class EpisodeTree(App[list[Episode] | None]):
    """Application Textual : tree des épisodes, tous les parents repliés.
    Sélection multiple : parent = tout télécharger, enfants = épisodes choisis.
    """

    BINDINGS = [
        ("q", "quit", "Quitter"),
    ]

    SUB_TITLE = "↑↓ déplacer · Espace Sélection · Tab déplier/replier · Entrée valider"

    def __init__(
        self,
        season: Season,
        episodes: list[Episode],
        *,
        title: str | None = None,
    ) -> None:
        super().__init__()
        self._season = season
        self._episodes = episodes
        self._title = title or f"{season.serie_name} - {season.name}"
        self._all_episodes: list[Episode] = list(episodes)
        self._selected_node_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        root_label = self._title
        tree = EpisodeTreeWidget(root_label, data=None, id="episode-tree")
        # Tous les parents restent repliés (on n'appelle pas expand())
        for ep in self._episodes:
            tree.root.add_leaf(ep.fancy_name, ep)
        yield tree

    def on_episode_tree_toggle_selection(self, message: EpisodeTreeToggleSelection) -> None:
        """Espace : bascule la sélection du nœud sous le curseur."""
        node = message.node
        nid = node.id
        if nid in self._selected_node_ids:
            self._selected_node_ids.discard(nid)
        else:
            self._selected_node_ids.add(nid)
        self._refresh_tree_labels()

    def on_episode_tree_confirm_selection(self, _: EpisodeTreeConfirmSelection) -> None:
        """Entrée : construit la liste d'épisodes sélectionnés et quitte."""
        result = self._build_selected_episodes()
        self.exit(result)

    def _refresh_tree_labels(self) -> None:
        """Marque visuellement les nœuds sélectionnés (✓) en mettant à jour les libellés."""
        tree = self.query_one(EpisodeTreeWidget)
        from textual.widgets._tree import TreeNode

        def visit(node: TreeNode[NodeData]) -> None:
            try:
                plain = node.label.plain if hasattr(node.label, "plain") else str(node.label)
                if node.id in self._selected_node_ids:
                    if not plain.startswith("✓ "):
                        node.set_label("✓ " + plain)
                else:
                    if plain.startswith("✓ "):
                        node.set_label(plain[2:].strip())
            except Exception:
                pass
            for child in node.children:
                visit(child)

        visit(tree.root)
        tree.refresh()

    def _build_selected_episodes(self) -> list[Episode]:
        """À partir des nœuds sélectionnés, produit la liste d'épisodes (sans doublon, ordre conservé)."""
        tree = self.query_one(EpisodeTreeWidget)
        result: list[Episode] = []
        seen: set[tuple[str, int]] = set()

        for node_id in self._selected_node_ids:
            try:
                node = tree.get_node_by_id(node_id)
            except Exception:
                continue
            to_add: list[Episode] = []
            if node.is_root:
                to_add = list(self._all_episodes)
            elif isinstance(node.data, list):
                to_add = node.data
            elif isinstance(node.data, Episode):
                to_add = [node.data]
            for ep in to_add:
                key = (ep.season_name, ep.index)
                if key not in seen:
                    seen.add(key)
                    result.append(ep)
        return result


def run_episode_tree(
    season: Season,
    episodes: list[Episode],
    *,
    title: str | None = None,
) -> list[Episode] | None:
    """Affiche les épisodes en Tree (tous les parents repliés).
    Espace = sélectionner/désélectionner (parent = toute la saison, enfants = épisodes).
    Tab = déplier/replier un nœud. Entrée = valider. Retourne la liste des épisodes choisis ou None (q).
    """
    app = EpisodeTree(season, episodes, title=title)
    app.run()
    return app.return_value


# Données des nœuds pour le tree multi-saisons : (Season, list[Episode]) pour une saison, (Season, Episode) pour une feuille
MultiSeasonNodeData = tuple[Season, list[Episode]] | tuple[Season, Episode] | None


# Raccourcis affichés en haut de la fenêtre de sélection
TREE_HINTS = "↓↑ = naviguer · Esc = menu précédent · Tab = Déplier/Replier · Espace = Select · Entrée = Valider"


def _load_ascii_art() -> str:
    """Charge le contenu ASCII art du package (anime-sama)."""
    try:
        from importlib.resources import files
        return (files("anime_sama_api") / "assets" / "ascii_art").read_text(encoding="utf-8")
    except Exception:
        return ""


class MultiSeasonEpisodeTree(App[list[tuple[Season, Episode]] | None]):
    """Tree Textual avec une saison par nœud parent collapsible.
    Structure : Racine > Saison 1 (▶) > Episode 1, 2, … ; Saison 2 (▶) > …
    """

    TITLE = ""
    SUB_TITLE = ""

    BINDINGS = [
        ("q", "quit", "Quitter"),
        ("escape", "quit", "Menu précédent"),
    ]

    # Fond sombre type terminal ; ASCII art + indications
    CSS = """
    Screen {
        background: #0c0c0c;
    }
    Header {
        display: none;
    }
    #tree-ascii-art {
        padding: 0 1 0 1;
        padding-left: 2;
        margin-top: 1;
        margin-bottom: 1;
        background: #0c0c0c;
        color: #00bfff;
        height: auto;
    }
    #tree-hints {
        padding: 0 1 0 1;
        background: #0c0c0c;
        color: #a0a0a0;
        text-style: dim;
        height: auto;
    }
    #episode-tree {
        background: #0c0c0c;
        padding: 0 0 0 0;
    }
    """

    def __init__(
        self,
        seasons_with_episodes: list[tuple[Season, list[Episode]]],
        *,
        title: str = "Saisons",
    ) -> None:
        super().__init__()
        self._seasons_with_episodes = seasons_with_episodes
        self._title = title
        self._selected_node_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        yield Static(TREE_HINTS, id="tree-hints")
        ascii_art = _load_ascii_art()
        if ascii_art:
            yield Static(Text(ascii_art, style="bold cyan"), id="tree-ascii-art")
        tree = EpisodeTreeWidget(self._title, data=None, id="episode-tree")
        for season, episodes in self._seasons_with_episodes:
            season_node = tree.root.add(
                season.name,
                data=(season, episodes),
                expand=False,
            )
            for ep in episodes:
                label = ep.name.strip() if getattr(ep, "name", None) else f"Episode {ep.index}"
                season_node.add_leaf(label, (season, ep))
        yield tree

    def on_episode_tree_toggle_selection(self, message: EpisodeTreeToggleSelection) -> None:
        node = message.node
        nid = node.id
        if nid in self._selected_node_ids:
            self._selected_node_ids.discard(nid)
        else:
            self._selected_node_ids.add(nid)
        self._refresh_tree_labels()

    def on_episode_tree_confirm_selection(self, _: EpisodeTreeConfirmSelection) -> None:
        result = self._build_selected()
        self.exit(result)

    def _refresh_tree_labels(self) -> None:
        tree = self.query_one(EpisodeTreeWidget)
        from textual.widgets._tree import TreeNode

        def visit(node: TreeNode[MultiSeasonNodeData]) -> None:
            try:
                plain = node.label.plain if hasattr(node.label, "plain") else str(node.label)
                if node.id in self._selected_node_ids:
                    if not plain.startswith("✓ "):
                        node.set_label("✓ " + plain)
                else:
                    if plain.startswith("✓ "):
                        node.set_label(plain[2:].strip())
            except Exception:
                pass
            for child in node.children:
                visit(child)

        visit(tree.root)
        tree.refresh()

    def _build_selected(self) -> list[tuple[Season, Episode]]:
        tree = self.query_one(EpisodeTreeWidget)
        result: list[tuple[Season, Episode]] = []
        seen: set[tuple[str, int]] = set()

        for node_id in self._selected_node_ids:
            try:
                node = tree.get_node_by_id(node_id)
            except Exception:
                continue
            to_add: list[tuple[Season, Episode]] = []
            if node.is_root:
                for s, eps in self._seasons_with_episodes:
                    to_add.extend((s, ep) for ep in eps)
            elif isinstance(node.data, tuple):
                if len(node.data) == 2:
                    s, val = node.data
                    if isinstance(val, list):
                        to_add = [(s, ep) for ep in val]
                    else:
                        to_add = [(s, val)]
            for s, ep in to_add:
                key = (ep.season_name, ep.index)
                if key not in seen:
                    seen.add(key)
                    result.append((s, ep))
        return result


def run_multi_season_episode_tree(
    seasons_with_episodes: list[tuple[Season, list[Episode]]],
    *,
    title: str = "Saisons",
) -> list[tuple[Season, Episode]] | None:
    """Tree collapsible multi-saisons (synchrone, utilise asyncio.run())."""
    app = MultiSeasonEpisodeTree(seasons_with_episodes, title=title)
    app.run()
    return app.return_value


async def run_multi_season_episode_tree_async(
    seasons_with_episodes: list[tuple[Season, list[Episode]]],
    *,
    title: str = "Saisons",
) -> list[tuple[Season, Episode]] | None:
    """Tree collapsible multi-saisons (async, pour boucle asyncio déjà en cours).
    À utiliser depuis un flux async au lieu de run_multi_season_episode_tree.
    """
    app = MultiSeasonEpisodeTree(seasons_with_episodes, title=title)
    await app.run_async()
    return app.return_value
