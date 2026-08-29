#!/bin/bash
# Run failure-watch.py on any usable python3.
#
# Resolution must not depend on a specific interpreter version: bumping mise's
# python previously left this hook pointing at a path that no longer existed,
# and the wrapper then exited 0 with `{}` — silently disabling failure watching
# with no diagnostic anywhere. Probe candidates in preference order, accept the
# first one that actually runs, and if none do, say so loudly in the hook log.
SCRIPT="${HOME}/.cursor/hooks/failure-watch.py"
HOOK_LOG="${HOME}/.cursor/hooks/logs/failure-watch.log"
MISE="${HOME}/.local/bin/mise"
MISE_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/mise"
UV_PY="${XDG_DATA_HOME:-$HOME/.local/share}/uv/python"

note() {
  mkdir -p "$(dirname "$HOOK_LOG")" 2>/dev/null
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >>"$HOOK_LOG" 2>/dev/null
  printf '[failure-watch] %s\n' "$1" >&2
}

# A candidate is usable if it runs and meets the script's own MIN_PY floor.
usable() {
  [[ -n "$1" && -x "$1" ]] || return 1
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null
}

resolve_python() {
  local c
  # 1. Whatever mise currently points at, whatever version that happens to be.
  if [[ -x "$MISE" ]]; then
    c=$("$MISE" which python3 2>/dev/null || true)
    usable "$c" && { printf '%s\n' "$c"; return 0; }
  fi
  # 2. Newest mise-managed install, resolved by glob rather than a pinned version.
  for c in $(printf '%s\n' "$MISE_DATA"/installs/python/*/bin/python3 2>/dev/null | sort -Vr); do
    usable "$c" && { printf '%s\n' "$c"; return 0; }
  done
  # 3. uv-managed interpreters, then system pythons.
  for c in $(printf '%s\n' "$UV_PY"/*/bin/python3 2>/dev/null | sort -Vr); do
    usable "$c" && { printf '%s\n' "$c"; return 0; }
  done
  for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    usable "$c" && { printf '%s\n' "$c"; return 0; }
  done
  # 4. Anything named python3 on PATH.
  c=$(command -v python3 2>/dev/null || true)
  usable "$c" && { printf '%s\n' "$c"; return 0; }
  return 1
}

py=$(resolve_python || true)

if [[ -z "$py" ]]; then
  note "DISABLED: no usable python3 found; failure watching is off until one is available"
  printf '%s\n' '{}'
  exit 0
fi

export PYTHONDONTWRITEBYTECODE=1
exec "$py" "$SCRIPT"
