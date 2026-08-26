#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# These are the legacy root-level dotfiles retained by this branch.
DOTFILES=(.gitconfig .zshrc)

for dotfile in "${DOTFILES[@]}"; do
    source="$SCRIPT_DIR/$dotfile"
    target="$HOME/$dotfile"
    if [[ ! -e "$source" ]]; then
        printf 'Skipping missing source: %s\n' "$source" >&2
        continue
    fi
    ln -sfn -- "$source" "$target"
done
