"""Exercise editor clipboard selection and independent repository review state."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run_lua(tmp_path: Path, script: str, **variables: str) -> None:
    nvim = shutil.which("nvim")
    assert nvim, "Neovim is required by the repository gate"
    probe = tmp_path / "probe.lua"
    probe.write_text(
        "local ok, err = pcall(function()\n"
        + script
        + '\nend)\nif not ok then io.stderr:write(tostring(err) .. "\\n"); vim.cmd.cquit() end\nvim.cmd.qa()\n'
    )
    environment = {
        **os.environ,
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        **variables,
    }
    result = subprocess.run(
        [nvim, "--headless", "-u", "NONE", "-i", "NONE", "-l", str(probe)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(("platform", "display"), [("linux", ""), ("linux", ":0"), ("mac", ":0")])
def test_clipboard_preserves_native_selection_without_linux_x_display(
    tmp_path: Path, platform: str, display: str
) -> None:
    binary = tmp_path / "bin"
    binary.mkdir()
    for tool in ("xclip", "wl-copy", "wl-paste"):
        path = binary / tool
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
    run_lua(
        tmp_path,
        """
local has = vim.fn.has
vim.fn.has = function(feature)
  if feature == "linux" or feature == "mac" then return feature == vim.env.TEST_PLATFORM and 1 or 0 end
  return has(feature)
end
dofile(vim.env.OPTIONS_CONFIG)
if vim.env.TEST_PLATFORM == "linux" and (vim.env.DISPLAY or "") ~= "" then
  assert(vim.g.clipboard.name == "xclip", "X display should use xclip")
else
  assert(vim.g.clipboard == nil, "configuration overrode the native clipboard provider")
  -- Neovim's Vimscript provider calls the real has('mac'), so only a Linux host reaches Wayland.
  if vim.env.TEST_PLATFORM == "linux" and has("linux") == 1 then
    assert(vim.fn["provider#clipboard#Executable"]() == "wl-copy", "Wayland provider was lost")
  end
end
""",
        PATH=f"{binary}:{os.environ['PATH']}",
        DISPLAY=display,
        WAYLAND_DISPLAY="wayland-fixture",
        TEST_PLATFORM=platform,
        OPTIONS_CONFIG=str(ROOT / "dot_config/nvim/lua/config/options.lua"),
    )


def test_branch_review_toggles_buffers_from_independent_repositories(tmp_path: Path) -> None:
    run_lua(
        tmp_path,
        """
local toggle
vim.keymap.set = function(_, key, callback)
  if key == "<leader>gm" then toggle = callback end
end
Snacks = { notify = { info = function() end, warn = function(message) error(message) end } }
local buffers = { vim.api.nvim_get_current_buf(), vim.api.nvim_create_buf(true, false) }
local bases = { [buffers[1]] = "aaaaaaaa", [buffers[2]] = "bbbbbbbb" }
local comparisons = {}
LazyVim = { root = { git = function() return bases[vim.api.nvim_get_current_buf()] end } }
vim.system = function(args, opts)
  return { wait = function()
    return { code = 0, stdout = args[2] == "merge-base" and opts.cwd or "origin/main" }
  end }
end
package.preload.gitsigns = function()
  return {
    change_base = function(base, global)
      local selected = global and buffers or { vim.api.nvim_get_current_buf() }
      for _, buf in ipairs(selected) do
        assert(base == bases[buf], "commit from another repository applied to this buffer")
        comparisons[buf] = base
      end
    end,
    reset_base = function(global)
      local selected = global and buffers or { vim.api.nvim_get_current_buf() }
      for _, buf in ipairs(selected) do comparisons[buf] = nil end
    end,
  }
end
dofile(vim.env.KEYMAP_CONFIG)
assert(toggle, "branch review mapping is missing")
toggle()
assert(comparisons[buffers[1]] == bases[buffers[1]] and comparisons[buffers[2]] == nil)
vim.api.nvim_set_current_buf(buffers[2])
toggle()
assert(comparisons[buffers[1]] == bases[buffers[1]] and comparisons[buffers[2]] == bases[buffers[2]])
toggle()
assert(comparisons[buffers[1]] == bases[buffers[1]] and comparisons[buffers[2]] == nil)
vim.api.nvim_set_current_buf(buffers[1])
toggle()
assert(comparisons[buffers[1]] == nil and comparisons[buffers[2]] == nil)
""",
        KEYMAP_CONFIG=str(ROOT / "dot_config/nvim/lua/config/keymaps.lua"),
    )
