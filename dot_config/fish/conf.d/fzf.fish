# Docs: https://fishshell.com/docs/current/index.html
# Base commands
set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden --strip-cwd-prefix --exclude .git'
set -gx FZF_ALT_C_COMMAND 'fd --type d --hidden --strip-cwd-prefix --exclude .git'

# Colours live in the theme, not here. The file is fetched from
# github.com/fmind/theme by .chezmoiexternal.toml.tmpl and is read before
# FZF_DEFAULT_OPTS, so this file keeps owning layout, bindings and previews.
set -gx FZF_DEFAULT_OPTS_FILE $HOME/.config/fzf/theme.conf

# Default options
set -gx FZF_DEFAULT_OPTS \
    --border \
    "--height=50%" \
    "--info=inline" \
    "--layout=reverse" \
    "--bind=ctrl-/:toggle-preview"

# Preview options
set -gx FZF_ALT_C_OPTS "--preview 'lsd --tree --color=always {} | head -200'"
set -gx FZF_CTRL_T_OPTS "--preview 'bat --number --color=always --line-range=:500 {}'"
