import asyncio
import logging
import re
from collections.abc import AsyncIterator, Generator
from dataclasses import dataclass
from html import unescape
from typing import Any, cast

from httpx import AsyncClient

from .catalogue import Catalogue, Category
from .episode import Episode
from .langs import Lang, flags
from .season import Season
from .utils import filter_literal, is_Literal

logger = logging.getLogger(__name__)


async def find_site_url(
    client: AsyncClient | None = None, provider_url="https://anime-sama.pw/"
) -> str | None:
    client = client or AsyncClient()

    response = await client.get(provider_url)

    if response.is_error:
        return None

    # * Sometimes need to check for the great word "anime-sama" in lowercase or uppercase but if add re.IGNORECASE it will work
    match = re.search(
        r"href=\"(.+?)\">Accéder à Anime-Sama", response.text, re.IGNORECASE
    )

    # * Ajouter un suive de redirection d'url au match au cas ou le site n'est pas a jour et redirige vers une autre url, puis garder l'url finale

    if match:
        redirected = await client.get(match.group(1), follow_redirects=False)
        return (
            redirected.headers["location"] + "/"
            if redirected.has_redirect_location
            else match.group(1)
        )


@dataclass(frozen=True)
class PlanningEntry:
    """Une entrée du planning (anime ou scan) avec titre, type, heure et langue."""

    title: str
    kind: str  # "Anime" | "Scans"
    time: str  # ex. "15h00" ou ""
    lang: str  # "VOSTFR" | "VF" | "VJ"
    url: str

    def display_line(self) -> str:
        time_part = f" {self.time}" if self.time else ""
        return f"{self.title} — {self.kind} {self.lang}{time_part}"


@dataclass(frozen=True)
class PlanningDay:
    """Un jour du planning avec sa date et la liste des sorties."""

    day_name: str  # Lundi, Mardi, ...
    date: str  # ex. "02/03"
    entries: tuple[PlanningEntry, ...]


@dataclass(frozen=True)
class EpisodeRelease:
    page_url: str
    image_url: str
    serie_name: str
    categories: tuple[Category]
    language: Lang
    descriptive: str

    def get_real_episodes(self) -> list[Episode]:
        raise NotImplementedError

    @property
    def fancy_name(self) -> str:
        return f"{self.serie_name} - {self.descriptive} {flags.get(self.language, '')}"


class AnimeSama:
    def __init__(self, site_url: str, client: AsyncClient | None = None) -> None:
        self.site_url = site_url
        self.client = client or AsyncClient()

    async def _get_homepage_section(self, section_name: str, how_many: int = 1) -> str:
        homepage = await self.client.get(self.site_url)

        if homepage.is_error:
            return ""

        sections = homepage.text.split("<!--")
        for index, section in enumerate(sections):
            comment_end_pos = section.find("-->")
            if section_name in section[:comment_end_pos]:
                return "<!--" + "<!--".join(sections[index : index + how_many])

        return ""

    def _yield_catalogues_from(self, html: str) -> Generator[Catalogue]:
        text_without_script = re.sub(r"<script[\W\w]+?</script>", "", html)
        for match in re.finditer(
            rf"href=\"({self.site_url}catalogue/.+)\"[\W\w]+?src=\"(.+?)\"[\W\w]+?<h2.+?>(.*)\n?<[\W\w]+?<p.+?>(.*)\n?<[\W\w]+?<p.+?>(.*)\n?<[\W\w]+?<p.+?>(.*)\n?<[\W\w]+?<p.+?>(.*)\n?<",
            text_without_script,
        ):
            (
                url,
                image_url,
                name,
                alternative_names_str,
                genres_str,
                categories_str,
                languages_str,
            ) = (unescape(item) for item in match.groups())

            alternative_names = (
                alternative_names_str.split(", ") if alternative_names_str else []
            )
            if " - " in genres_str:
                genres = genres_str.split(" - ")
            else:
                genres = genres_str.split(", ") if genres_str else []
            categories = categories_str.split(", ") if categories_str else []
            languages = languages_str.split(", ") if languages_str else []

            # Normaliser les variantes du site (anime-sama utilise parfois des libellés incorrects)
            _category_fix = {"Autre": "Autres", "Animes": "Anime", "Films": "Film"}
            categories = [_category_fix.get(c.strip(), c.strip()) for c in categories if c.strip()]

            def not_in_literal(value: Any) -> None:
                logger.warning(
                    "Erreur lors du parsing de « %s ». Signaler avec l'URL : %s", value, url
                )

            categories_checked = cast(
                set[Category], set(filter_literal(categories, Category, not_in_literal))
            )
            # Ne pas logger pour les langues : le site peut mettre "Scans" dans les langues (ex. Watamote)
            languages_checked = cast(
                set[Lang], set(filter_literal(languages, Lang, lambda _: None))
            )

            yield Catalogue(
                url=url,
                name=name,
                alternative_names=alternative_names,
                genres=genres,
                categories=categories_checked,
                languages=languages_checked,
                image_url=image_url,
                client=self.client,
            )

    def _yield_release_episodes_from(self, html: str) -> Generator[EpisodeRelease]:
        for match in re.finditer(
            rf"href=\"({self.site_url}catalogue/.+)\"[\W\w]+?src=\"(.+?)\"[\W\w]+?>(.*)\n?<[\W\w]+?>(.*)\n?<[\W\w]+?>(.*)\n?<[\W\w]+?>(.*)\n?<",
            html,
        ):
            (
                season_url,
                image_url,
                serie_name,
                categories,
                language,
                descriptive,
            ) = match.groups()
            categories = categories.split(", ") if categories else ["Anime"]
            _category_fix = {"Autre": "Autres", "Animes": "Anime", "Films": "Film"}
            categories = [_category_fix.get(c.strip(), c.strip()) for c in categories if c.strip()]
            language = language.strip() if language else "VOSTFR"

            def not_in_literal(value: Any) -> None:
                logger.warning(
                    "Erreur lors du parsing de « %s » (accueil). URL : %s", value, season_url
                )

            categories_checked = cast(
                tuple[Category],
                tuple(filter_literal(categories, Category, not_in_literal)),
            )
            is_Literal(language, Lang, not_in_literal)

            yield EpisodeRelease(
                page_url=season_url,
                image_url=image_url,
                serie_name=serie_name,
                categories=categories_checked,
                language=cast(Lang, language),
                descriptive=descriptive,
            )

    async def search(self, query: str) -> list[Catalogue]:
        response = (
            await self.client.get(f"{self.site_url}catalogue/?search={query}")
        ).raise_for_status()

        pages_regex = re.findall(r"page=(\d+)", response.text)

        if not pages_regex:
            last_page = 1
        else:
            last_page = int(pages_regex[-1])

        responses = [response] + await asyncio.gather(
            *(
                self.client.get(f"{self.site_url}catalogue/?search={query}&page={num}")
                for num in range(2, last_page + 1)
            )
        )

        catalogues = []
        for response in responses:
            if response.is_error:
                continue

            catalogues += list(self._yield_catalogues_from(response.text))

        return catalogues

    async def search_iter(self, query: str) -> AsyncIterator[Catalogue]:
        response = (
            await self.client.get(f"{self.site_url}catalogue/?search={query}")
        ).raise_for_status()

        pages_regex = re.findall(r"page=(\d+)", response.text)

        if not pages_regex:
            raise StopAsyncIteration

        last_page = int(pages_regex[-1])

        for catalogue in self._yield_catalogues_from(response.text):
            yield catalogue

        for number in range(2, last_page + 1):
            response = await self.client.get(
                f"{self.site_url}catalogue/?search={query}&page={number}"
            )

            if response.is_error:
                continue

            for catalogue in self._yield_catalogues_from(response.text):
                yield catalogue

    async def catalogues_iter(self) -> AsyncIterator[Catalogue]:
        async for catalogue in self.search_iter(""):
            yield catalogue

    async def all_catalogues(self) -> list[Catalogue]:
        return await self.search("")

    def _parse_planning(self, html: str) -> list[PlanningDay]:
        """Parse la page planning et retourne la liste des jours avec leurs entrées."""
        text = re.sub(r"<script[\W\w]+?</script>", "", html)
        base_url = self.site_url.rstrip("/")
        days_order = (
            "Lundi",
            "Mardi",
            "Mercredi",
            "Jeudi",
            "Vendredi",
            "Samedi",
            "Dimanche",
        )
        result: list[PlanningDay] = []

        # Trouver les sections par jour : <h2 ...>Lundi</h2> etc.
        day_pattern = re.compile(
            r'<h2[^>]*titreJours[^>]*>\s*('
            + "|".join(re.escape(d) for d in days_order)
            + r')\s*</h2>',
            re.IGNORECASE,
        )
        day_matches = list(day_pattern.finditer(text))

        for i, day_match in enumerate(day_matches):
            day_name = day_match.group(1).strip()
            start = day_match.end()
            end = day_matches[i + 1].start() if i + 1 < len(day_matches) else len(text)
            section = text[start:end]

            # Date du jour (DD/MM)
            date_match = re.search(r"(\d{1,2}/\d{1,2})", section)
            date_str = date_match.group(1) if date_match else ""

            # Cartes : uniquement Anime (pas les Scans)
            card_pattern = re.compile(
                r'<div[^>]*\b(Anime|Scans)\s+(VOSTFR|VF|VJ)[^>]*\bplanning-card\b'
                r'[^>]*data-title="([^"]*)"[^>]*>'
                r'[\s\S]*?href="(/catalogue/[^"]+)"'
                r'[\s\S]*?card-title[^>]*>([^<]+)'
                r'(?:[\s\S]*?info-text[^>]*>([^<]+))?',
                re.IGNORECASE,
            )
            entries_list: list[PlanningEntry] = []
            for card in card_pattern.finditer(section):
                kind, lang, _data_title, path, title, time_str = card.groups()
                if (kind or "").strip().lower() != "anime":
                    continue
                title = unescape(title).strip() if title else ""
                time_str = (time_str or "").strip()
                full_url = path if path.startswith("http") else base_url + path
                entries_list.append(
                    PlanningEntry(
                        title=title,
                        kind="Anime",
                        time=time_str,
                        lang=lang or "VOSTFR",
                        url=full_url,
                    )
                )
            result.append(
                PlanningDay(
                    day_name=day_name,
                    date=date_str,
                    entries=tuple(entries_list),
                )
            )
        return result

    async def planning(self) -> list[PlanningDay]:
        """Récupère le planning des sorties depuis la page planning du site."""
        response = await self.client.get(f"{self.site_url}planning/")
        if response.is_error:
            return []
        return self._parse_planning(response.text)

    async def new_episodes(self) -> list[EpisodeRelease]:
        """
        Return the new available episodes on anime-sama using the homepage sorted from oldest to newest.
        """
        section = await self._get_homepage_section("ajouts animes", 4)
        release_episodes = list(self._yield_release_episodes_from(section))
        return list(reversed(release_episodes))

    """async def new_scans(self) -> list[Scan]:
        raise NotImplementedError"""

    async def new_content(self) -> list[Catalogue]:
        raise NotImplementedError

    async def classics(self) -> list[Catalogue]:
        raise NotImplementedError

    async def highlights(self) -> list[Catalogue]:
        raise NotImplementedError
