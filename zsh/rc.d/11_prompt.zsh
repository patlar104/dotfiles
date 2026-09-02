# Load Powerlevel10k after Oh My Zsh initialization. gitstatus needs job
# control, which zsh cannot enable without a controlling terminal, so skip the
# theme entirely in non-TTY shells such as agent tooling. Test the monitor
# option rather than a tty: instant prompt redirects stdin while .zshrc runs.
if [[ -o monitor && -r "$ZDOTDIR/plugins/powerlevel10k/powerlevel10k.zsh-theme" ]]; then
    source "$ZDOTDIR/plugins/powerlevel10k/powerlevel10k.zsh-theme"
fi
