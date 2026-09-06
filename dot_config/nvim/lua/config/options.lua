-- Docs: https://www.lazyvim.org/configuration/general
-- Select the Python analyzer through LazyVim so only ty and Ruff are enabled.
vim.g.lazyvim_python_lsp = "ty"

local opt = vim.opt

-- Enable soft wrapping
opt.wrap = true
opt.linebreak = true

-- Scroll offset context
opt.scrolloff = 15

-- Substitute options
opt.gdefault = true

-- Keymap timeouts
opt.timeoutlen = 400

-- System clipboard synchronization
opt.clipboard:append("unnamedplus")

-- Prefer xclip on Linux/ChromeOS to avoid wl-clipboard hanging in Wayland containers
if vim.fn.executable("xclip") == 1 then
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
end

-- Resolve underlying filetype for chezmoi template files (*.tmpl)
vim.filetype.add({
  extension = {
    tmpl = function()
      return "template",
        function(bufnr)
          if vim.bo[bufnr].commentstring == "" then
            vim.bo[bufnr].commentstring = "{{/* %s */}}"
          end
        end
    end,
  },
  pattern = {
    [".*%.(%w+)%.tmpl"] = function(path, bufnr, ext)
      if path:find("symlink_") then
        return nil
      end
      local buf_arg = (bufnr and bufnr > 0 and vim.api.nvim_buf_is_valid(bufnr)) and bufnr or nil
      return vim.filetype.match({ filename = "file." .. ext, buf = buf_arg })
    end,
    [".*gitconfig.*%.tmpl"] = "gitconfig",
    [".*ghostty/config%.tmpl"] = "conf",
  },
})
