-- Docs: https://www.lazyvim.org/configuration/general
-- Markdown: no auto-wrap while typing. Soft wrap/linebreak are set globally in
-- options.lua; textwidth stays untouched so EditorConfig max_line_length still drives gq.
vim.api.nvim_create_autocmd("FileType", {
  pattern = "markdown",
  callback = function()
    vim.opt_local.formatoptions:remove("t")
  end,
})

-- Reload files changed by agents in other panes. LazyVim only checks on FocusGained and
-- terminal exit, which never fire while Neovim keeps focus. Insert mode is left alone.
vim.api.nvim_create_autocmd({ "BufEnter", "CursorHold" }, {
  group = vim.api.nvim_create_augroup("checktime_idle", { clear = true }),
  callback = function()
    if vim.bo.buftype == "" and vim.fn.getcmdwintype() == "" then
      vim.cmd.checktime()
    end
  end,
})
