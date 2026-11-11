# Docs: https://fishshell.com/docs/current/index.html
# Go xdg libraries (lazygit, lazydocker) default to ~/Library/Application Support on macOS; point them at ~/.config.
if not set -q XDG_CONFIG_HOME; or test -z "$XDG_CONFIG_HOME"
    set -gx XDG_CONFIG_HOME "$HOME/.config"
end

# Opens nvim on a terminal and fails fast without one (agent shells).
set -gx EDITOR "$HOME/.local/bin/nvim-tty"
set -gx VISUAL "$EDITOR"
set -gx LANG en_US.UTF-8
set -gx LESS -FRSXMK
set -gx LESSHISTFILE -
set -gx MANPAGER less
set -gx PAGER bat

# "1" auto-approves tools only; "true" would also trust every directory and its hooks, bypassing `dot trust`.
set -gx COPILOT_ALLOW_ALL 1
# ~/.claude/skills links to ~/.agents/skills, which OpenCode already reads natively.
set -gx OPENCODE_DISABLE_CLAUDE_CODE_SKILLS 1
if test -r "$HOME/.config/glamour/fmind.json"
    set -gx GLAMOUR_STYLE "$HOME/.config/glamour/fmind.json"
end
# Guard until chezmoi fetches theme.yml (lazygit rejects missing config files).
if test -r "$HOME/.config/lazygit/theme.yml"
    set -gx LG_CONFIG_FILE "$HOME/.config/lazygit/config.yml,$HOME/.config/lazygit/theme.yml"
end
# Reuse system Chrome/Chromium so mermaid-cli (mmdc) never downloads a second browser into ~/.cache/puppeteer.
if command -q google-chrome
    set -gx PUPPETEER_EXECUTABLE_PATH (command -v google-chrome)
else if command -q chromium
    set -gx PUPPETEER_EXECUTABLE_PATH (command -v chromium)
else if test -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    set -gx PUPPETEER_EXECUTABLE_PATH "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
end
set -gx RIPGREP_CONFIG_PATH $HOME/.config/ripgrep/config
set -gx TRIVY_CONFIG $HOME/.config/trivy/trivy.yaml
