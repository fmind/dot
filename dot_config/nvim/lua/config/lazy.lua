local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local lazyrepo = "https://github.com/folke/lazy.nvim.git"
  local staging = lazypath .. ".tmp." .. vim.fn.getpid()
  local bootstrap_timeout = vim.g.lazy_bootstrap_timeout_ms or 120000
  vim.fn.mkdir(vim.fs.dirname(lazypath), "p")
  local result = vim
    .system({ "git", "clone", "--filter=blob:none", "--branch=stable", lazyrepo, staging }, {
      text = true,
      timeout = bootstrap_timeout,
    })
    :wait()
  if result.code ~= 0 then
    -- Only remove the directory owned by this bootstrap attempt; an existing checkout is never touched.
    vim.fn.delete(staging, "rf")
    local detail = result.stderr ~= "" and result.stderr or "git clone timed out or failed"
    vim.api.nvim_echo({ { "Failed to clone lazy.nvim:\n" .. detail, "ErrorMsg" } }, true, {})
    os.exit(1)
  end
  local renamed, rename_error = (vim.uv or vim.loop).fs_rename(staging, lazypath)
  if not renamed then
    vim.fn.delete(staging, "rf")
    vim.api.nvim_echo({ { "Failed to publish lazy.nvim: " .. tostring(rename_error), "ErrorMsg" } }, true, {})
    os.exit(1)
  end
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
  spec = {
    { "LazyVim/LazyVim", import = "lazyvim.plugins" },
    { import = "plugins" },
  },
  defaults = {
    lazy = false,
    version = false,
  },
  rocks = {
    enabled = false,
  },
  git = {
    -- copilot.lua vendors its cross-platform LSP runtime, so a cold filtered
    -- checkout can exceed Lazy's two-minute default on ordinary connections.
    timeout = 600,
  },
  install = { colorscheme = { "tokyonight-moon" } },
  checker = {
    enabled = true,
    notify = false,
  },
  performance = {
    rtp = {
      disabled_plugins = {
        "gzip",
        "matchit",
        "matchparen",
        "netrwPlugin",
        "tarPlugin",
        "tohtml",
        "tutor",
        "zipPlugin",
      },
    },
  },
})
