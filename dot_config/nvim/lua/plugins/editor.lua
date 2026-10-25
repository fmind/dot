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
  -- jumps onto Tab for this preset.
  {
    "saghen/blink.cmp",
    opts = {
      keymap = { preset = "super-tab" },
    },
  },
  -- The util.chezmoi extra applies any opened source file on save; keep that explicit.
  -- Its <leader>sz picker still edits targets with --watch, like `chezmoi edit --watch`.
  { "xvzc/chezmoi.nvim", init = function() end },
  -- Which-key preset
  {
    "folke/which-key.nvim",
    opts = {
      preset = "classic",
    },
  },
}
