# Anime-Sama-CLI

Regarder ou télécharger vos animés en VF/VOSTFR depuis votre terminal.

https://github.com/user-attachments/assets/d04bddbd-4b20-4d63-a650-5b4a6add65da

---

## Dépendances

Le projet a besoin des éléments suivants pour fonctionner.

### Dépendances système

| Dépendance | Rôle | Version minimale |
|------------|------|------------------|
| **Python** | Exécution de l’application | 3.10+ |
| **fzf** | Menu de sélection interactif (recherche, choix d’épisodes, etc.) | 0.53 |
| **MPV** ou **VLC** | Lecture vidéo des épisodes | — |
| **yt-dlp** | Téléchargement et lecture des flux vidéo | récente |
| **ffmpeg** | Requis par yt-dlp pour fusionner flux audio/vidéo | — |
| **chafa** | Affichage des covers (jaquettes) dans le panneau de prévisualisation fzf (sixel/ASCII) | — |

**Terminal pour les covers :** pour que les jaquettes s’affichent correctement, utilisez un terminal qui supporte l’affichage d’images ou le protocole sixel (p. ex. **Kitty**, **iTerm2**, **WezTerm**, **foot**). Avec **chafa**, un aperçu en caractères est possible même dans les terminaux qui ne gèrent pas les images nativement.

### Dépendances Python (gérées à l’installation)

Elles sont installées automatiquement avec le projet : `httpx`, `platformdirs`, `rich`, `textual`, `tomli` (si Python &lt; 3.11), `yt-dlp`.

---

## Fonctionnalités

- **Regarder** : parcourir le catalogue, choisir un animé et un épisode, lecture dans MPV ou VLC.
- **Télécharger** : sélection d’épisodes ou de saisons pour téléchargement (via yt-dlp).
- **Planning** : affichage du planning des sorties de la semaine et lecture depuis le planning.
- **Historique AniList** : connexion à AniList, import des animés « déjà vus » et « à regarder », consultation et mise à jour depuis l’outil.
- **Historique local** : consultation de l’historique de visionnage local.
- **Recherche** : recherche dans le catalogue et dans l’historique.

---

## Installation des dépendances système

Installez d’abord les paquets système selon votre distribution, puis installez le projet (voir section suivante).

### Debian / Ubuntu (et dérivés)

Sur les distributions basées sur Debian (Ubuntu, Linux Mint, etc.), utilisez `apt` :

1. Mettre à jour la liste des paquets :
   ```bash
   sudo apt update
   ```
2. Installer Python, **pipx** (recommandé pour les applis CLI), fzf, chafa, un lecteur vidéo (MPV ou VLC), ffmpeg et yt-dlp :
   ```bash
   sudo apt install python3 pipx fzf chafa mpv ffmpeg yt-dlp
   ```
   Pour utiliser VLC au lieu de MPV :
   ```bash
   sudo apt install vlc
   ```
3. Activer pipx pour l’utilisateur courant :
   ```bash
   pipx ensurepath
   ```
   Puis redémarrer le terminal ou exécuter `source ~/.bashrc` (ou `source ~/.zshrc` selon votre shell).
**Note :** La version de `yt-dlp` dans les dépôts peut être en retard. Pour une version à jour, vous pouvez utiliser pipx : `pipx install yt-dlp`.

### Arch Linux (et dérivés)

Sur Arch (et dérivés comme Manjaro), utilisez `pacman` :

1. Installer les paquets :
   ```bash
   sudo pacman -S python python-pip fzf chafa mpv ffmpeg yt-dlp
   ```
   Pour utiliser VLC au lieu de MPV :
   ```bash
   sudo pacman -S vlc
   ```
Sous Arch, les paquets sont en général à jour ; `yt-dlp` et `fzf` sont maintenus dans les dépôts officiels.

### Fedora / RHEL (et dérivés)

Sur Fedora, RHEL, CentOS Stream, Rocky, Alma, etc., utilisez `dnf` :

1. Installer Python, pip, fzf, chafa, ffmpeg et yt-dlp :
   ```bash
   sudo dnf install python3 python3-pip fzf chafa ffmpeg yt-dlp
   ```
2. Installer un lecteur vidéo. **MPV** est souvent dans les dépôts additionnels (RPM Fusion). Si nécessaire, activez RPM Fusion puis installez mpv :
   ```bash
   sudo dnf install mpv
   ```
   Si mpv n’est pas disponible, ou si vous préférez VLC :
   ```bash
   sudo dnf install vlc
   ```
Sur RHEL/CentOS, si `yt-dlp` ou `fzf` ne sont pas dans les dépôts par défaut, vous pouvez les installer via pip pour `yt-dlp` (`pip install -U yt-dlp`) et suivre les instructions officielles pour `fzf` si besoin.

---

## Installation

Une fois les dépendances système installées :

### Debian / Ubuntu (et dérivés) — utiliser pipx uniquement

Sur les systèmes basés sur Debian (Python géré par le système, PEP 668), **n’utilisez pas** `pip install` : l’environnement est « externally managed » et cela provoquera une erreur. Utilisez **pipx** pour installer l’application dans un environnement virtuel dédié.

**Depuis PyPI :**
```bash
pipx install anime-sama-cli
```

**Depuis les sources (dépôt Git) :**
```bash
git clone https://github.com/CheikhNaro/anime-sama-cli.git && cd anime-sama-cli
pipx install -e .
```

La commande `anime-sama` sera disponible. Si elle n’est pas trouvée, assurez-vous que le répertoire des binaires de pipx est dans votre `PATH` (généralement `~/.local/bin`) en ajoutant cette ligne à votre .zshrc ou .bashrc:
```bash
export PATH="$HOME/.local/bin:$PATH"
```
Et exécutez `pipx ensurepath` si ce n’est pas déjà fait.

### Autres distributions (Arch, Fedora, etc.)

```bash
pip install anime-sama-cli
```

Ou depuis les sources :
```bash
git clone https://github.com/CheikhNaro/anime-sama-cli.git && cd anime-sama-cli && pip install -e .
```

Si nécessaire, ajoutez `~/.local/bin` à votre `PATH`.

---

Vous pouvez aussi lancer sans installer : `./anisama-cli` depuis la racine du dépôt (avec les dépendances Python déjà installées dans un venv).

---

## Utilisation

### Lancer l’outil (menu principal)

Sans argument, l’outil affiche le menu principal (Regarder, Télécharger, Planning, etc.) :

```bash
anime-sama
```

Au premier lancement, vos préférences de lecteur (MPV ou VLC) et de langue (VF ou VOSTFR) sont demandées puis enregistrées.

### Changer le lecteur vidéo par défaut

Pour choisir à nouveau entre MPV et VLC :

```bash
anime-sama --set-player
```

### Changer la langue par défaut (VF / VOSTFR)

Pour modifier la langue d’affichage des épisodes :

```bash
anime-sama --set-lang
```

### Se connecter à AniList et importer son historique

Pour lier un compte AniList et importer les listes « déjà vus » et « à regarder » :

```bash
anime-sama anilist login
```

Après connexion, l’historique AniList est disponible dans le menu (Historique AniList, Mise à jour AniList).

### Aide

```bash
anime-sama --help
```

---

Merci à [@Sky-NiniKo](https://github.com/Sky-NiniKo/anime-sama_api) pour avoir rendu ce projet possible
