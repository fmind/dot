-- Docs: https://github.com/folke/snacks.nvim#configuration
return {
  {
    "folke/snacks.nvim",
    opts = {
      scroll = { enabled = false },
      -- Zellij 0.45 gained Kitty graphics, but Snacks still marks every Zellij
      -- session unsupported. Keep normal detection everywhere else.
      image = { enabled = true, force = vim.env.ZELLIJ ~= nil },
      picker = {
        sources = {
          -- Include dotfiles while respecting ignore rules; Snacks already skips .git.
          grep = { hidden = true },
          grep_word = { hidden = true },
          files = { hidden = true },
        },
      },
    },
  },
}
