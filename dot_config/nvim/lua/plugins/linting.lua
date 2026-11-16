-- Docs: https://www.lazyvim.org/plugins/linting
return {
  {
    "mfussenegger/nvim-lint",
    opts = function(_, opts)
      opts.linters_by_ft = opts.linters_by_ft or {}
      -- Markdown is validated by dprint and repository-specific checks.
      opts.linters_by_ft.markdown = {}
      -- nvim-lint lacks require_cwd, so unconfigured sqlfluff enforces ANSI SQL on DuckDB/Postgres/SQLite files.
      for _, filetype in ipairs({ "mysql", "plsql", "sql" }) do
        opts.linters_by_ft[filetype] = {}
      end
      -- OpenTofu replaces the terraform extra's terraform_validate; the extra installs tflint
      -- but never runs it, so lint with the global copy too.
      for _, filetype in ipairs({ "opentofu", "terraform", "tf" }) do
        opts.linters_by_ft[filetype] = { "tofu", "tflint" }
      end
      return opts
    end,
  },
}
