# Nix and Home Manager are available in interactive and non-interactive Zsh.
if [[ -r /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]]; then
    emulate sh -c '. /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
fi
if [[ -d /nix/var/nix/profiles/default/bin ]]; then
    path=(/nix/var/nix/profiles/default/bin $path)
fi
if [[ -d "$HOME/.nix-profile/bin" ]]; then
    path=("$HOME/.nix-profile/bin" $path)
fi
typeset -U path
export PATH
if [[ -r "$HOME/.nix-profile/etc/profile.d/hm-session-vars.sh" ]]; then
    emulate sh -c '. "$HOME/.nix-profile/etc/profile.d/hm-session-vars.sh"'
fi
