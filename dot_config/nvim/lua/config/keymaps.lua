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

-- Review a whole branch: point gitsigns at the merge-base with the default branch so
-- ]h/[h and hunk previews cover every change since the branch started, not only unstaged ones.
local branch_base
map("n", "<leader>gm", function()
  local gitsigns = require("gitsigns")
  if branch_base then
    branch_base = nil
    gitsigns.reset_base(true)
    Snacks.notify.info("Comparing with the index", { title = "Git Base" })
    return
  end
  local root = LazyVim.root.git()
  local function git(...)
    local result = vim.system({ "git", ... }, { cwd = root, text = true }):wait()
    return result.code == 0 and vim.trim(result.stdout) or nil
  end
  local default = git("rev-parse", "--abbrev-ref", "origin/HEAD") or "main"
  local base = git("merge-base", "HEAD", default)
  if not base then
    Snacks.notify.warn("No merge-base with " .. default, { title = "Git Base" })
    return
  end
  branch_base = base
  gitsigns.change_base(base, true)
  Snacks.notify.info(("Comparing with %s (%s)"):format(default, base:sub(1, 7)), { title = "Git Base" })
end, { desc = "Toggle Branch Review Base" })

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
