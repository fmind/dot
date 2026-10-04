# Docs: https://fishshell.com/docs/current/index.html
# Go xdg libraries (lazygit, lazydocker, k9s) and ptpython default to
# ~/Library/Application Support on macOS; keep their managed ~/.config files active.
set -q XDG_CONFIG_HOME; or set -gx XDG_CONFIG_HOME $HOME/.config
set -gx PTPYTHON_CONFIG_HOME $XDG_CONFIG_HOME/ptpython

# Editors
set -gx EDITOR nvim
set -gx VISUAL $EDITOR

# Locales
set -gx LANG en_US.UTF-8

# Pagers
set -gx LESS -FRSXMK
set -gx LESSHISTFILE -
set -gx MANPAGER "nvim +Man!"
set -gx PAGER "bat --plain"

# Tools
set -gx CARAPACE_BRIDGES 'zsh,fish,bash'
# Native completion owns these names; Carapace's dot command means Graphviz.
set -gx CARAPACE_EXCLUDES 'agy,dot,bf'
# 1 auto-approves tools only; the exact value "true" would also trust every working
# directory and load its hooks, bypassing the folders curated by `dot trust`.
set -gx COPILOT_ALLOW_ALL 1
set -gx COREPACK_ENABLE_AUTO_PIN 0
# Match the skin installed by chezmoi externals.
set -gx K9S_SKIN theme
# Layer the fmind/theme external over the managed config; lazygit rejects a missing
# custom config file, so wait until chezmoi has fetched it.
if test -r $XDG_CONFIG_HOME/lazygit/theme.yml
    set -gx LG_CONFIG_FILE $XDG_CONFIG_HOME/lazygit/config.yml,$XDG_CONFIG_HOME/lazygit/theme.yml
end
# mermaid-cli (mmdc) renders through puppeteer; point it at the system Chrome so
# a diagram export never downloads a second browser into ~/.cache/puppeteer.
if command -q google-chrome
    set -gx PUPPETEER_EXECUTABLE_PATH (command -v google-chrome)
end
set -gx RIPGREP_CONFIG_PATH $HOME/.config/ripgrep/config
set -gx TRIVY_CONFIG $HOME/.config/trivy/trivy.yaml
