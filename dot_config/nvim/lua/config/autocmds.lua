-- Docs: https://www.lazyvim.org/configuration/general
-- Continue list items on <CR> in prose buffers: the markdown ftplugin keeps only the indent,
-- and other buffers align text under the `fb:-` comment leader. Mid-item <CR> splits the item;
-- an empty item outdents, then ends the list. A callback, not <expr>: insert mode evaluates
-- <expr> mappings before earlier queued keys reach the line. Items are written directly, so
-- comment options cannot interfere.
local function continue_list()
  local line = vim.api.nvim_get_current_line()
  local row, col = unpack(vim.api.nvim_win_get_cursor(0))
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
  if not marker or col < #line - #rest then
    -- Insert ahead of pending keys: appending would reorder macros and :normal.
    vim.api.nvim_feedkeys(vim.keycode("<CR>"), "ni", false)
  elseif rest ~= "" then
    vim.api.nvim_buf_set_lines(0, row - 1, row, true, { line:sub(1, col), indent .. marker .. line:sub(col + 1) })
    vim.api.nvim_win_set_cursor(0, { row + 1, #indent + #marker })
  elseif indent ~= "" then
    vim.api.nvim_feedkeys(vim.keycode("<C-d>"), "ni", false)
  else
    vim.api.nvim_set_current_line("")
  end
end

-- Attach on InsertEnter: LazyVim loads this file after the startup buffer was entered, and
-- unnamed scratch buffers never fire FileType.
local prose = { [""] = true, gitcommit = true, markdown = true, text = true }
vim.api.nvim_create_autocmd("InsertEnter", {
  callback = function(event)
    if vim.bo[event.buf].buftype == "" and prose[vim.bo[event.buf].filetype] then
      vim.keymap.set("i", "<CR>", continue_list, { buffer = event.buf, desc = "Continue List" })
    end
  end,
})

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
