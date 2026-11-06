import asyncio
import html
import logging
import re
from collections.abc import AsyncIterator, Generator
from dataclasses import dataclass
from typing import Any, cast, get_args

from httpx import AsyncClient
from scrapling.parser import Selector

from .catalogue import Catalogue, Category
from .episode import Episode
from .langs import Lang, flags
from .utils import filter_literal, is_Literal

logger = logging.getLogger(__name__)


def _own_text(node) -> str:
    """Le texte d'une balise sans ses descendants (Selector.text ne retourne que les enfants directs)."""
    return html.unescape("".join(t.text or "" for t in node.xpath("text()"))).strip()


def _badge_to_category(badge: str) -> str:
    return {
        "Anime": "Anime",
        "Animes": "Anime",
        "Scans": "Scans",
        "Scan": "Scans",
        "Manga": "Scans",
        "Webtoon": "Scans",
        "Film": "Film",
        "Films": "Film",
        "Autre": "Autres",
    }.get(badge.strip(), badge.strip())


def _title_to_lang(title: str) -> str | None:
    from .langs import FlagId, Lang, flagid2lang

    key = title.strip().upper()
    if key in get_args(Lang):
        return key
    return flagid2lang.get(cast(FlagId, title.strip().lower())) if title else None


async def find_site_url(
    client: AsyncClient | None = None, provider_url="https://anime-sama.pw/"
) -> str | None:
    client = client or AsyncClient()

    response = await client.get(provider_url)

    if response.is_error:
        return None

    page = Selector(content=response.text, url=provider_url)

    # * Sometimes need to check for the great word "anime-sama" in lowercase or uppercase
    link = page.find("a", re.compile(r"Accéder à Anime-Sama", re.IGNORECASE))
    if link is None:
        return None

    href = link.attrib.get("href", "")
    if not href:
        return None

    # * Ajouter un suivi de redirection d'url au match au cas où le site n'est pas à jour
    redirected = await client.get(href, follow_redirects=False)
    return (
        redirected.headers["location"] + "/"
        if redirected.has_redirect_location
        else href
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
        page = Selector(content=html)

        for card in page.css(".as-carte-oeuvre"):
            # URL
            a_tag = card.css(".as-carte-lien") or card.css("a")
            if not a_tag:
                continue
            url = self.client_url(a_tag[0].attrib.get("href", ""))
            if not url:
                continue

            # Image
            img = card.css("img")
            image_url = img[0].attrib.get("src", "") if img else ""

            # Nom principal
            title_el = card.css(".as-carte-titre")
            name = _own_text(title_el[0]) if title_el else ""
            if not name:
                name = card.attrib.get("data-nom", "").strip()

            # Noms alternatifs : plus affichés sur les cartes du catalogue
            alternative_names: list[str] = []

            # Badges de catégorie et drapeaux de langue
            genres: list[str] = []
            categories: list[str] = []
            languages: list[str] = []

            for badge in card.css(".as-badge"):
                label = _own_text(badge)
                if label:
                    categories.append(_badge_to_category(label))

            for flag_el in card.css(".as-drapeau img"):
                lang = _title_to_lang(flag_el.attrib.get("title", ""))
                if lang:
                    languages.append(lang)

            def not_in_literal(value: Any) -> None:
                logger.warning(
                    "Erreur lors du parsing de « %s ». Signaler avec l'URL : %s", value, url
                )

            categories_checked = cast(
                set[Category], set(filter_literal(categories, Category, not_in_literal))
            )
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

    def client_url(self, url: str) -> str:
        """Rend absolute une URL du site (les nouvelles cartes utilisent des chemins relatifs)."""
        if not url:
            return ""
        if url.startswith(("http://", "https://")):
            return url
        return self.site_url.rstrip("/") + "/" + url.lstrip("/")

    def _yield_release_episodes_from(self, html: str) -> Generator[EpisodeRelease]:
        page = Selector(content=html)

        for card in page.css(".as-carte-anime:not(.planning-card)"):
            a_tag = card.css(".as-carte-lien") or card.css("a")
            if not a_tag:
                continue
            season_url = self.client_url(a_tag[0].attrib.get("href", ""))
            if not season_url:
                continue

            # Image + nom de la série
            img = card.css(".as-carte-image img") or card.css("img")
            image_url = img[0].attrib.get("src", "") if img else ""

            title_el = card.css(".as-carte-titre")
            serie_name = _own_text(title_el[0]) if title_el else ""
            if not serie_name:
                serie_name = card.attrib.get("data-nom", "").strip()

            # Catégorie (Anime/Scans) puis langue (drapeau ou classes de la carte)
            badge_els = card.css(".as-badge")
            category_raw = _own_text(badge_els[0]) if badge_els else "Anime"

            flags = card.css(".as-drapeau img")
            language = (
                _title_to_lang(flags[0].attrib.get("title", "")) if flags else None
            ) or "VOSTFR"

            # Descriptif de l'épisode ( premier span de as-carte-info )
            info_spans = card.css(".as-carte-info span:not(.as-carte-temps)")
            descriptive = _own_text(info_spans[0]) if info_spans else ""

            categories = [_badge_to_category(category_raw)]

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
            last_page = int(max(pages_regex))

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
            return

        last_page = int(max(pages_regex))

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
        page = Selector(content=html)
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

        for header in page.css("h2.titreJours"):
            day_name = _own_text(header)

            if day_name not in days_order:
                continue

            parent = header.parent
            if parent is None:
                continue

            # La date (DD/MM) est le <p> qui suit immédiatement le titre du jour
            date_str = ""
            date_match = re.search(r"(\d{1,2}/\d{1,2})", parent.get_all_text())
            if date_match:
                date_str = date_match.group(1)

            entries_list: list[PlanningEntry] = []
            for card in parent.css(".planning-card"):
                # Les classes de la carte portent le type et la langue :
                # class="as-carte as-carte-anime planning-card Anime VOSTFR pl-sorti"
                card_classes = card.attrib.get("class", "").split()
                kind = next(
                    (k.capitalize() for k in card_classes if k.lower() in ("anime", "scans")),
                    "",
                )
                lang = next(
                    (k.upper() for k in card_classes if k.upper() in get_args(Lang)),
                    "VOSTFR",
                )

                if kind.lower() != "anime":
                    continue

                link_el = card.css(".as-carte-lien") or card.css("a")
                if not link_el:
                    continue
                full_url = self.client_url(link_el[0].attrib.get("href", ""))

                title_el = card.css(".as-carte-titre")
                title = _own_text(title_el[0]) if title_el else card.attrib.get("data-nom", "")

                time_el = card.css(".as-carte-temps")
                time_str = _own_text(time_el[0]) if time_el else ""

                entries_list.append(
                    PlanningEntry(
                        title=title,
                        kind="Anime",
                        time=time_str,
                        lang=lang,
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
        """Récupère le planning de la semaine depuis la page planning du site."""
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
