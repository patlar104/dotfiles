
# Activate the rbenv-selected Ruby for interactive shells.
if command -v rbenv >/dev/null 2>&1; then
    eval "$(rbenv init - zsh)"
fi

# Load interactive configuration modules.
for file in "$ZDOTDIR"/rc.d/*.zsh(N); do
    source "$file"
done
