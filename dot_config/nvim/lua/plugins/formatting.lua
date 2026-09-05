local go_tool = require("config.go_tool")

local function root_file(filename, names)
  return vim.fs.root(filename, names)
end

local dprint_filetypes =
  { json = true, jsonc = true, markdown = true, ["markdown.mdx"] = true, toml = true, yaml = true }
local biome_filetypes = {
  css = true,
  graphql = true,
  javascript = true,
  javascriptreact = true,
  json = true,
  jsonc = true,
  scss = true,
  typescript = true,
  typescriptreact = true,
}
local prettier_filetypes = {
  css = true,
  graphql = true,
  handlebars = true,
  html = true,
  htmlangular = true,
  javascript = true,
  javascriptreact = true,
  json = true,
  jsonc = true,
  less = true,
  markdown = true,
  ["markdown.mdx"] = true,
  scss = true,
  typescript = true,
  typescriptreact = true,
  vue = true,
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
  -- A missing or broken claimed formatter must fail visibly instead of handing the file to another owner.
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
  for path in result.stdout:gmatch("[^\r\n]+") do
    if vim.fs.normalize(path) == target then
      return true
    end
  end
  return false
end

local function prettier_project(filename)
  local markers = {
    [".prettierrc"] = true,
    [".prettierrc.json"] = true,
    [".prettierrc.yml"] = true,
    [".prettierrc.yaml"] = true,
    [".prettierrc.json5"] = true,
    [".prettierrc.js"] = true,
    [".prettierrc.cjs"] = true,
    [".prettierrc.mjs"] = true,
    [".prettierrc.ts"] = true,
    [".prettierrc.cts"] = true,
    [".prettierrc.mts"] = true,
    [".prettierrc.toml"] = true,
    ["prettier.config.js"] = true,
    ["prettier.config.cjs"] = true,
    ["prettier.config.mjs"] = true,
    ["prettier.config.ts"] = true,
    ["prettier.config.cts"] = true,
    ["prettier.config.mts"] = true,
  }
  return root_file(filename, function(name, path)
    if markers[name] then
      return true
    end
    if name ~= "package.json" then
      return false
    end
    local file = io.open(vim.fs.joinpath(path, name), "r")
    if not file then
      return false
    end
    local ok, package = pcall(vim.json.decode, file:read("*a"))
    file:close()
    return ok and package.prettier ~= nil
  end) ~= nil
end

local function biome_claims(filename)
  local root = root_file(filename, { "biome.json", "biome.jsonc", ".biome.json", ".biome.jsonc" })
  if not root then
    return false
  end
  if vim.fn.executable("biome") == 0 or not vim.uv.fs_stat(filename) then
    return true
  end
  -- A config can claim only TypeScript while excluding nearby JSON or lockfiles.
  -- Ask the formatter itself; an invalid config/report remains a visible failure.
  local result = vim
    .system({ "biome", "format", "--reporter=json", filename }, { cwd = root, text = true, timeout = 2000 })
    :wait()
  local ok, report = pcall(vim.json.decode, result.stdout or "")
  if not ok or type(report.summary) ~= "table" then
    return true
  end
  local summary = report.summary
  return (summary.changed or 0) + (summary.unchanged or 0) + (summary.errors or 0) + (summary.skipped or 0) > 0
end

local function project_owner(filename, filetype)
  if dprint_filetypes[filetype] and dprint_claims(filename) then
    return "dprint"
  end
  if biome_filetypes[filetype] and biome_claims(filename) then
    return "biome"
  end
  if prettier_filetypes[filetype] and prettier_project(filename) then
    return "prettier"
  end
end

local function owned_formatters(current, filetype)
  return function(bufnr)
    local filename = vim.api.nvim_buf_get_name(bufnr)
    local owner = project_owner(filename, filetype)
    local selected = owner and { owner } or {}
    local existing = type(current) == "function" and current(bufnr) or current or {}
    for _, formatter in ipairs(existing) do
      if formatter ~= "dprint" and formatter ~= "biome" and formatter ~= "biome-check" and formatter ~= "prettier" then
        table.insert(selected, formatter)
      end
    end
    selected.lsp_format = owner and "never" or "fallback"
    return selected
  end
end

return {
  {
    "stevearc/conform.nvim",
    opts = function(_, opts)
      opts.formatters_by_ft = opts.formatters_by_ft or {}
      local owned_filetypes =
        vim.tbl_keys(vim.tbl_extend("force", {}, dprint_filetypes, biome_filetypes, prettier_filetypes))
      for _, filetype in ipairs(owned_filetypes) do
        opts.formatters_by_ft[filetype] = owned_formatters(opts.formatters_by_ft[filetype], filetype)
      end
      opts.formatters_by_ft.templ = { "templ" }

      opts.formatters = opts.formatters or {}
      opts.formatters.goimports = go_tool.formatter("goimports")
      opts.formatters.gofumpt = go_tool.formatter("gofumpt")
      opts.formatters.templ = go_tool.formatter("templ")

      return opts
    end,
  },
}
