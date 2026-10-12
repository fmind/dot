-- Docs: https://www.lazyvim.org/configuration/general
-- Continue Markdown list items on <CR>; the markdown ftplugin keeps only the indent.
-- An empty item outdents, then ends the list. This runs as a callback, not <expr>: insert
-- mode evaluates <expr> mappings before earlier queued keys reach the line.
local function continue_list()
  local line = vim.api.nvim_get_current_line()
  local indent, marker, rest = line:match("^(%s*)([-*+]%s+)(.*)$")
  if not marker then
    local number, delimiter, space
    indent, number, delimiter, space, rest = line:match("^(%s*)(%d+)([.)])(%s+)(.*)$")
    marker = number and (number + 1) .. delimiter .. space
  end
  local text = rest and rest:match("^%[[ xX]%]%s+(.*)$")
  if text then
    marker, rest = marker .. "[ ] ", text
  end
  local keys = "<CR>"
  if marker and vim.fn.col(".") > #line then
    if rest ~= "" then
      keys = "<CR>" .. marker -- autoindent copies the item's indent
    elseif indent ~= "" then
      keys = "<C-d>"
    else
      vim.api.nvim_set_current_line("")
      return
    end
  end
  -- Insert ahead of pending keys: appending would reorder macros and :normal.
  vim.api.nvim_feedkeys(vim.keycode(keys), "ni", false)
end

-- Markdown: no auto-wrap while typing. Soft wrap/linebreak are set globally in
-- options.lua; textwidth stays untouched so EditorConfig max_line_length still drives gq.
vim.api.nvim_create_autocmd("FileType", {
  pattern = "markdown",
  callback = function()
    vim.opt_local.formatoptions:remove("t")
    vim.keymap.set("i", "<CR>", continue_list, { buffer = true, desc = "Continue List" })
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
