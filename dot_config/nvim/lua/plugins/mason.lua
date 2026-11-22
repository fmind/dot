-- Docs: https://github.com/mason-org/mason.nvim#configuration
return {
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      -- Keep mise/project tools ahead of Mason, including previously installed copies.
      opts.PATH = "append"
      if type(opts.ensure_installed) == "table" then
        -- dprint replaces the Markdown formatters (formatting.lua) and linters (linting.lua).
        -- Mason's sqlfluff venv symlinks an exact Python patch that breaks on mise upgrades;
        -- projects pin dialect-configured sqlfluff themselves.
        -- The global mise config provides stylua outside projects (tflint and opentofu are
        -- project-pinned): an inactive mise shim counts as executable, so Mason skips it anyway.
        local unused = { ["markdownlint-cli2"] = true, ["markdown-toc"] = true, ["sqlfluff"] = true }
        opts.ensure_installed = vim.tbl_filter(function(tool)
          return not unused[tool] and vim.fn.executable(tool) == 0
        end, opts.ensure_installed)
      end
      return opts
    end,
  },
}
