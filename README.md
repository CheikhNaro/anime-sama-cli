# Anime-Sama-cli
Regarder ou télécharger vos animés en VF/VOSTFR depuis votre terminal.
=======



https://github.com/user-attachments/assets/f10d82de-1a6d-47ea-b43e-a91fd9e10ed3



---

## Dépendances requises

- **Python 3.10+**
- **fzf** (≥ 0.53)
- **MPV** ou **VLC**
- **yt-dlp** (téléchargements et lecture)
- *Optionnel* : **ImageMagick** terminal compatible images (Kitty, WezTerm, iTerm2)

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

Cloner le dépôt puis installer pour votre utilisateur :

```bash
git clone https://github.com/CheikhNaro/anime-sama-cli.git
cd anime-sama-cli
pip install --user -e ".[cli]"
mkdir -p ~/.local/bin
ln -sf "$(pwd)/anisama-cli" ~/.local/bin/anime-sama
chmod +x ~/.local/bin/anime-sama
```

Ajouter `~/.local/bin` au `PATH` si besoin (dans `~/.bashrc` ou `~/.zshrc`) :

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## Utilisation

**Lancer l’outil**

```bash
anime-sama
```

Au premier lancement, le script demande le lecteur (MPV ou VLC) et la langue (VF ou VOSTFR), puis affiche le menu principal.

**Changer le lecteur par défaut**

```bash
anime-sama --set-player
```

**Changer la langue par défaut**

```bash
anime-sama --set-lang
```

**Aide**

```bash
anime-sama --help
```
