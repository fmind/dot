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
  -- fmind/theme owns the palette; skip the colorschemes bundled with LazyVim.
  { "folke/tokyonight.nvim", enabled = false },
  { "catppuccin/nvim", name = "catppuccin", enabled = false },
  -- Tab accepts completions and Enter always inserts a newline. LazyVim chains snippet
  -- jumps and Copilot suggestions onto Tab for this preset.
  {
    "saghen/blink.cmp",
    opts = {
      keymap = { preset = "super-tab" },
    },
  },
  -- The util.chezmoi extra applies a source file on every save; keep apply explicit.
  { "xvzc/chezmoi.nvim", init = function() end },
  -- Which-key preset
  {
    "folke/which-key.nvim",
    opts = {
      preset = "classic",
    },
  },
}
