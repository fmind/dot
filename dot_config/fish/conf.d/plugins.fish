# Docs: https://fishshell.com/docs/current/index.html
# PLUGINS
if status is-interactive
    if command -q mise
        mise activate fish | source
    end
    if command -q fzf
        fzf --fish | source
    end
    if command -q atuin
        atuin init fish --disable-ai | source
    end
    if command -q starship
        starship init fish --print-full-init | source
    end
    if command -q zoxide
        zoxide init fish | source
    end
    # Start once after shell initialization; keep Fish available if Zellij exits.
    function auto_zellij --on-event fish_prompt
        functions -e auto_zellij
        if status is-interactive
            and test -t 0 -a -t 1
            and command -q zellij
            and not set -q ZELLIJ
            and not set -q TMUX
            and not set -q NVIM
            and not set -q SSH_CONNECTION
            and not set -q SSH_CLIENT
            and not set -q SSH_TTY
            and not set -q CI
            and not set -q CLAUDECODE
            and not set -q ANTIGRAVITY_AGENT
            and test "$TERM_PROGRAM" != vscode
            and test "$TERM_PROGRAM" != agy
            and test "$TERM" != dumb
            command zellij attach --create main
        end
    end
end
