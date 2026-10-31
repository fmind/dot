-- Docs: https://www.lazyvim.org/extras/lang/python
-- The ruff and ty language servers live in lsp.lua with the other servers.
return {
  {
    "mfussenegger/nvim-dap-python",
    optional = true,
    config = function()
      -- uv recreates the adapter environment when Python changes; Mason's
      -- virtualenv can retain a symlink to a removed mise interpreter.
      local python = require("dap-python")
      python.setup("uv")
      -- Resolve from the current file: a repository-level .venv can belong to
      -- another package when Neovim opens a nested Python project.
      python.resolve_python = function()
        local root = vim.fs.root(0, { "pyproject.toml", "setup.cfg", "setup.py", "pytest.ini", ".git" })
        local executable = root and vim.fs.joinpath(root, ".venv", "bin", "python")
        return executable and vim.fn.executable(executable) == 1 and executable or vim.fn.exepath("python3")
      end
    end,
  },
  -- ty discovers the project .venv itself, and dap-python resolves it per file above.
  { "linux-cultist/venv-selector.nvim", enabled = false },
  {
    "jay-babu/mason-nvim-dap.nvim",
    optional = true,
    opts = { automatic_installation = { exclude = { "python" } } },
  },
}
