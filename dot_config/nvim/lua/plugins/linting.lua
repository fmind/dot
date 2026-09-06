-- Docs: https://www.lazyvim.org/plugins/linting
return {
  {
    "mfussenegger/nvim-lint",
    opts = function(_, opts)
      opts.linters_by_ft = opts.linters_by_ft or {}
      -- Markdown is validated by dprint and repository-specific checks.
      opts.linters_by_ft.markdown = {}
      return opts
    end,
  },
}
