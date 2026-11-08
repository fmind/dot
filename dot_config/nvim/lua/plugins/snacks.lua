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
          -- fd streams paths in parallel thread order, and Snacks skips sorting on an
          -- empty prompt (default tie-breaker is path length #text). Sort lexicographically
          -- when the prompt is empty while keeping fuzzy score first when filtering.
          files = {
            hidden = true,
            matcher = { sort_empty = true },
            sort = { fields = { "score:desc", "file", "idx" } },
          },
        },
      },
    },
  },
}
