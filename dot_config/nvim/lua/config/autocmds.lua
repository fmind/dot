-- Docs: https://www.lazyvim.org/configuration/general
-- Markdown: no auto-wrap while typing. Soft wrap/linebreak are set globally in
-- options.lua; textwidth stays untouched so EditorConfig max_line_length still drives gq.
vim.api.nvim_create_autocmd("FileType", {
  pattern = "markdown",
  callback = function()
    vim.opt_local.formatoptions:remove("t")
  end,
})
