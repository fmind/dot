-- Docs: https://www.lazyvim.org/configuration/general
local map = vim.keymap.set

-- Access literal (physical) line movement via gj/gk.
-- Plain j/k are left to LazyVim's count-aware default (v:count == 0 ? 'gj' : 'j'),
-- so {count}j/{count}k keep jumping real lines with relativenumber.
map({ "n", "v" }, "gj", "j", { silent = true })
map({ "n", "v" }, "gk", "k", { silent = true })

-- Keep forward buffer order while Snacks preserves splits and prompts before deletion.
local function bdelete_next()
  local buf = vim.api.nvim_get_current_buf()
  local win = vim.api.nvim_get_current_win()
  local buffers = vim.fn.getbufinfo({ buflisted = 1 })
  local next_buf
  for _, info in ipairs(buffers) do
    if info.bufnr > buf then
      next_buf = info.bufnr
      break
    end
  end
  next_buf = next_buf or (buffers[1] and buffers[1].bufnr)
  Snacks.bufdelete(buf)
  -- Cancellation leaves the original buffer listed and the current window untouched.
  if vim.api.nvim_buf_is_valid(buf) and vim.bo[buf].buflisted then
    return
  end
  if next_buf and next_buf ~= buf and vim.api.nvim_buf_is_valid(next_buf) and vim.api.nvim_win_is_valid(win) then
    vim.api.nvim_win_set_buf(win, next_buf)
  end
end
map("n", "<leader>bd", bdelete_next, { desc = "Delete Buffer (next)" })

-- Display full path in a floating notification and copy to clipboards.
map("n", "<leader>fh", function()
  local path = vim.fn.expand("%:p")
  if path == "" then
    Snacks.notify.warn("Buffer has no file path", { title = "File Path" })
    return
  end
  vim.fn.setreg("+", path)
  vim.fn.setreg('"', path)
  Snacks.notify.info(path, { title = "Full Path (Copied)" })
end, { desc = "Show and Copy Full Path" })
