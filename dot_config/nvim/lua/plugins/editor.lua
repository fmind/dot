-- Docs: https://www.lazyvim.org/configuration/plugins
-- General UI overrides and editor plugin fixes
return {
  -- Theme, named by chezmoi so the palette is chosen in one place
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = require("config.theme"),
    },
  },
  -- Which-key preset
  {
    "folke/which-key.nvim",
    opts = {
      preset = "classic",
    },
  },
  -- Fix refactoring.nvim error by ensuring async.nvim dependency is loaded
  {
    "ThePrimeagen/refactoring.nvim",
    dependencies = {
      "lewis6991/async.nvim",
    },
  },
}
