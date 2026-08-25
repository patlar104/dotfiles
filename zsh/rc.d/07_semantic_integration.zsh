# iTerm2 integration
# Prefer the vendored plugin over iTerm's auto-inject (older bundled script).
# Detect via profile/session ids and TERM_PROGRAM/LC_TERMINAL (SSH-forwarded).
if [[ -v ITERM_PROFILE || -v ITERM_SESSION_ID || ${TERM_PROGRAM-} == iTerm.app || ${LC_TERMINAL-} == iTerm2 ]]; then
    export ITERM_ENABLE_SHELL_INTEGRATION_WITH_TMUX=1
    # Drop auto-injected hooks so the newer plugin can load cleanly.
    precmd_functions=(${precmd_functions:#iterm2_precmd})
    preexec_functions=(${preexec_functions:#iterm2_preexec})
    unset ITERM_SHELL_INTEGRATION_INSTALLED ITERM2_SHOULD_DECORATE_PROMPT
    source $ZDOTDIR/plugins/iterm2-shell-integration/shell_integration/zsh
    path=($ZDOTDIR/plugins/iterm2-shell-integration/utilities $path)
fi

# Konsole integration
# Based on https://www.reddit.com/r/kde/comments/zf1ehj/psa_konsole_2208_now_supports_semantic_shell/ and P10K native support
if [[ -v KONSOLE_VERSION ]]; then
    export POWERLEVEL9K_TERM_SHELL_INTEGRATION=true

    _konsole_precmd() {
        print -n "\e]133;L\a\e]133;D;$?\a"
    }

    _konsole_preexec() {
        print -n "\e]133;C\a"
    }

    add-zsh-hook precmd _konsole_precmd
    add-zsh-hook preexec _konsole_preexec
fi

# Ghostty integration
if [[ -v GHOSTTY_RESOURCES_DIR ]]; then
    source $GHOSTTY_RESOURCES_DIR/shell-integration/zsh/ghostty-integration
fi
