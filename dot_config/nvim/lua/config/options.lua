-- Docs: https://www.lazyvim.org/configuration/general
vim.g.lazyvim_python_lsp = "ty"

for _, provider in ipairs({ "node", "perl", "python3", "ruby" }) do
  vim.g["loaded_" .. provider .. "_provider"] = 0
end

local opt = vim.opt
opt.wrap = true
opt.scrolloff = 15
opt.timeoutlen = 400

-- Prefer xclip on X11 and Crostini (SOMMELIER_VERSION bridges X11 clipboard while wl-clipboard can hang).
-- On Android AVF (local Xwayland never syncs clipboard) and Wayland-less Linux terminals, emit OSC 52 on yank
-- and paste from an in-process cache so terminals ignoring OSC 52 '?' reads never block 10s.
local android_vm = vim.uv.os_uname().release:find("android", 1, true) ~= nil
if
  vim.fn.has("linux") == 1
  and not android_vm
  and (vim.env.DISPLAY or "") ~= ""
  and ((vim.env.SOMMELIER_VERSION or "") ~= "" or (vim.env.WAYLAND_DISPLAY or "") == "")
  and vim.fn.executable("xclip") == 1
then
  -- Wrap xclip paste so empty/non-text selections return `{}` instead of an error; `keepempty=1` preserves linewise yanks.
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
