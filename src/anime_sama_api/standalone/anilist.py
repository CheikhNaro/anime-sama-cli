# -*- coding: utf-8 -*-
"""Connexion AniList et import de l'historique (listes déjà vus / à regarder)."""

from __future__ import annotations

import json

from . import constants

# Requête GraphQL : profil connecté (validation du token)
VIEWER_QUERY = """
query {
  Viewer {
    id
    name
  }
}
"""

# Requête GraphQL : liste des médias (COMPLETED, CURRENT, PLANNING)
MEDIA_LIST_QUERY = """
query ($userId: Int, $status: MediaListStatus, $type: MediaType, $page: Int, $perPage: Int) {
  Page(perPage: $perPage, page: $page) {
    pageInfo { total currentPage hasNextPage }
    mediaList(userId: $userId, status: $status, type: $type) {
      progress
      status
      media {
        title { romaji english }
        episodes
      }
    }
  }
}
"""

# Recherche d'un animé par titre (pour mise à jour liste)
SEARCH_MEDIA_QUERY = """
query ($search: String, $type: MediaType) {
  Page(perPage: 10, page: 1) {
    media(search: $search, type: $type) {
      id
      title { romaji english }
      episodes
    }
  }
}
"""

# Mutation : ajouter / mettre à jour une entrée dans la liste
SAVE_LIST_ENTRY_MUTATION = """
mutation ($mediaId: Int, $progress: Int, $status: MediaListStatus) {
  SaveMediaListEntry(mediaId: $mediaId, progress: $progress, status: $status) {
    id
    mediaId
    progress
    status
  }
}
"""


def load_auth() -> dict | None:
    """Charge le token et le profil AniList depuis anilist_auth.json."""
    if not constants.ANILIST_AUTH_FILE.exists():
        return None
    try:
        with open(constants.ANILIST_AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("token"):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_auth(token: str, user_id: int, name: str) -> None:
    """Enregistre le token et le profil AniList."""
    constants.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(constants.ANILIST_AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump({"token": token, "user_id": user_id, "name": name}, f, indent=2, ensure_ascii=False)


def _graphql(query: str, variables: dict | None = None, token: str | None = None) -> dict | None:
    """Envoie une requête GraphQL à AniList."""
    try:
        import httpx
    except ImportError:
        return None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    try:
        r = httpx.post(constants.ANILIST_GRAPHQL_URL, json=payload, headers=headers, timeout=15.0)
        if r.status_code != 200:
            return None
        data = r.json()
        if "errors" in data and data["errors"]:
            return None
        return data
    except Exception:
        return None


def authenticate(token: str) -> dict | None:
    """
    Valide le token et retourne le profil Viewer {id, name} ou None.
    """
    result = _graphql(VIEWER_QUERY, token=token)
    if not result or "data" not in result or "Viewer" not in result["data"]:
        return None
    viewer = result["data"]["Viewer"]
    if not viewer or "id" not in viewer:
        return None
    return {"id": viewer["id"], "name": (viewer.get("name") or "").strip()}


def fetch_media_list(token: str, user_id: int, status: str, page: int = 1, per_page: int = 50) -> dict | None:
    """
    Récupère une page de la liste utilisateur (status = COMPLETED, CURRENT, PLANNING).
    Retourne { "entries": [...], "hasNextPage": bool } ou None.
    """
    result = _graphql(
        MEDIA_LIST_QUERY,
        variables={"userId": user_id, "status": status, "type": "ANIME", "page": page, "perPage": per_page},
        token=token,
    )
    if not result or "data" not in result or "Page" not in result["data"]:
        return None
    page_data = result["data"]["Page"]
    page_info = page_data.get("pageInfo") or {}
    entries = []
    for item in page_data.get("mediaList") or []:
        media = item.get("media") or {}
        title = (media.get("title") or {})
        name = (title.get("romaji") or title.get("english") or "").strip()
        if not name:
            continue
        progress = item.get("progress") or 0
        entries.append({"anime": name, "season": 1, "episode": progress or 1, "status": status})
    return {"entries": entries, "hasNextPage": page_info.get("hasNextPage") is True}


def fetch_all_media_list(token: str, user_id: int, status: str) -> list[dict]:
    """Récupère toute la liste (pagination) pour un statut donné."""
    out = []
    page = 1
    while True:
        data = fetch_media_list(token, user_id, status, page=page)
        if not data:
            break
        out.extend(data["entries"])
        if not data.get("hasNextPage"):
            break
        page += 1
    return out


def search_media_by_title(token: str, title: str) -> dict | None:
    """
    Recherche un animé par titre. Retourne le premier résultat { "id": int, "title": str, "episodes": int } ou None.
    """
    result = _graphql(
        SEARCH_MEDIA_QUERY,
        variables={"search": (title or "").strip(), "type": "ANIME"},
        token=token,
    )
    if not result or "data" not in result or "Page" not in result["data"]:
        return None
    media_list = (result["data"]["Page"] or {}).get("media") or []
    if not media_list:
        return None
    m = media_list[0]
    t = m.get("title") or {}
    name = (t.get("romaji") or t.get("english") or "").strip()
    return {"id": m.get("id"), "title": name, "episodes": m.get("episodes")}


def save_list_entry(token: str, media_id: int, progress: int, status: str = "COMPLETED") -> bool:
    """Met à jour ou ajoute une entrée dans la liste AniList (status: COMPLETED ou CURRENT)."""
    result = _graphql(
        SAVE_LIST_ENTRY_MUTATION,
        variables={"mediaId": media_id, "progress": progress, "status": status},
        token=token,
    )
    if not result or "data" not in result or "SaveMediaListEntry" not in result["data"]:
        return False
    return result["data"]["SaveMediaListEntry"] is not None


def push_local_to_anilist() -> tuple[bool, str]:
    """
    Envoie l'historique local vers AniList (chaque entrée est mise à jour sur la liste).
    Retourne (succès, message).
    """
    auth = load_auth()
    if not auth or not auth.get("token"):
        return False, "Non connecté à AniList. Lancez « anime-sama anilist login »."
    token = auth["token"]
    from . import history
    entries = history.load_history()
    if not entries:
        return False, "Aucun animé dans l'historique local."
    updated = 0
    failed = 0
    for e in entries:
        title = (e.get("anime") or "").strip()
        if not title:
            continue
        progress = max(1, int(e.get("episode") or 1))
        media = search_media_by_title(token, title)
        if not media or not media.get("id"):
            failed += 1
            continue
        # COMPLETED si on a vu au moins tout (ou on met la progression)
        status = "COMPLETED"
        if media.get("episodes") and progress < media["episodes"]:
            status = "CURRENT"
        if save_list_entry(token, media["id"], progress, status):
            updated += 1
        else:
            failed += 1
    if updated == 0 and failed > 0:
        return False, "Aucune entrée mise à jour (recherche ou API en échec)."
    # Rafraîchir l'historique AniList local (anilist_history.json) depuis AniList en ligne
    user_id = auth.get("user_id")
    if user_id is not None and import_anilist_to_local(token, user_id):
        pass  # anilist_history.json est à jour
    return True, f"{updated} entrée(s) mise(s) à jour sur AniList (en ligne et historique local)."


def load_anilist_history() -> list[dict]:
    """Charge l'historique importé depuis AniList (anilist_history.json)."""
    if not constants.ANILIST_HISTORY_FILE.exists():
        return []
    try:
        with open(constants.ANILIST_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_anilist_history(entries: list[dict]) -> None:
    """Sauvegarde l'historique AniList importé."""
    constants.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(constants.ANILIST_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def import_anilist_to_local(token: str, user_id: int) -> bool:
    """
    Importe les listes COMPLETED et CURRENT depuis AniList vers anilist_history.json.
    Retourne True si au moins une entrée a été importée.
    """
    entries = []
    for status in ("COMPLETED", "CURRENT"):
        entries.extend(fetch_all_media_list(token, user_id, status))
    if not entries:
        return False
    save_anilist_history(entries)
    return True


def login_flow() -> bool:
    """
    Prompt pour le token (et optionnellement le pseudo), validation, sauvegarde.
    Propose ensuite d'importer l'historique AniList.
    Retourne True si connexion réussie.
    """
    from . import terminal
    terminal.clear_screen()
    terminal.print_ascii_art()
    print(constants.BOLD + constants.CYAN + "  Connexion AniList" + constants.RESET)
    print(constants.GREEN + "  ─────────────────────────" + constants.RESET)
    print()
    print("  Saisissez votre pseudo puis le token (obtenu via le lien ci-dessous).")
    print(f"  Lien pour obtenir le token : {constants.ANILIST_OAUTH_URL}")
    print()
    try:
        username = (input(constants.CYAN + "  Ani-list username : " + constants.RESET) or "").strip()
        token = (input(constants.CYAN + "  Anilist token : " + constants.RESET) or "").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not token:
        print(constants.YELLOW + "  Aucun token saisi." + constants.RESET)
        return False
    profile = authenticate(token)
    if not profile:
        print(constants.RED + "  Connexion échouée. Vérifiez le token." + constants.RESET)
        return False
    save_auth(token, profile["id"], profile["name"])
    print(constants.GREEN + "  Connexion réussie" + constants.RESET + f" (connecté en tant que {profile['name']}).")
    print()
    try:
        do_import = (input(constants.CYAN + "  Importer l'historique AniList vers l'historique local ? (o/n) : " + constants.RESET) or "").strip().lower()
    except (EOFError, KeyboardInterrupt):
        do_import = "n"
    if do_import in ("o", "oui", "y", "yes"):
        if import_anilist_to_local(token, profile["id"]):
            print(constants.GREEN + "  Historique AniList importé." + constants.RESET)
        else:
            print(constants.YELLOW + "  Aucune entrée à importer ou erreur." + constants.RESET)
    return True
