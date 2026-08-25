# Zero Home Presence Dotfiles

## License

[WTFPL](COPYING)

## There are many like it, but this one is mine

This repository contains tools and configurations I use in the shell. It
includes no graphical configurations, making it usable on servers and personal
workstations. It has been battle-tested on macOS and various Linux
distributions, including Debian, Ubuntu, CentOS, and even WSL.

I'm a big fan of the [XDG Base Directory
Specification](http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html)
and organize my dotfiles in a way that they don't clutter the `$HOME`
directory. I have reduced the files required in `$HOME` to a single
`.zshenv`; everything else goes under standard XDG paths or is launched via
aliases. Additionally, if you have root permissions, you can install dotfiles
with [zero home presence](#zero-home-presence).

## Features

* Extensive Zsh [configuration](zsh/rc.d) and [plugins](zsh/plugins), including:
  * [powerlevel10k](https://github.com/romkatv/powerlevel10k) prompt
  * [additional completions](https://github.com/zsh-users/zsh-completions)
  * [async autosuggestions plugin](https://github.com/zsh-users/zsh-autosuggestions)
  * [syntax highlighting plugin](https://github.com/zsh-users/zsh-syntax-highlighting)
  * [autoenv plugin](https://github.com/Tarrasch/zsh-autoenv)
  * [autopair plugin](https://github.com/hlissner/zsh-autopair)
  * [clean Zsh implementation of `z`](https://github.com/agkozak/zsh-z)
* Vim [configuration](vim/vimrc) and [plugins](vim/pack)
* Neovim [configuration](nvim/init.lua) and [plugins](nvim/plugins)
* Tmux [configuration](tmux/tmux.conf) and [plugins](tmux/plugins)
* Yazi [configuration](yazi/yazi.toml) and [plugins](yazi/plugins)
* Other configurations:
  * [ranger](configs/ranger)
  * [quilt](configs/quiltrc)
  * [Git](configs/gitconfig)
  * [htop](configs/htoprc)
  * [Ghostty](configs/ghostty)
* Handy [utilities](tools), including:
  * [fzf](https://github.com/junegunn/fzf)
  * [spark](https://github.com/holman/spark) to draw bar charts right in the console
  * [diff-so-fancy](https://github.com/so-fancy/diff-so-fancy) for a much better git diff layout
  * [git-extras](https://github.com/tj/git-extras) additional helpers for Git
  * [noindex](tools/noindex/noindex) to block macOS Spotlight from indexing heavy development folders (`node_modules`, `.venv`, `.git`, etc.)
* [Environment wrappers](env-wrappers) for multiple programming languages:
  * [goenv](https://github.com/syndbg/goenv)
  * [jenv](https://github.com/jenv/jenv)
  * [luaenv](https://github.com/cehoffman/luaenv)
  * [nodenv](https://github.com/nodenv/nodenv)
  * [phpenv](https://github.com/phpenv/phpenv)
  * [plenv](https://github.com/tokuhirom/plenv)
  * [pyenv](https://github.com/yyuu/pyenv)
  * [rbenv](https://github.com/rbenv/rbenv)

## Installation

> [!WARNING]
> I'm in process on switching to Neovim. Vim configuration isn't maintained
> anymore, might be removed in future.

### Requirements

* `zsh` version 5.9 or newer
* `git` all external components are added as git submodules
* GNU coreutils on macOS and \*BSD, see [GNU userland](#gnu-userland)

### Optional Dependencies

* `make` and `which` required to install git helpers
* `perl` diff-so-fancy runtime
* [`delta`](https://github.com/dandavison/delta) will be used as git pager instead of diff-so-fancy
* [`bat`](https://github.com/sharkdp/bat) will be used as man pager
* Nerd Fonts Symbols Only installed and enabled fallback in terminal emulator

### GNU Userland

Shell aliases assume GNU versions of `ls`, `df`, `du`, `cp` and `rm`,
as they use flags base BSD utilities don't provide. Without GNU coreutils these
aliases fail with `unrecognized option`. Some \*BSD variants need GNU
`grep` and `diff` too, their base versions don't support the long options
used in aliases.

Where coreutils is installed with a `g` prefix, like `gls` or `gdf`,
symlink the binaries under their plain names into `$HOME/.local/bin`, which
is already first in `PATH`:

```sh
for util in ls df du cp rm; do
    ln -sf "$(command -v g$util)" "$HOME/.local/bin/$util"
done
```

### Location

Dotfiles can be installed in any directory, but probably somewhere under
`$HOME`. Personally, I use `$HOME/.local/dotfiles`. The installation is
simple:

```sh
git clone https://github.com/z0rc/dotfiles.git "$HOME/.local/dotfiles"
$HOME/.local/dotfiles/deploy.zsh
chsh -s /bin/zsh
```

The [deployment script](deploy.zsh) helps set up all required symlinks after
the initial clone. It also adds a cron job to pull updates every midnight and
serves as a post-merge git hook, so you don't have to worry about updating
submodules after a successful pull.

## Zero Home Presence

It's possible to install dotfiles without creating a `~/.zshenv` symlink. To
do so, set the environment variable `ZDOTDIR` to `<installation dir>/zsh`,
e.g., `$HOME/.local/dotfiles/zsh`. This variable should be set very early in
the login process, before zsh starts sourcing the user's `.zshenv`. One
possible option is to add:

```sh
export ZDOTDIR="$HOME/.local/dotfiles/zsh"
```

into `/etc/zsh/zshenv`. Alternatively, you can set it with a PAM environment
module.

## Neovim Version

Neovim configuration is tested with latest Neovim release only.

## Vim Version

Vim 9.1 or higher is required to support the XDG Base Directory Specification.
To use all bundled vim plugins, install vim with Python and Ruby support
built-in.

## Configuration

### Git Configuration

Update `~/.config/git/local/user` with your email and name. It should look
like this:

```ini
[user]
    email = jdoe@example.com
    name = John Doe
```

You can also add additional configurations in `~/.config/git/local/stuff`.

### Spotlight Indexing Prevention (`noindex`)

The `noindex` utility (`tools/noindex/noindex` linked to `~/.local/bin/noindex`) prevents macOS Spotlight (`mds`) from indexing heavy development folders like `node_modules`, `.venv`, `.git`, `target`, `dist`, `build`, `.next`, and `.cache`.

#### CLI Commands

```sh
noindex                     # Touch .metadata_never_index in current directory
noindex node_modules        # Touch .metadata_never_index in node_modules
noindex sweep ~/Projects    # Recursively scan workspace and add .metadata_never_index to all dev folders
noindex check node_modules  # Check if Spotlight indexing is blocked
noindex rename build        # Rename build directory to build.noindex
```

#### Automatic Shell & Git Integration

* **Package Manager Wrappers:** Executing `npm`, `pnpm`, `yarn`, `bun`, `uv`, or `pip` installation commands automatically marks newly created `node_modules` or `.venv` folders with `.metadata_never_index`.
* **Zsh Navigation Hook (`chpwd`):** Automatically adds `.metadata_never_index` to `.git`, `node_modules`, or `.venv` whenever you `cd` into a directory.
* **Global Git Lifecycle Hooks (`~/.config/git/hooks/`):** `post-checkout`, `post-merge`, and `post-rewrite` hooks automatically run `noindex sweep` on any repository you switch branches in or pull updates to.

#### Troubleshooting & Removal

* **Check Indexing Status:**
  Verify if a directory is currently ignored by Spotlight:
  ```sh
  noindex check /path/to/folder
  mdls /path/to/folder
  ```
* **Re-enable Indexing on a Directory:**
  Remove `.metadata_never_index` to allow Spotlight to index a directory again:
  ```sh
  rm /path/to/folder/.metadata_never_index
  ```
* **Remove All Index Blocks in a Workspace:**
  Remove `.metadata_never_index` recursively across your workspace:
  ```sh
  find ~/Projects -name ".metadata_never_index" -delete
  ```
* **Disable Automatic Hooks:**
  * To disable shell package manager & `chpwd` hooks, remove `~/.local/dotfiles/zsh/rc.d/30_noindex.zsh`.
  * To disable global Git hooks, remove `post-checkout`, `post-merge`, or `post-rewrite` in `~/.config/git/hooks/`.

### Zsh Configuration

Note that Zsh configuration skips every global configuration file except
`/etc/zsh/zshenv`.

You can add your local configuration into `$ZDOTDIR/env.d/9[0-9]_*` and
`$ZDOTDIR/rc.d/9[0-9]_*`. The difference is that `env.d` is sourced always,
while `rc.d` is sourced only in interactive sessions.

Additionally, `$ZDOTDIR/.zlogin` and `$ZDOTDIR/.zlogout` are available for
modifications, though they are missing by default.

### Neovim Configuration

Local configuration can be added to:

* `$DOTFILES/nvim/init/0[1-9]_*` (like `01_local.lua`) to load after default
  options, but before any plugin.
* `$DOTFILES/nvim/init/9[0-9]_*` (like `99_local.vim`) to load after plugins.

### Vim Configuration

Add your local configuration to `$DOTFILES/vim/vimrc.local`.

### Local Paths

Local binaries can be placed in `$HOME/.local/bin`; it's added to `PATH` by
default. Man pages can be placed in `$XDG_DATA_HOME/man`.

### Lazy \*env

Pyenv and similar wrappers are lazy-loaded, meaning they won't be initialized
at shell start. Activation occurs on the first execution. Check the output of
`type -f pyenv` in the shell and the
[implementation](zsh/rc.d/12_many_env.zsh). Because of this, files like
`.python-version` won't work as expected; it's recommended to use
`autoenv.zsh` to explicitly activate the needed environment.

### Ignore Config Files Changes Locally

For example, Htop updates its config file `htoprc` when changing any view
mode or sort order. To ignore local changes to configuration files, you can do:

```sh
git update-index --assume-unchanged configs/htoprc
```

To restore git tracking of those files, use:

```sh
git update-index --no-assume-unchanged configs/htoprc
```

## Nix (system-wide dev tools)

Determinate Nix is installed at `/nix`. Dotfiles disables macOS global zsh
config (`unsetopt GLOBAL_RCS`), so Nix is wired via `zsh/env.d/05_nix.zsh`.

Home Manager flake: `nix/` in this repo.

```sh
# Apply (also runs from deploy.zsh)
/nix/var/nix/profiles/default/bin/nix run home-manager -- switch --flake ~/.local/dotfiles/nix#patricklarocque@darwin

# Verify in a fresh login shell
zsh -lic 'nix --version && gh --version && direnv version'
```

### Tool ownership (avoid duplicate installs)

| Layer | Owns | Examples |
|---|---|---|
| **Nix / Home Manager** | Baseline CLI on PATH | `git`, `gh`, `direnv`, `rg`, `fd`, `bat`, `fzf`, `jq`, `shellcheck`, `terraform` |
| **mise** | Language runtimes | node, bun, python, rust, uv (`~/.config/mise/config.toml`) |
| **Homebrew** | macOS / GNU userland | coreutils gnubin, curl, casks; OK if it overlaps Nix, Nix wins on PATH |
| **Legacy *env wrappers** | Lazy fallbacks | rbenv / pyenv / nodenv in `zsh/rc.d/12_many_env.zsh` — prefer mise for new work |

`uv` and `bun` are owned by mise, but installers (Hermes, Astral) and
GUI-spawned / sandboxed shells often miss interactive `mise activate`.
Dotfiles put mise shims on PATH for agents via `zsh/env.d/05_noninteractive_agent.zsh`
(+ `~/.cursor/hooks/agent-shell-env.sh` after snap restore) and link
`~/.local/bin/{uv,bun}` → the mise shims on `deploy.zsh` so sanitized PATHs
still find them without a second install.

Cursor sandbox network allowlist (`~/.cursor/sandbox.json` and
`cli-config.json` → `sandbox.networkAllowlist`) includes npm/bun registries
plus HashiCorp (terraform) and GitHub release hosts.

Do not remove Homebrew packages in the first pass unless you explicitly want a
Nix-only CLI. Prefer adding new baseline tools to `nix/home.nix` instead of brew.

### Nix trust (optional admin step)

`nix config check` may report `[INFO] You are not trusted by store uri: daemon`
while `trusted-users = root` only. To silence it and allow user-level store
operations without root, append to `/etc/nix/nix.custom.conf` (sudo), then
restart the Nix daemon:

```sh
echo 'trusted-users = root patricklarocque' | sudo tee -a /etc/nix/nix.custom.conf
sudo launchctl kickstart -k system/systems.determinate.nix-daemon
nix config check
```

The `[FAIL] Found profiles outside of "/nix/var/nix"/profiles` pointing at
`~/.nix-profile` is expected for standalone Home Manager on macOS and is safe
to ignore.

Local `/env-setup` skill: `~/.cursor/skills/env-setup/`.

### Known Nix / Home Manager warnings

**`warning: Git tree '…/dotfiles' has uncommitted changes`**

Harmless but noisy. Nix flakes record the Git tree state; dirty working trees
trigger this on every `home-manager switch`. Commit or stash dotfiles changes
before applying if you want a clean run (recommended after editing `nix/`).

**`warning: Using 'builtins.derivation' to create a derivation named 'options.json' … without a proper context`**

Comes from Home Manager’s options introspection on current nixpkgs/home-manager
inputs. It does not block activation and the generation still installs. Track
upstream home-manager/nixpkgs; upgrading flake inputs occasionally clears it.
No local action required unless activation starts failing.

**Terraform is unfree (BSL) in nixpkgs**

`flake.nix` uses `allowUnfreePredicate` for the `terraform` package only.
Open-source alternative: `opentofu` (drop-in CLI) is free in nixpkgs if you
prefer not to allow unfree packages.

### Cursor agent: Terraform + sandbox

Terraform is installed via Home Manager and allowlisted in `~/.cursor/permissions.json`
(read-only commands only). `init`, `plan`, `apply`, and `destroy` require
approval. Sandbox network rules: `~/.cursor/sandbox.json` / CLI
`sandbox.networkAllowlist` (HashiCorp, npm/bun registries, GitHub release hosts).
