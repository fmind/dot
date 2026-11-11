# Docs: https://fishshell.com/docs/current/index.html
set -gx FZF_DEFAULT_COMMAND 'fd --type f --hidden'
set -gx FZF_ALT_C_COMMAND 'fd --type d --hidden'

# fmind/theme supplies colors via FZF_DEFAULT_OPTS_FILE (read before FZF_DEFAULT_OPTS); guard until fetched.
if test -r $HOME/.config/fzf/theme.conf
    set -gx FZF_DEFAULT_OPTS_FILE $HOME/.config/fzf/theme.conf
end

set -gx FZF_DEFAULT_OPTS \
    --border \
    "--height=50%" \
    "--info=inline" \
    "--layout=reverse" \
    "--bind=ctrl-/:toggle-preview"

set -gx FZF_ALT_C_OPTS "--preview 'lsd --tree --icon=always --color=always {} | head -200'"
set -gx FZF_CTRL_T_OPTS "--preview 'bat --number --color=always --line-range=:500 {}'"
