-- Docs: https://writewithharper.com/docs/integrations/neovim
return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        -- mise owns harper-ls. Limit it to prose so code comments stay quiet.
        harper_ls = {
          mason = false,
          filetypes = { "gitcommit", "markdown", "text", "typst" },
        },
      },
    },
  },
}
