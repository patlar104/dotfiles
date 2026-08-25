# Some sane defaults for fzf
export FZF_DEFAULT_OPTS="--ansi --height=50% --tmux=bottom,50%,border-native --border=top --layout=reverse-list"

# Shell integration: Ctrl-T (files), Ctrl-R (history), Alt-C (cd)
# https://github.com/junegunn/fzf#setting-up-shell-integration
if (( $+commands[fzf] )); then
    source <(fzf --zsh)
fi
