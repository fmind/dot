-- Docs: https://www.lazyvim.org/plugins/formatting
-- dprint owns these filetypes in projects with a dprint config and passes files its
-- config excludes or has no plugin for through unchanged (deliberately, without a per-save
-- probe); elsewhere Conform falls back to the language server.
local dprint_filetypes = { "json", "jsonc", "markdown", "markdown.mdx", "toml", "yaml" }

return {
  {
    "stevearc/conform.nvim",
    opts = function(_, opts)
      opts.formatters = opts.formatters or {}
      opts.formatters.dprint = { require_cwd = true }
      opts.formatters_by_ft = opts.formatters_by_ft or {}
      for _, filetype in ipairs(dprint_filetypes) do
        opts.formatters_by_ft[filetype] = { "dprint", lsp_format = "fallback" }
      end
      -- Ruff is the single Python formatting and import-order owner.
      opts.formatters_by_ft.python = { "ruff_organize_imports", "ruff_format" }
      return opts
    end,
  },
}
