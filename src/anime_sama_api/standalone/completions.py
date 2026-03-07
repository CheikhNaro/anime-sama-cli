# -*- coding: utf-8 -*-
"""Génération des complétions shell (bash, zsh, fish)."""

from __future__ import annotations

import sys


def get_bash_script() -> str:
    """Retourne le script de complétion Bash."""
    return r'''# Complétion pour anime-sama (Bash)
# À ajouter : source <(anime-sama completions bash)  (dans ~/.bashrc ou ~/.bash_profile)

_anime_sama() {
    local cur prev words cword
    _init_completion -s 2>/dev/null || _init_completion -n = 2>/dev/null || return
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=($(compgen -W "--help -h --set-player --set-lang completions anilist" -- "$cur"))
        return
    fi
    prev="${words[cword-1]}"
    case "$prev" in
        anilist)
            COMPREPLY=($(compgen -W "login" -- "$cur"))
            ;;
        completions)
            COMPREPLY=($(compgen -W "bash zsh fish" -- "$cur"))
            ;;
        *)
            COMPREPLY=()
            ;;
    esac
}

complete -F _anime_sama anime-sama
'''


def get_zsh_script() -> str:
    """Retourne le script de complétion Zsh."""
    return r'''# Complétion pour anime-sama (Zsh)
# À ajouter : source <(anime-sama completions zsh)  (dans ~/.zshrc)

_anime_sama() {
    local cur context state state_descr line
    typeset -A opt_args
    _arguments -C \
        '(-h --help)'{-h,--help}'[Affiche cette aide]' \
        '(--set-player)'--set-player'[Changer le lecteur vidéo]' \
        '(--set-lang)'--set-lang'[Changer la langue]' \
        '1: :->cmd' \
        '2: :->sub'
    case $state in
        cmd)
            _values "commande" \
                "anilist[Commandes AniList]" \
                "completions[Générer les complétions shell]"
            ;;
        sub)
            case $line[1] in
                anilist)
                    _values "sous-commande" "login"
                    ;;
                completions)
                    _values "shell" "bash" "zsh" "fish"
                    ;;
            esac
            ;;
    esac
}

compdef _anime_sama anime-sama
'''


def get_fish_script() -> str:
    """Retourne le script de complétion Fish."""
    return r'''# Complétion pour anime-sama (Fish)
# À placer dans ~/.config/fish/completions/anime-sama.fish
# ou : anime-sama completions fish > ~/.config/fish/completions/anime-sama.fish

complete -c anime-sama -s h -l help -d "Affiche cette aide"
complete -c anime-sama -l set-player -d "Changer le lecteur vidéo (MPV / VLC)"
complete -c anime-sama -l set-lang -d "Changer la langue (VF / VOSTFR)"

complete -c anime-sama -n "not __fish_seen_subcommand_from anilist completions" -a anilist -d "Commandes AniList"
complete -c anime-sama -n "not __fish_seen_subcommand_from anilist completions" -a completions -d "Générer les complétions shell"

complete -c anime-sama -n "__fish_seen_subcommand_from anilist" -a login -d "Se connecter à AniList"

complete -c anime-sama -n "__fish_seen_subcommand_from completions" -a bash -d "Script Bash"
complete -c anime-sama -n "__fish_seen_subcommand_from completions" -a zsh -d "Script Zsh"
complete -c anime-sama -n "__fish_seen_subcommand_from completions" -a fish -d "Script Fish"
'''


def main(shell: str) -> bool:
    """Affiche le script de complétion pour le shell donné. Retourne True si shell reconnu."""
    script = None
    if shell == "bash":
        script = get_bash_script()
    elif shell == "zsh":
        script = get_zsh_script()
    elif shell == "fish":
        script = get_fish_script()
    if script:
        print(script, end="")
        return True
    return False
