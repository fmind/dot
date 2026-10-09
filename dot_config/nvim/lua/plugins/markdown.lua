-- Docs: https://github.com/brianhuster/live-preview.nvim
-- Browser preview in pure Lua: live updates while typing, sync scroll, KaTeX, and Mermaid,
-- without markdown-preview.nvim's Node build. The server binds to 127.0.0.1 only.

-- File the browser was last opened on: <leader>cp closes the preview on that file and
-- retargets it from any other, since the browser tab cannot follow buffer switches.
-- Deleting that buffer (:bd, <leader>bd) also closes the preview.
local previewed

local function close()
  vim.api.nvim_create_augroup("LivePreviewBuffer", { clear = true })
  previewed = nil
  if require("livepreview").is_running() then
    vim.cmd.LivePreview("close")
  end
end

local function toggle()
  local buf = vim.api.nvim_get_current_buf()
  local file = vim.api.nvim_buf_get_name(buf)
  if require("livepreview").is_running() and previewed == file then
    return close()
  end
  -- `start` restarts a running server on the current file and opens its tab.
  vim.cmd.LivePreview("start")
  previewed = file
  vim.api.nvim_create_autocmd("BufDelete", {
    group = vim.api.nvim_create_augroup("LivePreviewBuffer", { clear = true }),
    buffer = buf,
    once = true,
    callback = vim.schedule_wrap(close),
  })
end

return {
  { "iamcco/markdown-preview.nvim", enabled = false },
  {
    "brianhuster/live-preview.nvim",
    cmd = "LivePreview",
    keys = {
      {
        "<leader>cp",
        toggle,
        ft = { "markdown", "asciidoc", "html", "svg" },
        desc = "Live Preview (toggle or switch file)",
      },
    },
  },
}
