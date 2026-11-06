-- Docs: https://www.lazyvim.org/configuration/general
-- Select the Python analyzer through LazyVim so only ty and Ruff are enabled.
vim.g.lazyvim_python_lsp = "ty"

-- No plugin uses a remote-plugin host.
for _, provider in ipairs({ "node", "perl", "python3", "ruby" }) do
  vim.g["loaded_" .. provider .. "_provider"] = 0
end

local opt = vim.opt

-- Enable soft wrapping (LazyVim already breaks lines at word boundaries)
opt.wrap = true

-- Scroll offset context
opt.scrolloff = 15

-- Keymap timeouts
opt.timeoutlen = 400

-- Prefer xclip with an X display on Linux/ChromeOS to avoid wl-clipboard hanging
-- in Wayland containers. Keep native macOS and Wayland-only clipboard selection.
if vim.fn.has("linux") == 1 and vim.env.DISPLAY and vim.env.DISPLAY ~= "" and vim.fn.executable("xclip") == 1 then
  -- xclip exits non-zero with "Error: target STRING not available" whenever a selection
  -- has no owner or holds non-text data, which Neovim surfaces as a clipboard error on
  -- every paste. Read through a Lua function so an unavailable selection is simply an
  -- empty register instead of an error message. Preserve the trailing newline with
  -- keepempty=1 so linewise yanks (yy, dd) match Neovim's clipboard cache and paste as
  -- full lines instead of characterwise text.
  local function paste(selection)
    return function()
      local lines = vim.fn.systemlist({ "xclip", "-selection", selection, "-o" }, "", 1)
      return vim.v.shell_error == 0 and lines or {}
    end
  end

  vim.g.clipboard = {
    name = "xclip",
    copy = {
      ["+"] = "xclip -selection clipboard",
      ["*"] = "xclip -selection primary",
    },
    paste = {
      ["+"] = paste("clipboard"),
      ["*"] = paste("primary"),
    },
    cache_enabled = 1,
  }
elseif
  vim.fn.has("linux") == 1
  and (vim.env.WAYLAND_DISPLAY or "") == ""
  and (vim.env.SSH_CONNECTION or "") == ""
  and (vim.env.TMUX or "") == ""
then
  -- LazyVim sets clipboard=unnamedplus, which disables Neovim's built-in OSC 52
  -- fallback. Emit OSC 52 on yank and serve paste from an in-process register
  -- cache so terminals that ignore OSC 52 '?' read queries (such as ttyd) never
  -- block for 10s on paste. SSH and tmux keep Neovim's own OSC 52 and tmux providers.
  local osc52 = require("vim.ui.clipboard.osc52")
  local cache = { ["+"] = {}, ["*"] = {} }
  local function copy(reg)
    local send = osc52.copy(reg)
    return function(lines)
      cache[reg] = lines
      send(lines)
    end
  end

  vim.g.clipboard = {
    name = "osc52-write",
    copy = {
      ["+"] = copy("+"),
      ["*"] = copy("*"),
    },
    paste = {
      ["+"] = function()
        return cache["+"]
      end,
      ["*"] = function()
        return cache["*"]
      end,
    },
  }
end
