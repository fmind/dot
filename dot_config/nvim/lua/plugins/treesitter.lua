-- Docs: https://github.com/nvim-treesitter/nvim-treesitter#setup
-- Add the Zellij KDL parser; LazyVim's util.dot extra already adds fish.
-- GCC can spend minutes optimizing generated grammars, and nvim-treesitter offers no
-- build-only environment, so CC applies to every child process; preserve an explicit CC.
if not vim.env.CC and vim.fn.executable("clang") == 1 then
  vim.env.CC = "clang"
end

return {
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      if type(opts.ensure_installed) == "table" then
        -- Web parsers stay retired: snacks.image only misses inline images in TSX
        -- documents, like its other optional languages; Markdown images still render.
        local retired = { tsx = true, typescript = true }
        opts.ensure_installed = vim.tbl_filter(function(language)
          return not retired[language]
        end, opts.ensure_installed)
        vim.list_extend(opts.ensure_installed, { "kdl" })
      end
      return opts
    end,
  },
}
