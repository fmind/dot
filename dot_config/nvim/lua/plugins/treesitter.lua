-- Docs: https://github.com/nvim-treesitter/nvim-treesitter#setup
-- Add the parsers used by the managed shell and project tooling.
-- GCC can spend minutes optimizing generated grammars; preserve an explicit CC.
if not vim.env.CC and vim.fn.executable("clang") == 1 then
  vim.env.CC = "clang"
end

return {
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      if type(opts.ensure_installed) == "table" then
        local retired = {
          angular = true,
          go = true,
          gomod = true,
          gosum = true,
          gowork = true,
          templ = true,
          tsx = true,
          typescript = true,
        }
        opts.ensure_installed = vim.tbl_filter(function(language)
          return not retired[language]
        end, opts.ensure_installed)
        vim.list_extend(opts.ensure_installed, { "kdl", "fish" })
      end
      return opts
    end,
  },
}
