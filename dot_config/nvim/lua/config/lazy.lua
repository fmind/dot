-- Docs: https://www.lazyvim.org/configuration/lazy.nvim
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
  install = { colorscheme = { require("config.theme") } },
  -- `mise run upgrade` owns plugin updates and captures the lockfile into chezmoi;
  -- in-editor updates would drift from the source and be reverted on apply.
  checker = { enabled = false },
  performance = {
    rtp = {
      disabled_plugins = {
        "gzip",
        "netrwPlugin",
        "tarPlugin",
        "tohtml",
        "tutor",
        "zipPlugin",
      },
    },
  },
})
