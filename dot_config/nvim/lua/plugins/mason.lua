-- Docs: https://github.com/mason-org/mason.nvim#configuration
return {
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      if type(opts.ensure_installed) == "table" then
        opts.ensure_installed = vim.tbl_filter(function(tool)
          return vim.fn.executable(tool) == 0
        end, opts.ensure_installed)
      end
      return opts
    end,
  },
}
