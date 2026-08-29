---
name: env-setup
description: >-
  Set up or update a local development environment on macOS. Use when the user
  asks to configure dev tools, wire shell/Nix/direnv, verify installs end-to-end,
  run /env-setup, or set up a new environment for dotfiles or a codebase.
---

# env-setup

Local adaptation of the Cursor Cloud env-setup workflow for macOS. Cloud-only
steps (cursor-cloud MCP, environment snapshots, `environment.json` publish) are
documented in `references/update-environment.md` for optional Cloud Agent use.

## When to use

- User invokes `/env-setup` or asks to set up / update a dev environment
- System-wide dotfiles/Nix work under `~/.local/dotfiles`
- Project-specific work: read repo install signals first (lockfiles, README, AGENTS.md)

## Workflow

Read the matching reference before acting:

| Situation | Reference |
|---|---|
| New or empty local env | [create-environment.md](references/create-environment.md) |
| Update existing dotfiles/nix config | [update-environment.md](references/update-environment.md) |

### 1. Discovery

Inspect current state before changing anything:

- Shell: `~/.local/dotfiles/zsh/`, login PATH (`zsh -lic 'echo $PATH'`)
- Nix: `/etc/nix/nix.conf`, `nix --version`, `nix config check`
- Tool overlap: mise (`~/.config/mise/config.toml`), Homebrew, lazy *env in dotfiles
- Repo signals (if project-scoped): `package.json`, lockfiles, `scripts/`, CI, README

Separate **macOS-only** steps (Xcode, iOS Simulator) from steps runnable in any shell.

### 2. Define

Choose the smallest change that satisfies the objective:

- **System-wide (default on this machine):** `~/.local/dotfiles/nix/flake.nix` + Home Manager
- Shell hooks: `zsh/env.d/05_nix.zsh`, `zsh/rc.d/23_direnv.zsh`
- Idempotent apply: `deploy.zsh` home-manager block

Do not remove mise/*env/Homebrew in the first pass unless the user asks.

### 3. Apply

Run apply steps; **run twice** to confirm idempotency:

```bash
NIX=/nix/var/nix/profiles/default/bin/nix
$NIX run home-manager -- switch --flake ~/.local/dotfiles/nix#patricklarocque@darwin
~/.local/dotfiles/deploy.zsh
```

If `nix config check` reports untrusted user, fix trust before profile installs.

### 4. Verify

Use the verification-before-completion gate: no success claims without fresh command output.

Fresh login shell checks:

```bash
zsh -lic 'command -v nix && nix --version'
zsh -lic 'nix profile list 2>/dev/null | head -20'
zsh -lic 'direnv version && git --version && gh --version && rg --version'
zsh -lic 'type -a node python3'
```

Re-run `deploy.zsh` and confirm the nix step succeeds on the second run.

### 5. Demo

Run representative applications and capture output:

- `nvim --headless -c 'echo ok' -c q`
- `gh auth status` (if authenticated)
- Any project-specific verify command from README/AGENTS.md

Report evidence, not assumptions.

## Guardrails

- Prefer dotfiles-integrated Nix over per-project flakes for system-wide goals
- Never skip sourcing nix-daemon.sh when dotfiles uses `unsetopt GLOBAL_RCS`
- Keep language runtimes on mise unless Nix ownership is explicit
- Do not commit secrets (.env, credentials)
