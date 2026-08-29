# AI agent configuration

Single source of truth for the personal (user tier) agent setup: Cursor hooks,
rules and skills, plus skills for the agents CLI. `deploy.zsh` symlinks these
into place, so `git pull` on another workstation updates the live configuration
without a copy step.

## Layout

```text
ai/
  AGENTS.md            -> ~/AGENTS.md
  cursor/
    hooks.json         -> ~/.cursor/hooks.json
    hooks/             per-file links into ~/.cursor/hooks/
      agent-shell-env.sh
      failure-watch.sh
      failure-watch.py
    rules/             -> ~/.cursor/rules
    skills/            -> ~/.cursor/skills
  agents/
    skills/            -> ~/.agents/skills
```

## Why the watchdog is linked file by file

`failure-watch.sh` and `failure-watch.py` locate their own state through a
hardcoded `$HOME/.cursor/hooks`, not through the script's own location, and they
write `logs/failure-watch.log` and `state/failure-watch/` there. Linking the
whole directory would place that continuously changing runtime state inside this
repository.

Linking only the configuration and the two executables keeps `~/.cursor/hooks`
a real directory. Logs and state stay host-local and unversioned, while every
self-reference in the scripts still resolves.

Rules and skills produce no runtime output, so they are linked as whole
directories: a new rule or skill syncs with one commit and no `deploy.zsh` edit.

## Setting up another workstation

```sh
git clone https://github.com/patlar104/dotfiles.git ~/.local/dotfiles
cd ~/.local/dotfiles && ./deploy.zsh
```

`deploy.zsh` moves any pre-existing real file or directory aside with a
`.pre-dotfiles.<timestamp>` suffix before linking, so an existing setup is never
overwritten in place.

## How updates propagate

- The two watchdog scripts are re-read on every hook invocation, so a pull takes
  effect on the next tool call.
- `hooks.json` is read when a Cursor session starts. Changing the hook *wiring*
  (as opposed to the script bodies) needs a session restart.
- Rules and skills are read per session.

## Deliberately not tracked

Host-specific or tool-managed, and left out of version control:

| Path | Reason |
| --- | --- |
| `~/.cursor/mcp.json` | Contains absolute paths to locally installed binaries |
| `~/.cursor/cli-config.json`, `permissions.json`, `sandbox.json` | Host-local preferences |
| `~/.cursor/hooks/logs`, `~/.cursor/hooks/state` | Runtime output, regenerated on first hook run |
| `~/.cursor/skills-cursor`, `~/.cursor/plugins` | Managed by Cursor, repopulated automatically |
| `helm-asc` skill | A link into an installed application bundle. Git-ignored and recreated by `deploy.zsh` only where that bundle exists. |

## Verifying a deployment

```sh
for p in AGENTS.md .cursor/hooks.json .cursor/hooks/failure-watch.py \
         .cursor/rules .cursor/skills .agents/skills; do
    printf '%-34s -> %s\n' "$p" "$(readlink "$HOME/$p")"
done
```

To confirm the watchdog is live rather than assuming it, run any failing command
and check that a new line appears in `~/.cursor/hooks/logs/failure-watch.log`.
