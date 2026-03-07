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
