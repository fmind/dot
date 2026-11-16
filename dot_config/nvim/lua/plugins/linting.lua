-- Docs: https://www.lazyvim.org/plugins/linting
return {
  {
    "mfussenegger/nvim-lint",
    opts = function(_, opts)
      opts.linters_by_ft = opts.linters_by_ft or {}
      -- Markdown is validated by dprint and repository-specific checks.
      opts.linters_by_ft.markdown = {}
      -- Only lint SQL when a repo declares .sqlfluff or .sqruff so project dialects stay explicit.
      opts.linters = opts.linters or {}
      opts.linters.sqlfluff = {
        condition = function(ctx)
          return vim.fs.root(ctx.filename, { ".sqlfluff" }) ~= nil
        end,
      }
      local sqruff_severities = {
        Error = vim.diagnostic.severity.ERROR,
        Warning = vim.diagnostic.severity.WARN,
        Information = vim.diagnostic.severity.INFO,
        Hint = vim.diagnostic.severity.HINT,
      }
      opts.linters.sqruff = {
        cmd = "sqruff",
        args = {
          "lint",
          "--format",
          "json",
          "--stdin-filename",
          function()
            return vim.api.nvim_buf_get_name(0)
          end,
          "-",
        },
        stdin = true,
        stream = "both",
        ignore_exitcode = true,
        condition = function(ctx)
          return vim.fs.root(ctx.filename, { ".sqruff" }) ~= nil
        end,
        parser = function(output)
          local trimmed = vim.trim(output or "")
          if trimmed == "" then
            return {}
          end
          local ok, decoded = pcall(vim.json.decode, trimmed, { luanil = { object = true, array = true } })
          if not ok or type(decoded) ~= "table" then
            return {
              {
                lnum = 0,
                col = 0,
                end_lnum = 0,
                end_col = 0,
                severity = vim.diagnostic.severity.ERROR,
                source = "sqruff",
                message = "sqruff failed: " .. trimmed,
              },
            }
          end
          local diagnostics = {}
          for _, items in pairs(decoded) do
            if type(items) == "table" then
              for _, item in ipairs(items) do
                if type(item) == "table" then
                  local range = type(item.range) == "table" and item.range or {}
                  local start_pos = type(range.start) == "table" and range.start or {}
                  local end_pos = type(range["end"]) == "table" and range["end"] or start_pos
                  local start_line = type(start_pos.line) == "number" and start_pos.line or 1
                  local start_char = type(start_pos.character) == "number" and start_pos.character or 1
                  local end_line = type(end_pos.line) == "number" and end_pos.line or start_line
                  local end_char = type(end_pos.character) == "number" and end_pos.character or start_char
                  local lnum = math.max(0, start_line - 1)
                  local col = math.max(0, start_char - 1)
                  local end_lnum = math.max(lnum, end_line - 1)
                  local end_col = math.max(col, end_char - 1)
                  table.insert(diagnostics, {
                    lnum = lnum,
                    col = col,
                    end_lnum = end_lnum,
                    end_col = end_col,
                    severity = sqruff_severities[item.severity] or vim.diagnostic.severity.WARN,
                    source = type(item.source) == "string" and item.source or "sqruff",
                    code = type(item.code) == "string" and item.code or nil,
                    message = type(item.message) == "string" and item.message or "",
                  })
                end
              end
            end
          end
          return diagnostics
        end,
      }
      for _, filetype in ipairs({ "mysql", "plsql", "sql" }) do
        opts.linters_by_ft[filetype] = { "sqlfluff", "sqruff" }
      end
      -- OpenTofu replaces the terraform extra's terraform_validate; the extra installs tflint
      -- but never runs it, so lint with the global copy too.
      for _, filetype in ipairs({ "opentofu", "terraform", "tf" }) do
        opts.linters_by_ft[filetype] = { "tofu", "tflint" }
      end
      return opts
    end,
  },
}
