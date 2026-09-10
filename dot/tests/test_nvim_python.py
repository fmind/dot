"""Check Python LSP behavior with Neovim and ty, without downloading plugins."""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ty_refreshes_imports_changed_outside_the_editor(tmp_path: Path) -> None:
    nvim = shutil.which("nvim")
    ty = shutil.which("ty")
    assert nvim, "Neovim is required by the repository gate"
    assert ty, "ty is required by the repository gate"
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "lsp-fixture"\nversion = "0.0.0"\n')
    (tmp_path / "dependency.py").write_text('value: str = "wrong"\n')
    (tmp_path / "main.py").write_text("from dependency import value\nresult: int = value\n")
    script = tmp_path / "probe.lua"
    script.write_text(
        """
local ok, err = pcall(function()
  local specs = dofile(vim.env.PYTHON_LSP_CONFIG)
  local config = specs[1].opts.servers.ty
  config.cmd = { vim.env.TY_EXECUTABLE, "server" }
  config.filetypes = { "python" }
  config.root_dir = vim.env.LSP_PROJECT
  vim.lsp.config("ty", config)
  vim.lsp.enable("ty")
  vim.cmd.edit(vim.env.LSP_PROJECT .. "/main.py")
  vim.bo.filetype = "python"
  local function type_errors()
    return vim.tbl_filter(function(diagnostic)
      return diagnostic.code == "invalid-assignment"
    end, vim.diagnostic.get(0))
  end
  assert(vim.wait(15000, function() return #type_errors() == 1 end, 50),
    "ty did not report the initial imported type error")
  -- Change an unopened dependency without sending didChange from a buffer.
  vim.fn.writefile({ "value: int = 42" }, vim.env.LSP_PROJECT .. "/dependency.py")
  assert(vim.wait(15000, function() return #type_errors() == 0 end, 50),
    "ty kept stale diagnostics after the dependency changed on disk")
  vim.lsp.stop_client(vim.lsp.get_clients())
end)
if not ok then
  io.stderr:write(tostring(err) .. "\\n")
  vim.cmd.cquit()
end
vim.cmd.qa()
"""
    )
    environment = {
        **os.environ,
        "PYTHON_LSP_CONFIG": str(ROOT / "dot_config/nvim/lua/plugins/python.lua"),
        "TY_EXECUTABLE": ty,
        "LSP_PROJECT": str(tmp_path),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
    }
    result = subprocess.run(
        [nvim, "--headless", "-u", "NONE", "-i", "NONE", "-l", str(script)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
