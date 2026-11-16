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
      -- Require an explicit .sqlfluff config so project dialects (DuckDB, PostgreSQL, SQLite) are respected.
      opts.formatters.sqlfluff = {
        args = { "format", "-" },
        cwd = require("conform.util").root_file({ ".sqlfluff" }),
        require_cwd = true,
      }
      -- Ruff is the single Python formatting and import-order owner.
      opts.formatters_by_ft.python = { "ruff_organize_imports", "ruff_format" }
      -- The terraform extra calls a terraform binary; the workstation installs OpenTofu instead.
      for _, filetype in ipairs({ "hcl", "opentofu", "terraform", "terraform-vars", "tf" }) do
        opts.formatters_by_ft[filetype] = { "tofu_fmt" }
      end
      return opts
    end,
  },
}
