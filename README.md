# Anime-Sama-CLI

Regarder ou télécharger vos animés en VF/VOSTFR depuis votre terminal.

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

### Dépendance optionnelle

| Dépendance | Rôle |
|------------|------|
| **ImageMagick** | Aperçu des jaquettes dans fzf et renforcement de la netteté des images |

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
2. Installer Python, pip, fzf, un lecteur vidéo et yt-dlp :
   ```bash
   sudo apt install python3 python3-pip fzf mpv yt-dlp
   ```
   Pour utiliser VLC au lieu de MPV :
   ```bash
   sudo apt install vlc
   ```
3. *(Optionnel)* ImageMagick pour les aperçus et la netteté des covers :
   ```bash
   sudo apt install imagemagick
   ```

**Note :** La version de `yt-dlp` dans les dépôts peut être en retard. Pour une version à jour, vous pouvez utiliser pip : `pip install -U yt-dlp` (après avoir installé `python3-pip`).

### Arch Linux (et dérivés)

Sur Arch (et dérivés comme Manjaro), utilisez `pacman` :

1. Installer les paquets :
   ```bash
   sudo pacman -S python python-pip fzf mpv yt-dlp
   ```
   Pour utiliser VLC au lieu de MPV :
   ```bash
   sudo pacman -S vlc
   ```
2. *(Optionnel)* ImageMagick :
   ```bash
   sudo pacman -S imagemagick
   ```

Sous Arch, les paquets sont en général à jour ; `yt-dlp` et `fzf` sont maintenus dans les dépôts officiels.

### Fedora / RHEL (et dérivés)

Sur Fedora, RHEL, CentOS Stream, Rocky, Alma, etc., utilisez `dnf` :

1. Installer Python, pip, fzf et yt-dlp :
   ```bash
   sudo dnf install python3 python3-pip fzf yt-dlp
   ```
2. Installer un lecteur vidéo. **MPV** est souvent dans les dépôts additionnels (RPM Fusion). Si nécessaire, activez RPM Fusion puis installez mpv :
   ```bash
   sudo dnf install mpv
   ```
   Si mpv n’est pas disponible, installez VLC :
   ```bash
   sudo dnf install vlc
   ```
3. *(Optionnel)* ImageMagick :
   ```bash
   sudo dnf install ImageMagick
   ```

Sur RHEL/CentOS, si `yt-dlp` ou `fzf` ne sont pas dans les dépôts par défaut, vous pouvez les installer via pip pour `yt-dlp` (`pip install -U yt-dlp`) et suivre les instructions officielles pour `fzf` si besoin.

---

## Installation du projet

Une fois les dépendances système installées :

```bash
pip install anime-sama-cli
```

La commande `anime-sama` sera disponible. Si nécessaire, ajoutez le répertoire des binaires à votre `PATH` (par exemple `~/.local/bin` pour une installation utilisateur) :

```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Installation depuis les sources (dépôt Git) :**

```bash
git clone https://github.com/CheikhNaro/anime-sama-cli.git && cd anime-sama-cli && pip install -e .
```

Vous pouvez aussi lancer sans installer : `./anisama-cli` depuis la racine du dépôt (avec les dépendances Python déjà installées).

---

## Utilisation

### Lancer l’outil (menu principal)

Sans argument, l’outil affiche le menu principal (Regarder, Télécharger, Planning, etc.) :

```bash
anime-sama
```

Au premier lancement, le lecteur (MPV ou VLC) et la langue (VF ou VOSTFR) sont demandés puis enregistrés.

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

