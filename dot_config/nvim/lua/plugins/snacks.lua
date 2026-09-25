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
          -- Match file search: include dotfiles while respecting ignore rules.
          grep = { hidden = true, ignored = false, exclude = { ".git" } },
          grep_word = { hidden = true, ignored = false, exclude = { ".git" } },
          -- Git roots from recently opened files work across machine layouts.
          projects = { recent = true },
          files = {
            hidden = true,
            ignored = false,
            exclude = {
              ".git",
              "*.png",
              "*.webp",
              "*.jpg",
              "*.jpeg",
              "*.gif",
              "*.ico",
              "*.bmp",
              "*.tiff",
              "*.avif",
              "*.heic",
              "*.pdf",
              "*.zip",
              "*.tar",
              "*.gz",
              "*.7z",
              "*.mp3",
              "*.mp4",
              "*.mov",
              "*.webm",
              "*.woff",
              "*.woff2",
              "*.ttf",
              "*.eot",
              "*.otf",
            },
          },
        },
      },
    },
  },
}
