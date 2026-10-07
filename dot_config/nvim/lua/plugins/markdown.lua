-- Docs: https://github.com/brianhuster/live-preview.nvim
-- Browser preview in pure Lua: live updates while typing, sync scroll, KaTeX, and Mermaid,
-- without markdown-preview.nvim's Node build. The server binds to 127.0.0.1 only.
return {
  { "iamcco/markdown-preview.nvim", enabled = false },
  {
    "brianhuster/live-preview.nvim",
    cmd = "LivePreview",
    keys = {
      {
        "<leader>cp",
        function()
          vim.cmd.LivePreview(require("livepreview").is_running() and "close" or "start")
        end,
        ft = { "markdown", "asciidoc", "html", "svg" },
        desc = "Live Preview",
      },
    },
  },
}
