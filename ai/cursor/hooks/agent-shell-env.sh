#!/bin/bash
# Post-snap Shell inject: mise shims + nix bins + direnv export after Cursor restores state.
# env.d alone runs *before* eval "$snap", which can wipe PATH / re-set DIRENV_*.
set -euo pipefail

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' '{"permission":"allow"}'
  exit 0
fi

cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // .command // empty')
if [[ -z "$cmd" ]]; then
  printf '%s\n' '{"permission":"allow"}'
  exit 0
fi

# zsh prefix: runs inside the agent /bin/zsh -c after snap restore
read -r -d '' prefix <<'EOF' || true
() {
  local d
  local mise_shims=${XDG_DATA_HOME:-$HOME/.local/share}/mise/shims
  [[ -d $mise_shims ]] && path=($mise_shims $path)
  for d in ${XDG_STATE_HOME:-$HOME/.local/state}/nix/profile/bin $HOME/.nix-profile/bin /nix/var/nix/profiles/default/bin; do
    [[ -d $d ]] && path=($d $path)
  done
  if [[ -z ${__ETC_PROFILE_NIX_SOURCED:-} && -r /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]]; then
    emulate sh -c 'source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' 2>/dev/null || true
  fi
  if (( ${+commands[direnv]} )); then
    unset DIRENV_DIFF DIRENV_WATCHES IN_NIX_SHELL 2>/dev/null || true
    emulate zsh -c "$(chpwd_functions=(); direnv export zsh 2>/dev/null)" 2>/dev/null || true
  fi
};
EOF

printf '%s' "$input" | jq -c --arg prefix "$prefix" '
  .permission = "allow"
  | .updated_input = ((.tool_input // {command: .command}) + {command: ($prefix + " " + (.tool_input.command // .command // ""))})
  | {permission, updated_input}
'
