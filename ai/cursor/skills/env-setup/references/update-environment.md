# Update an existing environment

Use when dotfiles/Nix config already exists and needs package or hook changes.

## Local update path

1. Edit `~/.local/dotfiles/nix/home.nix` (packages, sessionPath, programs)
2. Edit shell hooks if PATH/direnv behavior changed
3. Apply:

```bash
NIX=/nix/var/nix/profiles/default/bin/nix
$NIX run home-manager -- switch --flake ~/.local/dotfiles/nix#patricklarocque@darwin
~/.local/dotfiles/deploy.zsh
```

4. Verify in `zsh -lic` — same checks as create-environment.md step 5
5. Roll back if needed: `home-manager generations` then switch to prior generation

## Idempotency

Run `deploy.zsh` twice. Second run must not error or drift paths unexpectedly.

## Cloud Agent appendix (optional)

When updating a **Cursor Cloud Agent** environment (not local Mac):

- Use cursor-cloud MCP: `environment-info`, `list-cloud-agents` with `sources: ["setup"]`
- Update idempotent `install` script in `.cursor/environment.json`
- `take-environment-snapshot` → `check-environment-snapshot` → rebuild

Local dotfiles git commits are the durable artifact for this machine; cloud
snapshots are separate.
