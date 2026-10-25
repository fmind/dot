-- Docs: https://www.lazyvim.org/plugins/linting
return {
  {
    "mfussenegger/nvim-lint",
    opts = function(_, opts)
      opts.linters_by_ft = opts.linters_by_ft or {}
      -- Markdown is validated by dprint and repository-specific checks.
      opts.linters_by_ft.markdown = {}
      -- OpenTofu replaces the terraform extra's terraform_validate; the extra installs tflint
      -- but never runs it, so lint with the global copy too.
      opts.linters_by_ft.terraform = { "tofu", "tflint" }
      opts.linters_by_ft.tf = { "tofu", "tflint" }
      return opts
    end,
  },
}
