-- Docs: https://github.com/nvim-treesitter/nvim-treesitter#commands
-- Lazy's build callbacks start asynchronous parser work; headless tasks must wait.
local ok, err = pcall(function()
  local timeout = 15 * 60 * 1000
  local ts = require("nvim-treesitter")
  local languages = LazyVim.opts("nvim-treesitter").ensure_installed
  local info = require("nvim-treesitter.config").get_install_dir("parser-info")
  -- LazyVim starts missing installs when the module loads. Joining them through
  -- install() has a separate 60s timeout, too short for large grammars such as gitcommit.
  assert(
    vim.wait(timeout, function()
      local installed = ts.get_installed("parsers")
      return vim.iter(languages):all(function(language)
        -- The shared library appears before queries and revision metadata are published.
        return vim.list_contains(installed, language)
          and vim.uv.fs_stat(vim.fs.joinpath(info, language .. ".revision")) ~= nil
      end)
    end),
    "Tree-sitter parsers are still missing after installation"
  )
  assert(ts.update(languages, { summary = true }):wait(timeout), "Tree-sitter parser update failed")
end)

if not ok then
  vim.api.nvim_err_writeln(tostring(err))
  vim.cmd.cquit()
end
