# Provide zf_* file-operation builtins before env.d loads.
zmodload -m -F zsh/files 'b:zf_*'

# Make rbenv shims available before Zsh redirects ZDOTDIR.
# This is needed for non-interactive shells as well as interactive shells.
if [[ -d "$HOME/.rbenv/shims" ]]; then
    path=("$HOME/.rbenv/shims" "$HOME/.rbenv/bin" $path)
    typeset -U path
    export PATH
fi

# Keep the rest of the Zsh configuration in this dotfiles repository.
export ZDOTDIR="$HOME/.local/dotfiles/zsh"

# XDG locations used by the dotfiles configuration.
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"

# Load environment configuration for every Zsh invocation.
for file in "$ZDOTDIR"/env.d/*.zsh(N); do
    source "$file"
done
