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
        vim.list_extend(opts.ensure_installed, { "kdl", "just", "fish", "templ" })
      end
      return opts
    end,
  },
}
