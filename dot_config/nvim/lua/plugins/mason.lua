-- Docs: https://github.com/mason-org/mason.nvim#configuration
return {
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      -- Keep mise/project tools ahead of Mason, including previously installed copies.
      opts.PATH = "append"
      if type(opts.ensure_installed) == "table" then
        opts.ensure_installed = vim.tbl_filter(function(tool)
          -- linting.lua disables the Markdown linters, so its formatter condition never fires.
          return tool ~= "markdownlint-cli2" and vim.fn.executable(tool) == 0
        end, opts.ensure_installed)
      end
      return opts
    end,
  },
}
