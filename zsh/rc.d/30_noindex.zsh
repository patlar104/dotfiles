# 30_noindex.zsh - Automatic Spotlight indexing suppression for dev tools

_spotlight_noindex_touch() {
  local target="$1"
  if [[ -d "$target" && ! -f "$target/.metadata_never_index" ]]; then
    touch "$target/.metadata_never_index" 2>/dev/null
  fi
}

# Package manager wrappers to auto-block Spotlight on newly created dependency folders
npm() {
  command npm "$@"
  local res=$?
  if [[ $res -eq 0 && -d "node_modules" ]]; then
    _spotlight_noindex_touch "node_modules"
  fi
  return $res
}

pnpm() {
  command pnpm "$@"
  local res=$?
  if [[ $res -eq 0 && -d "node_modules" ]]; then
    _spotlight_noindex_touch "node_modules"
  fi
  return $res
}

yarn() {
  command yarn "$@"
  local res=$?
  if [[ $res -eq 0 && -d "node_modules" ]]; then
    _spotlight_noindex_touch "node_modules"
  fi
  return $res
}

bun() {
  command bun "$@"
  local res=$?
  if [[ $res -eq 0 && -d "node_modules" ]]; then
    _spotlight_noindex_touch "node_modules"
  fi
  return $res
}

uv() {
  command uv "$@"
  local res=$?
  if [[ $res -eq 0 ]]; then
    _spotlight_noindex_touch ".venv"
    _spotlight_noindex_touch "venv"
  fi
  return $res
}

pip() {
  command pip "$@"
  local res=$?
  if [[ $res -eq 0 ]]; then
    _spotlight_noindex_touch ".venv"
    _spotlight_noindex_touch "venv"
  fi
  return $res
}

# Auto-block indexing on entering directories with .git, node_modules, or .venv
_spotlight_noindex_chpwd() {
  if [[ -d ".git" ]]; then
    _spotlight_noindex_touch ".git"
  fi
  if [[ -d "node_modules" ]]; then
    _spotlight_noindex_touch "node_modules"
  fi
  if [[ -d ".venv" ]]; then
    _spotlight_noindex_touch ".venv"
  fi
}

autoload -U add-zsh-hook
add-zsh-hook chpwd _spotlight_noindex_chpwd
