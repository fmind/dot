# Docs: https://fishshell.com/docs/current/index.html
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
set -gx COPILOT_ALLOW_ALL true
set -gx COREPACK_ENABLE_AUTO_PIN 0
# Match the skin installed by chezmoi externals.
set -gx K9S_SKIN theme
# mermaid-cli (mmdc) renders through puppeteer; point it at the system Chrome so
# a diagram export never downloads a second browser into ~/.cache/puppeteer.
if command -q google-chrome
    set -gx PUPPETEER_EXECUTABLE_PATH (command -v google-chrome)
end
set -gx RIPGREP_CONFIG_PATH $HOME/.config/ripgrep/config
set -gx TRIVY_CONFIG $HOME/.config/trivy/trivy.yaml
