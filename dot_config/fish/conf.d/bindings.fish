# Docs: https://fishshell.com/docs/current/interactive.html#vi-mode-commands
if status is-interactive
    # Vi modes that keep the emacs-style bindings in every mode.
    set -g fish_key_bindings fish_hybrid_key_bindings

    set -g fish_cursor_default block
    set -g fish_cursor_insert line
    set -g fish_cursor_replace_one underscore
    set -g fish_cursor_visual block
end
