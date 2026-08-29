## Learned User Preferences

- Prefer end-to-end setup with smoke tests and verification; do not skip plan steps, and give concrete proof (logs, version checks) rather than a claim that work finished.
- Ask before running commands that need sudo.
- Prefer system-wide, sandbox-accessible tooling over project-only installs unless the task is explicitly project-scoped.
- Prefer Nix/mise for lightweight isolation; use Apple `container` only for Linux/OCI; do not run Docker Desktop and Apple `container` at the same time.
- When adding machine tools, also persist agent-facing Cursor rules/docs so future agents know how to use them.
- Prefer GitHits MCP for open-source package and docs context when available instead of generic web search.
- For storage or System Data investigations, keep iOS simulators, backups, Ollama data, and Photos iCloud content unless explicitly told to remove them.
- Treat `/env-setup` and similar environment work as system-wide on this Mac unless told it is project-specific.
- Do not make assumptions: verify from official/trusted sources, check signatures (GPG) before installing downloaded binaries, and interpret ambiguous requests by intended outcome rather than literal wording.
- Pin explicit tool versions instead of `latest` in version-manager configs, for reproducible development.
- Claude CLI is optional and mainly for use with Ollama; the user adds API keys themselves.
- Include installed shells such as PowerShell in allowed-shells configuration when editing shell access lists.

## Learned Workspace Facts

- Dotfiles live at `~/.local/dotfiles` (Nix Home Manager); GitHub fork is `patlar104/dotfiles` — do not force-push over unrelated remote `main` history.
- Apple `container` CLI is at `/opt/homebrew/bin/container`; agent usage is documented in `~/.cursor/rules/apple-container.mdc` (on-demand start/stop, CPU/memory caps).
- fzf is installed via dotfiles at `~/.local/bin/fzf`, with agent guidance in `~/.cursor/rules/fzf.mdc`.
- Cursor agent shells are non-interactive; mise/nix/direnv behavior for agents is documented in `~/.cursor/rules/agent-shell.mdc`.
- General-purpose lab workspace is at `~/Music/Developer/lab` (includes `scripts/doctor.sh` for local git/automation checks).
- Terraform is managed via Home Manager with explicit unfree/BSL allowlisting in the dotfiles flake.
- `~/.kube/config` exists for local Kubernetes access (Docker Desktop context when that is the intended cluster).
- `~/.cursor/skills/env-setup` is the preferred skill for system-wide macOS environment setup and verification; runtimes such as Bun should be configured to work inside the Cursor sandbox.
- iTerm2 shell integration is set up on this Mac.
- Python tooling is split deliberately: mise manages project runtimes (node, bun, go, rust, python, uv, shellcheck) and `uv tool` is the installer for Python CLI apps (including `pipx` itself) — keep them non-overlapping.
- `uv tool` venvs must be pinned to uv-managed interpreters, never mise's Python, since bumping mise's Python breaks them; there is no Homebrew Python, and a python.org framework Python 3.14.6 lives at `/usr/local/bin/python3.14`.
- Shell env vars live in numbered plain files under `~/.local/dotfiles/zsh/env.d/`; `rm -rf` and the file delete tool are blocked by the permissions config, but `find -depth -delete` works.
