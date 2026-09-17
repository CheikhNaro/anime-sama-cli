import re
from collections.abc import Sequence
from typing import Any, Literal, cast

from httpx import AsyncClient
from scrapling.parser import Selector

from .langs import Lang, flags
from .season import Season
from .utils import remove_some_js_comments

# Oversight from anime-sama that we should handle
# 'Animes' instead of 'Anime' seen in Cyberpunk: Edgerunners and Valkyrie Apocalypse
# 'Autre' instead of 'Autres' seen in Hazbin Hotel
# 'Scans' is in the language section for Watamote (harder to handle)
Category = Literal["Anime", "Scans", "Film", "Autres"]


class Catalogue:
    def __init__(
        self,
        url: str,
        name: str = "",
        alternative_names: Sequence[str] | None = None,
        genres: Sequence[str] | None = None,
        categories: set[Category] | None = None,
        languages: set[Lang] | None = None,
        image_url: str = "",
        client: AsyncClient | None = None,
    ) -> None:
        if alternative_names is None:
            alternative_names = []
        if genres is None:
            genres = []
        if categories is None:
            categories = set()
        if languages is None:
            languages = set()

        self.url = url + "/" if url[-1] != "/" else url
        self.site_url = "/".join(url.split("/")[:3]) + "/"
        self.client = client or AsyncClient()

        self.name = name or url.split("/")[-2]

        self._page: str | None = None
        self.alternative_names = alternative_names
        self.genres = genres
        self.categories = categories
        self.languages = languages
        self.image_url = image_url

    async def page(self) -> str:
        if self._page is not None:
            return self._page

        response = await self.client.get(self.url)

        if response.is_error:
            self._page = ""
        else:
            self._page = response.text

        return self._page

    async def seasons(self) -> list[Season]:
        html = await self.page()
        page = Selector(content=html)

        # Les données de saisons sont dans des balises <script> sous forme d'appels JS :
        # panneauAnime("Saison 1", "saison1/vostfr");
        # On extrait le contenu de tous les scripts puis on applique la regex JS.
        scripts_text = " ".join(
            script.text.clean() if script.text else ""
            for script in page.css("script")
        )
        scripts_without_comments = remove_some_js_comments(scripts_text)

        # Insensible à la casse pour VOSTFR/Vf (ex. Berserk, pages avec VOSTFR en majuscules)
        seasons = re.findall(
            r'panneauAnime\("(.+?)", *"(.+?)(?:vostfr|vf)"\);',
            scripts_without_comments,
            re.IGNORECASE,
        )

        seasons = [
            Season(
                url=self.url + link,
                name=name,
                serie_name=self.name,
                client=self.client,
            )
            for name, link in seasons
        ]

        return seasons

    async def advancement(self) -> str:
        html = await self.page()
        page = Selector(content=html)

        # Chercher la section "Actualité" dans les info-rows
        for row in page.css(".info-row"):
            label_el = row.css(".info-label")
            if not label_el:
                continue
            label_text = label_el[0].text.clean() if label_el[0].text else ""
            if "Actualit" in label_text:
                val_el = row.css(".info-val")
                if val_el and val_el[0].text:
                    return val_el[0].text.clean()
                # Fallback : tout le texte de la row hors label
                val_el2 = row.css("[class*='info-val']")
                if val_el2 and val_el2[0].text:
                    return val_el2[0].text.clean()

        return ""

    async def correspondence(self) -> str:
        html = await self.page()
        page = Selector(content=html)

        # Chercher la section "Correspondance" dans les info-rows
        for row in page.css(".info-row"):
            label_el = row.css(".info-label")
            if not label_el:
                continue
            label_text = label_el[0].text.clean() if label_el[0].text else ""
            if "Correspondance" in label_text:
                val_el = row.css(".info-val")
                if val_el and val_el[0].text:
                    return val_el[0].text.clean()
                val_el2 = row.css("[class*='info-val']")
                if val_el2 and val_el2[0].text:
                    return val_el2[0].text.clean()

        return ""

    async def synopsis(self) -> str:
        html = await self.page()
        page = Selector(content=html)

        # Synopsis dans l'élément #synopsisText
        synopsis_el = page.css("#synopsisText")
        if synopsis_el and synopsis_el[0].text:
            return synopsis_el[0].text.clean()

        # Fallback : chercher le paragraphe après le h2 Synopsis
        h2_list = page.find_all("h2", re.compile(r"Synopsis", re.IGNORECASE))
        if h2_list:
            # Chercher le premier <p> frère ou descendant suivant
            parent = h2_list[0].parent
            if parent:
                p_els = parent.css("p")
                if p_els and p_els[0].text:
                    return p_els[0].text.clean()

        return ""

    async def is_mature(self) -> bool:
        """Return True if the catalogue contain a warning about adult content"""
        html = await self.page()
        page = Selector(content=html)

        # Chercher une div avec classe contenant "yellow" et le texte "public averti"
        for div in page.css("div[class*='yellow']"):
            text = div.text.clean() if div.text else ""
            if "public averti" in text.lower():
                return True

        return False

    @property
    def is_anime(self) -> bool:
        return "Anime" in self.categories

    @property
    def is_manga(self) -> bool:
        return "Scans" in self.categories

    @property
    def is_film(self) -> bool:
        return "Film" in self.categories

    @property
    def is_other(self) -> bool:
        return "Autres" in self.categories

    @property
    def fancy_name(self) -> str:
        names = [""] + list(self.alternative_names) if self.alternative_names else []
        return f"{self.name}[bright_black]{' - '.join(names)} {' '.join(flags[lang] for lang in self.languages if lang != 'VOSTFR')}"

    def __repr__(self) -> str:
        return f"Catalogue({self.url!r}, {self.name!r})"

    def __str__(self) -> str:
        return self.fancy_name

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, Catalogue):
            return False
        return self.url == value.url

    def __hash__(self) -> int:
        return hash(self.url + self.name + "".join(self.alternative_names))
