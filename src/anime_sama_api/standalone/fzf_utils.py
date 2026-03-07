# -*- coding: utf-8 -*-
"""Sélection fzf, preview des covers, vérification des dépendances."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any

from . import constants
from . import terminal


def check_fzf_version() -> bool:
    try:
        out = subprocess.run(
            ["fzf", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0:
            return False
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", out.stdout or out.stderr or "")
        if m:
            v = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return v >= constants.FZF_MIN_VERSION
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return False


def check_deps(player: str) -> None:
    """Vérifie fzf et le lecteur (mpv ou vlc)."""
    if not check_fzf_version():
        terminal.die(
            "fzf >= 0.53.0 est requis (recherche dynamique). "
            "Installez-le : sudo apt install fzf  ou  https://github.com/junegunn/fzf"
        )
    cmd = "mpv" if player.upper() == "MPV" else "vlc"
    try:
        subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        terminal.die(f"Le lecteur '{cmd}' est requis. Installez-le (ex: sudo apt install {cmd.lower()}).")


def _terminal_supports_images() -> bool:
    term = os.environ.get("TERM", "")
    program = os.environ.get("TERM_PROGRAM", "")
    if "kitty" in term or os.environ.get("KITTY_WINDOW_ID"):
        return True
    if "WezTerm" in program or "wezterm" in term:
        return True
    if "iTerm" in program or "iTerm.app" in program:
        return True
    return False


def full_cover_url(catalogue: Any) -> str:
    """URL complète de la cover (image_url peut être relative)."""
    url = getattr(catalogue, "image_url", "") or ""
    if url.startswith("http"):
        return url
    base = getattr(catalogue, "site_url", None) or constants.SITE_URL
    return (base.rstrip("/") + "/" + url.lstrip("/"))


def _fetch_page_info(page_url: str) -> dict[str, str]:
    """Récupère synopsis, genres et type depuis la page catalogue."""
    import html as html_module
    import urllib.request
    result = {"synopsis": "", "genre": "", "type": ""}
    if not page_url or not page_url.startswith("http"):
        return result
    try:
        req = urllib.request.Request(
            page_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; anime-sama-cli)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return result
    for synopsis_m in re.finditer(r"Synopsis[\W\w]+?>(.+?)<", html):
        raw = html_module.unescape(synopsis_m.group(1).strip())
        if raw and raw != "Synopsis" and len(raw) > 15:
            result["synopsis"] = raw
            break
    if not result["synopsis"]:
        synopsis_after = re.search(r"Synopsis\s*</[^>]+>\s*<[^>]+>(.+?)</[^>]+>", html, re.DOTALL)
        if synopsis_after:
            result["synopsis"] = html_module.unescape(synopsis_after.group(1).strip())
    genres_m = re.search(r"Genres[\W\w]+?>(.+?)<", html)
    if genres_m:
        result["genre"] = html_module.unescape(genres_m.group(1).strip())
    type_m = re.search(r"Types?[\W\w]+?>(.+?)<", html, re.IGNORECASE)
    if type_m:
        result["type"] = html_module.unescape(type_m.group(1).strip())
    return result


def _preview_width() -> int:
    """Largeur de la fenêtre de preview (fzf définit FZF_PREVIEW_COLUMNS)."""
    try:
        w = os.environ.get("FZF_PREVIEW_COLUMNS")
        if w:
            return max(20, int(w))
    except (ValueError, TypeError):
        pass
    try:
        import shutil
        return max(20, shutil.get_terminal_size((80, 24)).columns)
    except Exception:
        return 80


def run_preview_cover(mapping_path: str, line: str) -> None:
    """
    Preview façon viu : image en haut, puis séparateur sur toute la largeur,
    puis infos (Titre, Genre, Type, Synopsis) avec retours à la ligne.
    Utilise FZF_PREVIEW_COLUMNS pour la largeur (défini par fzf).
    """
    import base64
    import hashlib
    import tempfile
    import textwrap
    line = (line or "").strip()
    if not line or not os.path.isfile(mapping_path):
        return
    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        def _norm(s: str) -> str:
            return " ".join((s or "").strip().split())
        line_norm = _norm(line)
        entry = next((e for e in mapping if _norm(e.get("name") or "") == line_norm), None)
        if not entry:
            return
        image_url = entry.get("url", "").strip()
    except (json.JSONDecodeError, OSError):
        return

    width = _preview_width()

    if image_url:
        constants.COVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(image_url.encode()).hexdigest()[:16]
        cached = constants.COVER_CACHE_DIR / f"{key}_h{constants.COVER_MAX_HEIGHT}.png"
        if not cached.is_file():
            try:
                import urllib.request
                req = urllib.request.Request(
                    image_url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; anime-sama-cli)"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    raw = resp.read()
            except Exception:
                pass
            else:
                tmp_in = tempfile.NamedTemporaryFile(suffix=".img", delete=False)
                try:
                    tmp_in.write(raw)
                    tmp_in.close()
                    for convert_cmd in ("convert", "magick"):
                        result = subprocess.run(
                            [convert_cmd, tmp_in.name, "-resize", f"x{constants.COVER_MAX_HEIGHT}>", "-quality", "90", "png:-"],
                            capture_output=True,
                            timeout=5,
                        )
                        if result.returncode == 0 and result.stdout:
                            cached.write_bytes(result.stdout)
                            break
                finally:
                    try:
                        os.unlink(tmp_in.name)
                    except OSError:
                        pass
        if cached.is_file():
            try:
                data = cached.read_bytes()
                b64 = base64.standard_b64encode(data).decode("ascii")
                sys.stdout.write(f"\033]1337;File=size={len(data)};width=213px;height={constants.COVER_MAX_HEIGHT}px;inline=1:{b64}\033\\")
                sys.stdout.flush()
            except OSError:
                pass

    sys.stdout.write("\n")
    sep_line = "\033[90m" + "─" * width + "\033[0m\n"

    def sep() -> None:
        sys.stdout.write(sep_line)

    title = (entry.get("title") or entry.get("name") or "").strip()
    genre = (entry.get("genre") or "").strip()
    type_val = (entry.get("type") or "").strip()
    synopsis = (entry.get("synopsis") or "").strip()

    page_url = (entry.get("page_url") or "").strip()
    if page_url and (not synopsis or not genre or not type_val):
        info = _fetch_page_info(page_url)
        if not synopsis:
            synopsis = (info.get("synopsis") or "").strip()
        if not genre:
            genre = (info.get("genre") or "").strip()
        if not type_val:
            type_val = (info.get("type") or "").strip()

    def print_row(label: str, value: str) -> None:
        value = (value or "—").strip()
        value = " ".join(value.split())
        label_len = len(label)
        wrap_w = max(10, width - label_len - 2)
        lines = textwrap.wrap(value, width=wrap_w) if value else [""]
        if not lines:
            lines = [""]
        sys.stdout.write(constants.CYAN + label + "\033[0m " + lines[0] + "\n")
        for part in lines[1:]:
            sys.stdout.write(" " * (label_len + 1) + part + "\n")
        sep()

    sep()
    print_row("Titre : ", title)
    print_row("Genre : ", genre)
    print_row("Type : ", type_val)
    sys.stdout.write(constants.CYAN + "Synopsis :" + "\033[0m\n\n")
    if synopsis:
        synopsis_flat = " ".join(synopsis.split())
        for part in textwrap.wrap(synopsis_flat, width=width):
            sys.stdout.write(part + "\n")
    else:
        sys.stdout.write("—\n")
    sys.stdout.flush()


def fzf_select(
    items: list[str],
    prompt: str = "Choisir : ",
    multi: bool = False,
    catalogues_for_preview: list[Any] | None = None,
) -> str | list[str] | None:
    """Sélection via fzf. Si catalogues_for_preview, affiche la cover à droite."""
    if not items:
        return None
    if len(items) == 1 and not multi:
        return items[0]
    fzf_input = "\n".join(items)
    cmd = [
        "fzf", "--reverse", "--cycle", f"--prompt={prompt}", "--height=100%",
        "--bind=backspace:abort",
    ]
    if multi:
        cmd.append("-m")
        cmd.append("--bind=space:toggle")
    map_path = None
    if catalogues_for_preview:
        try:
            import shlex
            import tempfile
            mapping = []
            for c in catalogues_for_preview:
                name = (getattr(c, "name", None) or "").strip()
                if not name:
                    continue
                genres = getattr(c, "genres", None) or []
                categories = getattr(c, "categories", None)
                if hasattr(categories, "__iter__") and not isinstance(categories, str):
                    type_str = ", ".join(str(x) for x in categories)
                else:
                    type_str = str(categories or "")
                entry = {
                    "name": name,
                    "url": full_cover_url(c) if getattr(c, "image_url", None) else "",
                    "title": (getattr(c, "title", None) or getattr(c, "name", None) or "").strip(),
                    "genre": ", ".join(genres) if isinstance(genres, (list, tuple)) else str(genres or ""),
                    "type": type_str,
                    "page_url": (getattr(c, "page_url", None) or getattr(c, "url", "") or "").strip(),
                }
                mapping.append(entry)
            if mapping:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
                    json.dump(mapping, tf, ensure_ascii=False)
                    map_path = tf.name
                script_path = constants.PREVIEW_SCRIPT_PATH or os.path.abspath(sys.argv[0])
                preview_window = "--preview-window=right:40%:wrap"
                if not _terminal_supports_images():
                    preview_window = "--preview-window=right:50%:wrap"
                cmd.extend([
                    "--preview",
                    f"{shlex.quote(sys.executable)} {shlex.quote(script_path)} --preview-cover {shlex.quote(map_path)} {{}}",
                    preview_window,
                ])
        except Exception:
            map_path = None
    try:
        result = subprocess.run(cmd, input=fzf_input, text=True, capture_output=True, timeout=300)
        if map_path and os.path.isfile(map_path):
            try:
                os.unlink(map_path)
            except OSError:
                pass
        if result.returncode != 0:
            return None
        out = (result.stdout or "").strip()
        if multi:
            return [s for s in out.split("\n") if s] if out else []
        return out
    except (FileNotFoundError, subprocess.TimeoutExpired):
        if map_path and os.path.isfile(map_path):
            try:
                os.unlink(map_path)
            except OSError:
                pass
        return None
