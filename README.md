# Anime-Sama-cli
Regarder ou télécharger vos animés en VF/VOSTFR depuis votre terminal.

## Structure du projet

```
anime-sama-cli/
├── src/
│   └── anime_sama_api/    # Package Python (API + CLI)
├── tests/                 # Tests unitaires
├── examples/              # Exemples d’utilisation
├── scripts/               # Scripts utilitaires (ex. debug)
├── anisama-cli            # Point d’entrée principal (à lancer ou lier dans ~/.local/bin)
├── pyproject.toml
└── README.md
```



https://github.com/user-attachments/assets/f10d82de-1a6d-47ea-b43e-a91fd9e10ed3



---

## Dépendances requises

- **Python 3.10+**
- **fzf** (≥ 0.53)
- **MPV** ou **VLC**
- **yt-dlp** (téléchargements et lecture)
- *Optionnel* : **ImageMagick** (preview fzf + netteté des covers)

### Qualité des images (covers)

Les images sont redimensionnées puis **renforcées en netteté** (UnsharpMask / `-unsharp`) pour limiter le flou, quel que soit le terminal. Pour aller plus loin, vous pouvez upscaler vous‑même les images du cache avec un outil IA (le résultat sera utilisé au prochain affichage) :

- **Real-ESRGAN** (anime, très bon) : [github.com/xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- **waifu2x** (style anime) : [github.com/nagadomi/waifu2x](https://github.com/nagadomi/waifu2x)
- **Upscayl** (interface graphique) : [upscayl.org](https://upscayl.org)

Cache des covers : `~/.cache/anime-sama-cli/covers/` (supprimer le dossier pour régénérer après upscale manuel).

### Installation des dépendances

**Debian / Ubuntu (apt)**

```bash
sudo apt update
sudo apt install python3 python3-pip fzf mpv yt-dlp
# ou VLC à la place de mpv :
# sudo apt install vlc
```

**Arch (pacman)**

```bash
sudo pacman -S python python-pip fzf mpv yt-dlp
# ou vlc
```

**Fedora / RHEL (dnf)**

```bash
sudo dnf install python3 python3-pip fzf mpv yt-dlp
# ou vlc
```

---

## Installation

### Via pip (PyPI)

Une fois le paquet publié sur [PyPI](https://pypi.org/), vous pourrez installer avec :

```bash
pip install anime-sama-cli
```

La commande `anime-sama-cli` sera alors disponible (ajoutez `~/.local/bin` à votre `PATH` si nécessaire).

### Depuis les sources

```bash
git clone https://github.com/CheikhNaro/anime-sama-cli.git
cd anime-sama-cli
pip install -e .
# Ou pour un lancement direct sans installer :
./anisama-cli
```

Ajouter `~/.local/bin` au `PATH` si besoin (dans `~/.bashrc` ou `~/.zshrc`) :

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## Utilisation

**Lancer l’outil**

```bash
anime-sama-cli
# ou (alias fourni par le paquet)
anime-sama
```

Au premier lancement, le script demande le lecteur (MPV ou VLC) et la langue (VF ou VOSTFR), puis affiche le menu principal.

**Changer le lecteur par défaut**

```bash
anime-sama-cli --set-player
```

**Changer la langue par défaut**

```bash
anime-sama-cli --set-lang
```

**Aide**

```bash
anime-sama-cli --help
```

---

## Publication sur PyPI (mainteneurs)

Pour publier une nouvelle version sur [PyPI](https://pypi.org/) :

1. Installer les outils : `pip install build twine`
2. Incrémenter la version dans `pyproject.toml` (champ `version`)
3. Builder : `python -m build`
4. Vérifier : `twine check dist/*`
5. Publier : `twine upload dist/*` (ou utiliser GitHub Actions avec un secret `PYPI_API_TOKEN`)
