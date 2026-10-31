-- Docs: https://www.lazyvim.org/plugins/lsp · https://mise.jdx.dev/ide-integration.html
return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        -- Neovim is a review tool on this workstation: lua_ls held about 900 MiB per editor for a
        -- handful of Lua files, which stylua (`mise run check:lua`) still checks.
        lua_ls = { enabled = false },
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
        -- mise owns the Python servers; Mason still supplies other languages.
        ruff = { mason = false },
        -- The terraform extra enables terraformls; use OpenTofu's language server instead.
        terraformls = { enabled = false },
        tofu_ls = {},
        ty = {
          mason = false,
          -- Neovim disables this on Linux by default. ty needs notifications
          -- for imports and configuration changed by tools outside the editor.
          capabilities = {
            workspace = { didChangeWatchedFiles = { dynamicRegistration = true } },
          },
        },
      },
    },
  },
}
