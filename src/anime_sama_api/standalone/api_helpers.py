# -*- coding: utf-8 -*-
"""Helpers API : client HTTP et récupération catalogues / recherche."""

from __future__ import annotations

from . import constants


def get_client():
    from httpx import AsyncClient
    return AsyncClient()


async def get_catalogues(query: str = ""):
    from anime_sama_api import AnimeSama
    client = get_client()
    api = AnimeSama(constants.SITE_URL, client=client)
    if query.strip():
        return await api.search(query.strip())
    return await api.all_catalogues()


async def search_catalogues(query: str):
    from anime_sama_api import AnimeSama
    client = get_client()
    api = AnimeSama(constants.SITE_URL, client=client)
    return await api.search(query.strip())


async def get_catalogue_for_planning_entry(anime_name: str):
    """
    Récupère les infos réelles d'un animé depuis le site (page catalogue)
    à partir de son nom (ex. "Jujutsu Kaisen" -> https://anime-sama.to/catalogue/jujutsu-kaisen/).
    Utilisé pour afficher la preview du planning comme celle du catalogue.
    Retourne un objet catalogue (avec name, url, image_url, genres, categories) ou None.
    """
    if not (anime_name or "").strip():
        return None
    try:
        catalogues = await search_catalogues((anime_name or "").strip())
        return catalogues[0] if catalogues else None
    except Exception:
        return None
