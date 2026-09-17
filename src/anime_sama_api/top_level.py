import asyncio
import logging
import re
from collections.abc import AsyncIterator, Generator
from dataclasses import dataclass
from typing import Any, cast

from httpx import AsyncClient
from scrapling.parser import Selector

from .catalogue import Catalogue, Category
from .episode import Episode
from .langs import Lang, flags
from .utils import filter_literal, is_Literal

logger = logging.getLogger(__name__)


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

        for card in page.css(".catalog-card"):
            # URL
            a_tag = card.css("a")
            if not a_tag:
                continue
            url = a_tag[0].attrib.get("href", "")
            if not url:
                continue

            # Image
            img = card.css("img")
            image_url = img[0].attrib.get("src", "") if img else ""

            # Nom principal
            title_el = card.css(".card-title")
            name = title_el[0].text.clean() if title_el and title_el[0].text else ""

            # Noms alternatifs
            alt_el = card.find("p", class_="alternate-titles")
            if alt_el and alt_el.text:
                alt_names_raw = alt_el.text.clean()
                alternative_names = [a.strip() for a in alt_names_raw.split(",") if a.strip()]
            else:
                alternative_names = []

            # Info rows (genres, catégories, langues)
            genres: list[str] = []
            categories: list[str] = []
            languages: list[str] = []

            for row in card.css(".info-row"):
                label_el = row.css(".info-label")
                if not label_el:
                    continue
                label_text = label_el[0].text.clean() if label_el[0].text else ""

                if "Genres" in label_text:
                    genres = [
                        tag.text.clean()
                        for tag in row.css(".genre-tag")
                        if tag.text and tag.text.clean()
                    ]
                elif re.search(r"Types?", label_text, re.IGNORECASE):
                    val_el = row.css(".info-value")
                    for val in val_el:
                        raw = val.text.clean() if val.text else ""
                        parts = [v.strip() for v in raw.split(",") if v.strip()]
                        categories.extend(parts)
                elif "Langues" in label_text:
                    for flag_el in row.css(".lang-flag"):
                        title_attr = flag_el.attrib.get("title", "")
                        lang = self._flag_title_to_lang(title_attr)
                        if lang:
                            languages.append(lang)

            _category_fix = {"Autre": "Autres", "Animes": "Anime", "Films": "Film"}
            categories = [_category_fix.get(c.strip(), c.strip()) for c in categories if c.strip()]

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

    @staticmethod
    def _flag_title_to_lang(title: str) -> str | None:
        from .langs import flagid2lang
        return flagid2lang.get(title.strip().lower())

    def _yield_release_episodes_from(self, html: str) -> Generator[EpisodeRelease]:
        page = Selector(content=html)

        for card in page.css(".anime-card-premium"):
            a_tag = card.css("a")
            if not a_tag:
                continue
            season_url = a_tag[0].attrib.get("href", "")
            if not season_url:
                continue

            img = card.css("img")
            image_url = img[0].attrib.get("src", "") if img else ""
            serie_name = img[0].attrib.get("alt", "").strip() if img else ""

            # Badge de catégorie
            badge_els = card.css(".badge-text")
            category_raw = badge_els[0].text.clean() if badge_els and badge_els[0].text else "Anime"

            # Badge de langue (language-badge-top)
            lang_badge = card.css(".language-badge-top .badge-text")
            language = lang_badge[0].text.clean() if lang_badge and lang_badge[0].text else "VOSTFR"

            # Texte d'info (descriptif de l'épisode)
            info_el = card.css(".info-text")
            descriptive = info_el[0].text.clean() if info_el and info_el[0].text else ""

            categories = [category_raw]
            _category_fix = {"Autre": "Autres", "Animes": "Anime", "Films": "Film"}
            categories = [_category_fix.get(c.strip(), c.strip()) for c in categories if c.strip()]

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
        page = Selector(content=html)
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

        # Trouver les h2 de jours de la semaine (class contenant "titreJours")
        day_headers = page.css("h2.titreJours") or page.find_all("h2", class_="titreJours")

        for header in day_headers:
            day_name_raw = header.text.clean() if header.text else ""
            day_name = day_name_raw.strip()

            if day_name not in days_order:
                continue

            # Date du jour : chercher dans le parent/section suivante
            # On récupère le texte suivant (DD/MM) proche du h2
            date_str = ""
            parent = header.parent
            if parent:
                date_match = re.search(r"(\d{1,2}/\d{1,2})", parent.text.clean() if parent.text else "")
                if date_match:
                    date_str = date_match.group(1)

            # Cartes de planning dans la section du jour
            # Les cartes se trouvent généralement dans un container après le h2
            entries_list: list[PlanningEntry] = []
            section_parent = header.parent or page

            for card in section_parent.css(".planning-card"):
                # Extraire classe kind (Anime/Scans) et lang (VOSTFR/VF/VJ) depuis les classes
                card_classes = card.attrib.get("class", "")
                kind_match = re.search(r"\b(Anime|Scans)\b", card_classes, re.IGNORECASE)
                lang_match = re.search(r"\b(VOSTFR|VF|VJ)\b", card_classes, re.IGNORECASE)

                kind = kind_match.group(1).capitalize() if kind_match else ""
                lang = lang_match.group(1).upper() if lang_match else "VOSTFR"

                if kind.lower() != "anime":
                    continue

                # URL
                link_el = card.css("a")
                if not link_el:
                    continue
                path = link_el[0].attrib.get("href", "")
                full_url = path if path.startswith("http") else base_url + path

                # Titre
                title_el = card.css(".card-title")
                title = title_el[0].text.clean() if title_el and title_el[0].text else ""

                # Heure
                time_el = card.css(".info-text")
                time_str = time_el[0].text.clean() if time_el and time_el[0].text else ""

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
