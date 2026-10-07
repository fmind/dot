-- Docs: https://github.com/mason-org/mason.nvim#configuration
return {
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      -- Keep mise/project tools ahead of Mason, including previously installed copies.
      opts.PATH = "append"
      if type(opts.ensure_installed) == "table" then
        -- dprint replaces the Markdown formatters (formatting.lua) and linters (linting.lua).
        local unused = { ["markdownlint-cli2"] = true, ["markdown-toc"] = true }
        opts.ensure_installed = vim.tbl_filter(function(tool)
          return not unused[tool] and vim.fn.executable(tool) == 0
        end, opts.ensure_installed)
      end
      return opts
    end,
  },
}
