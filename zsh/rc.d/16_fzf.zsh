# Some sane defaults for fzf
export FZF_DEFAULT_OPTS="--ansi --height=50% --tmux=bottom,50%,border-native --border=top --layout=reverse-list"

# Shell integration: Ctrl-T (files), Ctrl-R (history), Alt-C (cd)
# https://github.com/junegunn/fzf#setting-up-shell-integration
# The keybindings need zle, so skip them in non-TTY shells; `fzf -f` still works.
if (( $+commands[fzf] )) && [[ -o monitor ]]; then
    source <(fzf --zsh)
fi
