# -*- coding: utf-8 -*-
"""
anime-sama CLI - Regarder ou télécharger des animés depuis anime-sama.to

Point d'entrée conservé pour compatibilité (pyproject.scripts). La logique
est factorisée dans le package anime_sama_api.standalone.
"""

from __future__ import annotations

import os

# Pour que la preview fzf appelle ce script avec --preview-cover
from anime_sama_api.standalone import constants as _constants
_constants.PREVIEW_SCRIPT_PATH = os.path.abspath(__file__)

from anime_sama_api.standalone import main

if __name__ == "__main__":
    main()
