# Docs: https://fishshell.com/docs/current/index.html
# Go xdg libraries (lazygit, lazydocker) default to ~/Library/Application Support on macOS; point them at ~/.config.
if not set -q XDG_CONFIG_HOME; or test -z "$XDG_CONFIG_HOME"
    set -gx XDG_CONFIG_HOME "$HOME/.config"
end
# Repair SHELL when unset or pointing at an uninstalled binary (e.g. removed Homebrew fish).
if not set -q SHELL; or not test -x "$SHELL"
    set -gx SHELL (status fish-path)
end

# Opens nvim on a terminal and fails fast without one (agent shells).
set -gx EDITOR "$HOME/.local/bin/nvim-tty"
set -gx VISUAL "$EDITOR"
set -gx LANG en_US.UTF-8
set -gx LESS -FRSXMK
set -gx LESSHISTFILE -
set -gx MANPAGER less
set -gx PAGER bat

# Mirror dot_config/mise/config.toml [env] so non-mise Fish sessions keep identical tool guards.
set -gx AGENTS_CLI_TELEMETRY 0
set -gx AWS_CLI_AGENT_TOOLKIT_HINT_DISABLED true
set -gx CF_SEND_TELEMETRY 0
set -gx CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS 1
# "1" auto-approves tools only; "true" would also trust every directory and its hooks, bypassing per-folder Copilot trust (~/.copilot/config.json).
set -gx COPILOT_ALLOW_ALL 1
set -gx COPILOT_AUTO_UPDATE false
set -gx COPILOT_TELEMETRY_DISABLED true
# Keep gws off the macOS Keychain only; Linux keeps the system Secret Service keyring.
if test (uname -s) = Darwin
    set -gx GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND file
end
set -gx HF_HUB_DISABLE_TELEMETRY 1
set -gx HF_HUB_DISABLE_UPDATE_CHECK 1
# ~/.claude/skills links to ~/.agents/skills, which OpenCode already reads natively.
set -gx OPENCODE_DISABLE_CLAUDE_CODE_SKILLS 1
set -gx PI_SKIP_VERSION_CHECK 1
set -gx PI_TELEMETRY 0
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
set -gx RIPGREP_CONFIG_PATH "$HOME/.config/ripgrep/config"
set -gx SONARQUBE_CLI_KEYCHAIN_FILE "$HOME/.sonar/sonarqube-cli/tokens.json"
set -gx TRIVY_CONFIG "$HOME/.config/trivy/trivy.yaml"
