# Set up a new environment (local macOS)

Use this reference when provisioning a **new** local dev environment or bringing
an empty/broken Nix shell back to working order.

## Prerequisites

- Determinate Nix installed under `/nix`
- Dotfiles at `~/.local/dotfiles`
- Home Manager flake at `~/.local/dotfiles/nix/`

## Steps

### 1. Audit

```bash
NIX=/nix/var/nix/profiles/default/bin/nix
$NIX --version
$NIX config check
zsh -lic 'which -a nix node python3 git direnv; mise ls 2>/dev/null'
cat /etc/nix/nix.conf
```

Record: nix in PATH or not, profile empty or not, tool overlap with mise/brew.

### 2. Ensure shell integration

Confirm these files exist in dotfiles:

- `zsh/env.d/05_nix.zsh` — sources `nix-daemon.sh` (required because dotfiles disables GLOBAL_RCS)
- `zsh/rc.d/23_direnv.zsh` — `eval "$(direnv hook zsh)"`

### 3. Define packages in home.nix

Baseline CLI tools in `home.packages`. Defer node/python/rust to mise unless
explicitly moving them to Nix.

### 4. First apply

```bash
NIX=/nix/var/nix/profiles/default/bin/nix
$NIX run home-manager -- switch --flake ~/.local/dotfiles/nix#patricklarocque@darwin
direnv allow ~/.local/dotfiles/nix 2>/dev/null || true
~/.local/dotfiles/deploy.zsh
```

### 5. Verify (fresh login shell)

All must pass:

- `command -v nix` resolves
- `nix config check` has no FAIL for PATH (trust may still INFO)
- Core tools from Nix/HM profile run
- `deploy.zsh` succeeds on second run

### 6. Demo

Run at least two representative commands (nvim headless, gh, or project tests)
and paste output in the session.

## macOS-only notes

- Xcode / iOS Simulator: document but do not block system-wide Nix setup
- GNU coreutils: dotfiles already prefers Homebrew gnubin on macOS
