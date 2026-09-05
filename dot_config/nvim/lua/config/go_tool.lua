local M = {}

local function declared_root(tool, filename)
  local root = vim.fs.root(filename, "go.mod")
  if not root then
    return nil
  end
  local result = vim.system({ "go", "mod", "edit", "-json" }, { cwd = root, text = true }):wait()
  if result.code ~= 0 then
    return nil
  end
  local ok, mod = pcall(vim.json.decode, result.stdout)
  if not ok or type(mod.Tool) ~= "table" then
    return nil
  end
  for _, declared in ipairs(mod.Tool) do
    local name = declared.Path and declared.Path:match("([^/]+)$")
    if name == tool then
      return root
    end
  end
  return nil
end

function M.formatter(tool)
  return {
    command = function(_, ctx)
      return declared_root(tool, ctx.filename) and "go" or tool
    end,
    prepend_args = function(_, ctx)
      return declared_root(tool, ctx.filename) and { "tool", tool } or {}
    end,
    cwd = function(_, ctx)
      return declared_root(tool, ctx.filename)
    end,
  }
end

function M.lsp(tool, args)
  return function(dispatchers, config)
    local fallback_root = (config and config.root_dir) or vim.fn.getcwd()
    local root = declared_root(tool, fallback_root)
    local command = root and { "go", "tool", tool } or { tool }
    vim.list_extend(command, args)
    return vim.lsp.rpc.start(command, dispatchers, { cwd = root or fallback_root })
  end
end

return M
