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


def run_preview_cover(mapping_path: str, line: str) -> None:
    """Mode --preview-cover : télécharge/redimensionne la cover et l'affiche."""
    import base64
    import hashlib
    import tempfile
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
        if not image_url:
            return
    except (json.JSONDecodeError, OSError):
        return
    constants.COVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(image_url.encode()).hexdigest()[:16]
    cached = constants.COVER_CACHE_DIR / f"{key}_h{constants.COVER_MAX_HEIGHT}.png"
    if not cached.is_file():
        try:
            import urllib.request
            req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0 (compatible; anime-sama-cli)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
        except Exception:
            return
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
            else:
                return
        finally:
            try:
                os.unlink(tmp_in.name)
            except OSError:
                pass
    try:
        data = cached.read_bytes()
    except OSError:
        return
    b64 = base64.standard_b64encode(data).decode("ascii")
    sys.stdout.write(f"\033]1337;File=size={len(data)};width=213px;height={constants.COVER_MAX_HEIGHT}px;inline=1:{b64}\033\\")
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
    cmd = ["fzf", "--reverse", "--cycle", f"--prompt={prompt}", "--height=100%"]
    if multi:
        cmd.append("-m")
        cmd.append("--bind=space:toggle")
    map_path = None
    if catalogues_for_preview and _terminal_supports_images():
        try:
            import shlex
            import tempfile
            mapping = [
                {"name": (c.name or "").strip(), "url": full_cover_url(c)}
                for c in catalogues_for_preview
                if getattr(c, "image_url", None)
            ]
            if mapping:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
                    json.dump(mapping, tf, ensure_ascii=False)
                    map_path = tf.name
                script_path = constants.PREVIEW_SCRIPT_PATH or os.path.abspath(sys.argv[0])
                cmd.extend([
                    "--preview",
                    f"{shlex.quote(sys.executable)} {shlex.quote(script_path)} --preview-cover {shlex.quote(map_path)} {{}}",
                    "--preview-window=right:30%:wrap",
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
