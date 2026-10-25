-- Docs: https://www.lazyvim.org/plugins/lsp
return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        -- Neovim is a review tool on this workstation: lua_ls held about 900 MiB per editor for a
        -- handful of Lua files, which stylua (`mise run check:lua`) still checks.
        lua_ls = { enabled = false },
      },
    },
  },
}
