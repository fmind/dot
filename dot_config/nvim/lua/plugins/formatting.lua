-- Docs: https://www.lazyvim.org/plugins/formatting
local dprint_filetypes = {
  json = true,
  jsonc = true,
  markdown = true,
  ["markdown.mdx"] = true,
  toml = true,
  yaml = true,
}

local function dprint_claims(filename)
  local config = vim.fs.find({ "dprint.json", "dprint.jsonc", ".dprint.json", ".dprint.jsonc" }, {
    path = vim.fs.dirname(filename),
    upward = true,
  })[1]
  if not config then
    return false
  end
  -- A broken claimed formatter remains visible instead of silently changing ownership.
  if vim.fn.executable("dprint") == 0 then
    return true
  end
  local result = vim
    .system({ "dprint", "file-paths", "--config", config, filename }, {
      cwd = vim.fs.dirname(config),
      text = true,
      timeout = 2000,
    })
    :wait()
  if result.code ~= 0 then
    return true
  end
  local target = vim.fs.normalize(filename)
  return vim.iter(vim.split(result.stdout, "\n", { trimempty = true })):any(function(path)
    return vim.fs.normalize(path) == target
  end)
end

return {
  {
    "stevearc/conform.nvim",
    opts = function(_, opts)
      opts.formatters_by_ft = opts.formatters_by_ft or {}
      for filetype in pairs(dprint_filetypes) do
        local current = opts.formatters_by_ft[filetype]
        opts.formatters_by_ft[filetype] = function(bufnr)
          local selected = {}
          local claimed = dprint_claims(vim.api.nvim_buf_get_name(bufnr))
          if claimed then
            table.insert(selected, "dprint")
          end
          local existing = type(current) == "function" and current(bufnr) or current or {}
          for _, formatter in ipairs(existing) do
            if formatter ~= "dprint" and not claimed then
              table.insert(selected, formatter)
            end
          end
          selected.lsp_format = claimed and "never" or "fallback"
          return selected
        end
      end
      -- Ruff is the single Python formatting and import-order owner.
      opts.formatters_by_ft.python = { "ruff_organize_imports", "ruff_format" }
      return opts
    end,
  },
}
