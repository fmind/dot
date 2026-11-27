"""Exercise editor clipboard selection, Python LSP, repository review state, and list editing."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from repo_helpers import ROOT


def run_lua(tmp_path: Path, script: str, *, timeout: int = 30, **variables: str) -> None:
    nvim = shutil.which("nvim")
    assert nvim, "Neovim is required by the repository gate"
    probe = tmp_path / "probe.lua"
    # TEST_KERNEL fakes the kernel release, which tells Android's Linux terminal VM apart.
    probe.write_text(
        "local release = vim.env.TEST_KERNEL\n"
        "if release then\n"
        "  local uname = vim.uv.os_uname\n"
        "  vim.uv.os_uname = function() local info = uname(); info.release = release; return info end\n"
        "end\n"
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
        timeout=timeout,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


LINUX_KERNEL = "6.12.99-generic-fixture"
ANDROID_KERNEL = "6.12.93-android16-6-fixture"


@pytest.mark.parametrize(
    ("platform", "display", "kernel"),
    [
        ("linux", "", LINUX_KERNEL),
        ("linux", ":0", LINUX_KERNEL),
        ("linux", ":0", ANDROID_KERNEL),
        ("mac", ":0", LINUX_KERNEL),
    ],
    ids=["linux-wayland", "wayland-desktop", "android-vm-wayland", "mac"],
)
def test_clipboard_keeps_native_wayland_selection(tmp_path: Path, platform: str, display: str, kernel: str) -> None:
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
assert(vim.g.clipboard == nil, "configuration overrode the native clipboard provider")
-- Neovim's Vimscript provider calls the real has('mac'), so only a Linux host reaches Wayland.
if vim.env.TEST_PLATFORM == "linux" and has("linux") == 1 then
  assert(vim.fn["provider#clipboard#Executable"]() == "wl-copy", "Wayland provider was lost")
end
""",
        PATH=f"{binary}:{os.environ['PATH']}",
        DISPLAY=display,
        WAYLAND_DISPLAY="wayland-fixture",
        TEST_KERNEL=kernel,
        TEST_PLATFORM=platform,
        OPTIONS_CONFIG=str(ROOT / "dot_config/nvim/lua/config/options.lua"),
    )


@pytest.mark.parametrize(
    ("display", "kernel", "ssh", "tmux", "expected"),
    [
        ("", LINUX_KERNEL, "", "", "osc52-write"),
        (":0", ANDROID_KERNEL, "", "", "osc52-write"),
        (":0", LINUX_KERNEL, "", "", "xclip"),
        ("", LINUX_KERNEL, "10.0.0.1 1 10.0.0.2 22", "", "none"),
        ("", LINUX_KERNEL, "", "tmux-socket,1,0", "none"),
    ],
    ids=["no-display", "android-vm", "x11-desktop", "ssh", "tmux"],
)
def test_linux_without_wayland_uses_xclip_on_x11_else_osc52_outside_ssh_and_tmux(
    tmp_path: Path, display: str, kernel: str, ssh: str, tmux: str, expected: str
) -> None:
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "xclip").write_text("#!/bin/sh\nexit 0\n")
    (binary / "xclip").chmod(0o755)
    run_lua(
        tmp_path,
        """
vim.fn.has = function(feature) return feature == "linux" and 1 or 0 end
local sent
package.preload["vim.ui.clipboard.osc52"] = function()
  return { copy = function(reg) return function(lines) sent = { reg, lines } end end }
end
dofile(vim.env.OPTIONS_CONFIG)
if vim.env.EXPECTED == "none" then
  assert(vim.g.clipboard == nil, "SSH and tmux must keep Neovim's own clipboard providers")
  return
end
if vim.env.EXPECTED == "xclip" then
  assert(vim.g.clipboard.name == "xclip", "an X11 desktop should keep xclip for paste from other apps")
  return
end
assert(vim.g.clipboard.name == vim.env.EXPECTED, "OSC 52 provider not installed")
vim.g.clipboard.copy["+"]({ "x" })
assert(sent[1] == "+" and sent[2][1] == "x", "OSC 52 sequence not emitted")
assert(vim.deep_equal(vim.g.clipboard.paste["+"](), { "x" }), "paste cache lost the yank")
assert(vim.deep_equal(vim.g.clipboard.paste["*"](), {}), "primary selection must stay separate")
""",
        PATH=f"{binary}:{os.environ['PATH']}",
        DISPLAY=display,
        TEST_KERNEL=kernel,
        WAYLAND_DISPLAY="",
        SSH_CONNECTION=ssh,
        TMUX=tmux,
        EXPECTED=expected,
        OPTIONS_CONFIG=str(ROOT / "dot_config/nvim/lua/config/options.lua"),
    )


def test_sqruff_linter_parses_json_nulls_and_surfaces_cli_errors(tmp_path: Path) -> None:
    sql_repo = tmp_path / "sql-repo"
    nested = sql_repo / "models"
    nested.mkdir(parents=True)
    (sql_repo / ".sqruff").write_text("[sqruff]\ndialect = postgres\n", encoding="utf-8")
    sql_file = nested / "query.sql"
    sql_file.write_text("select  1\n", encoding="utf-8")

    run_lua(
        tmp_path,
        """
local spec = dofile(vim.env.LINTING_CONFIG)
local opts = spec[1].opts(nil, {})
assert(vim.deep_equal(opts.linters_by_ft.sql, { "sqlfluff", "sqruff" }))
local sqruff = opts.linters.sqruff
assert(sqruff.stream == "both", "stderr errors must reach the sqruff parser")
assert(not sqruff.condition({ filename = vim.env.OUTSIDE_SQL }))
assert(sqruff.condition({ filename = vim.env.SQL_FILE }))

local parser = sqruff.parser
assert(#parser("") == 0 and #parser("   \\n") == 0)
assert(#parser('{"<string>":[]}') == 0)

local null_fixture = parser([[
{"<string>":[
  {"range":{"start":{"line":null,"character":null},"end":null},"message":null,"severity":"Warning","source":null,"code":null},
  {"range":{"start":{"line":2,"character":5},"end":{"line":2,"character":8}},"message":"Use uppercase","severity":"Error","source":"sqruff","code":"CP01"}
]}
]])
assert(#null_fixture == 2, "both fixture items should parse without vim.NIL errors")
assert(null_fixture[1].lnum == 0 and null_fixture[1].col == 0 and null_fixture[1].code == nil)
assert(null_fixture[2].lnum == 1 and null_fixture[2].col == 4 and null_fixture[2].end_col == 7)
assert(null_fixture[2].severity == vim.diagnostic.severity.ERROR and null_fixture[2].code == "CP01")

local err_diags = parser("Error: bad config\\n")
assert(#err_diags == 1 and err_diags[1].severity == vim.diagnostic.severity.ERROR)
assert(err_diags[1].lnum == 0 and err_diags[1].col == 0 and err_diags[1].source == "sqruff")
assert(err_diags[1].message == "sqruff failed: Error: bad config")
""",
        LINTING_CONFIG=str(ROOT / "dot_config/nvim/lua/plugins/linting.lua"),
        SQL_FILE=str(sql_file),
        OUTSIDE_SQL=str(tmp_path / "plain.sql"),
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


def test_enter_continues_lists_in_prose_buffers_in_typeahead_order(tmp_path: Path) -> None:
    run_lua(
        tmp_path,
        """
vim.cmd("filetype plugin indent on")
-- Mirror LazyVim: comment leaders continue on <CR>, and Markdown keeps a 2-space indent.
vim.o.formatoptions = "jcroqlnt"
vim.g.markdown_recommended_style = 0
vim.o.expandtab, vim.o.shiftwidth = true, 2
dofile(vim.env.AUTOCMD_CONFIG)
local function expect(keys, want)
  vim.api.nvim_buf_set_lines(0, 0, -1, false, {})
  -- One feed puts every key in typeahead at once, like a macro or :normal.
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("i" .. keys .. "<Esc>", true, false, true), "xt", false)
  local got = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  assert(vim.deep_equal(got, want), vim.bo.filetype .. ": " .. keys .. " produced " .. vim.inspect(got))
end
-- The unnamed startup buffer predates the configuration, as with LazyVim's lazy loading.
for _, open in ipairs({ "", "edit list.md", "edit notes.txt", "edit COMMIT_EDITMSG" }) do
  if open ~= "" then
    vim.cmd(open)
  end
  expect("- top<CR>second<CR><C-t>nested<CR>deeper<CR><CR>back<CR><CR>after",
    { "- top", "- second", "  - nested", "  - deeper", "- back", "after" })
  expect("9. nine<CR>ten", { "9. nine", "10. ten" })
  expect("- [x] done<CR>todo", { "- [x] done", "- [ ] todo" })
  expect("plain<CR>line", { "plain", "line" })
  expect("- split<Left><Left><CR>", { "- spl", "- it" })
  expect("- x<Home><CR>", { "", "- x" })
  vim.bo.modified = false
end
""",
        AUTOCMD_CONFIG=str(ROOT / "dot_config/nvim/lua/config/autocmds.lua"),
    )


def test_lazy_bootstrap_pins_exact_commit_from_lazy_lock_and_fails_closed(tmp_path: Path) -> None:
    nvim_cfg = tmp_path / "config" / "nvim"
    nvim_cfg.mkdir(parents=True)
    shutil.copyfile(ROOT / "dot_config/nvim/lazy-lock.json", nvim_cfg / "lazy-lock.json")
    run_lua(
        tmp_path,
        """
local calls = {}
local orig_system = vim.fn.system
vim.fn.system = function(cmd)
  table.insert(calls, cmd)
  return ""
end
package.preload.lazy = function() return { setup = function() end } end
package.preload["config.theme"] = function() return "fmind" end
dofile(vim.env.LAZY_CONFIG)
vim.fn.system = orig_system
assert(#calls == 2, "expected clone + detached checkout, got " .. tostring(#calls))
assert(calls[1][1] == "git" and calls[1][2] == "clone" and calls[1][4] == "--no-checkout")
assert(calls[2][1] == "git" and calls[2][4] == "checkout" and calls[2][5] == "--detach")
assert(calls[2][6]:match("^[0-9a-f]+$") and #calls[2][6] == 40, "expected 40-char commit SHA")
""",
        LAZY_CONFIG=str(ROOT / "dot_config/nvim/lua/config/lazy.lua"),
    )

    bad_dir = tmp_path / "bad"
    (bad_dir / "config" / "nvim").mkdir(parents=True)
    (bad_dir / "config" / "nvim" / "lazy-lock.json").write_text('{"lazy.nvim": {"commit": "main"}}\n', encoding="utf-8")
    nvim = shutil.which("nvim")
    assert nvim
    probe = bad_dir / "probe.lua"
    probe.write_text("dofile(vim.env.LAZY_CONFIG)\n", encoding="utf-8")
    res = subprocess.run(
        [nvim, "--headless", "-u", "NONE", "-i", "NONE", "-l", str(probe)],
        env={
            **os.environ,
            "XDG_CONFIG_HOME": str(bad_dir / "config"),
            "XDG_DATA_HOME": str(bad_dir / "data"),
            "LAZY_CONFIG": str(ROOT / "dot_config/nvim/lua/config/lazy.lua"),
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res.returncode == 1
    assert not (bad_dir / "data" / "nvim" / "lazy" / "lazy.nvim").exists()


def test_ty_refreshes_imports_changed_outside_the_editor(tmp_path: Path) -> None:
    ty = shutil.which("ty")
    assert ty, "ty is required by the repository gate"
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "lsp-fixture"\nversion = "0.0.0"\n')
    (tmp_path / "dependency.py").write_text('value: str = "wrong"\n')
    (tmp_path / "main.py").write_text("from dependency import value\nresult: int = value\n")
    run_lua(
        tmp_path,
        """
local specs = dofile(vim.env.LSP_CONFIG)
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
""",
        timeout=40,
        LSP_CONFIG=str(ROOT / "dot_config/nvim/lua/plugins/lsp.lua"),
        TY_EXECUTABLE=ty,
        LSP_PROJECT=str(tmp_path),
    )
