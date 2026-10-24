-- Docs: https://mise.jdx.dev/ide-integration.html
return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        -- `mise lsp` (mise 2026.10.18+) checks mise config files for unknown or deprecated keys,
        -- task names, and tool names, and ignores other TOML files. dprint keeps TOML formatting.
        mise = {
          mason = false,
          cmd = { "mise", "lsp" },
          -- It reads configs from the opened file's path; start it outside any project, because
          -- mise run from this repository's dot_config/ tracks the source copy of the global config.
          cmd_cwd = vim.env.HOME,
          filetypes = { "toml" },
          root_markers = { "mise.toml", ".mise.toml", ".git" },
          init_options = { formatting = false },
        },
      },
    },
  },
}
