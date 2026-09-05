package dot

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestNvimBootstrapIsBoundedAndNonInteractive(t *testing.T) {
	source := readRepoFile(t, "dot_config/nvim/lua/config/lazy.lua")
	for _, required := range []string{".system", "or 120000", "timeout = bootstrap_timeout", ":wait()", "fs_rename", "os.exit(1)"} {
		if !strings.Contains(source, required) {
			t.Errorf("lazy bootstrap lacks %q", required)
		}
	}
	if strings.Contains(source, "getchar") {
		t.Error("headless bootstrap must never wait for keyboard input")
	}
}

func TestNvimBootstrapRuntimeTimeout(t *testing.T) {
	nvim, lookupErr := exec.LookPath("nvim")
	if lookupErr != nil {
		t.Skip("nvim is not part of the repository test toolchain")
	}

	root := t.TempDir()
	bin := filepath.Join(root, "bin")
	if err := os.Mkdir(bin, 0o755); err != nil {
		t.Fatal(err)
	}
	git := filepath.Join(bin, "git")
	if err := os.WriteFile(git, []byte("#!/bin/sh\nexec sleep 300\n"), 0o755); err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, nvim, "--headless", "-u", "NONE", "-c", "lua vim.g.lazy_bootstrap_timeout_ms = 50; dofile([["+filepath.Join(repositoryRoot(t), "dot_config/nvim/lua/config/lazy.lua")+"]])")
	command.Env = append(os.Environ(), "PATH="+bin+string(os.PathListSeparator)+os.Getenv("PATH"), "XDG_DATA_HOME="+filepath.Join(root, "data"))
	output, runErr := command.CombinedOutput()
	if ctx.Err() != nil {
		t.Fatalf("headless bootstrap ignored its timeout: %v", ctx.Err())
	}
	if runErr == nil {
		t.Fatal("timed-out clone unexpectedly succeeded")
	}
	if !strings.Contains(string(output), "Failed to clone lazy.nvim") {
		t.Fatalf("missing bounded failure diagnostic: %s", output)
	}
	staging, err := filepath.Glob(filepath.Join(root, "data", "nvim", "lazy", "lazy.nvim.tmp.*"))
	if err != nil {
		t.Fatal(err)
	}
	if len(staging) != 0 {
		t.Fatalf("bootstrap left attempt-owned staging paths: %v", staging)
	}
}

func TestNvimBootstrapRuntimeFailureAndSuccess(t *testing.T) {
	nvim, lookupErr := exec.LookPath("nvim")
	if lookupErr != nil {
		t.Skip("nvim is not part of the repository test toolchain")
	}
	lazySource := filepath.Join(repositoryRoot(t), "dot_config/nvim/lua/config/lazy.lua")

	t.Run("failed clone", func(t *testing.T) {
		root := t.TempDir()
		git := fakeNvimGit(t, root, "#!/bin/sh\nexit 42\n")
		output, runErr := runNvimLazy(t, nvim, lazySource, root, git)
		if runErr == nil || !strings.Contains(output, "Failed to clone lazy.nvim") {
			t.Fatalf("failed clone result = %v, output = %s", runErr, output)
		}
		assertNoLazyStaging(t, root)
	})

	t.Run("fresh clone", func(t *testing.T) {
		root := t.TempDir()
		git := fakeNvimGit(t, root, "#!/bin/sh\ntarget=$5\nmkdir -p \"$target/lua/lazy\"\nprintf '%s\\n' 'return { setup = function(_) end }' > \"$target/lua/lazy/init.lua\"\n")
		output, runErr := runNvimLazy(t, nvim, lazySource, root, git)
		if runErr != nil {
			t.Fatalf("fresh clone failed: %v: %s", runErr, output)
		}
		if _, err := os.Stat(filepath.Join(root, "data with spaces", "nvim", "lazy", "lazy.nvim", "lua", "lazy", "init.lua")); err != nil {
			t.Fatalf("published lazy checkout: %v", err)
		}
		assertNoLazyStaging(t, root)
	})

	t.Run("existing clone", func(t *testing.T) {
		root := t.TempDir()
		checkout := filepath.Join(root, "data with spaces", "nvim", "lazy", "lazy.nvim", "lua", "lazy")
		if err := os.MkdirAll(checkout, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(checkout, "init.lua"), []byte("return { setup = function(_) end }\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		sentinel := filepath.Join(root, "git-called")
		git := fakeNvimGit(t, root, "#!/bin/sh\ntouch \"$NVIM_GIT_SENTINEL\"\nexit 99\n")
		output, runErr := runNvimLazy(t, nvim, lazySource, root, git, "NVIM_GIT_SENTINEL="+sentinel)
		if runErr != nil {
			t.Fatalf("existing checkout failed: %v: %s", runErr, output)
		}
		if _, err := os.Stat(sentinel); !os.IsNotExist(err) {
			t.Fatalf("existing checkout unexpectedly invoked git: %v", err)
		}
	})
}

func fakeNvimGit(t *testing.T, root, source string) string {
	t.Helper()
	bin := filepath.Join(root, "bin")
	if err := os.Mkdir(bin, 0o755); err != nil {
		t.Fatal(err)
	}
	git := filepath.Join(bin, "git")
	if err := os.WriteFile(git, []byte(source), 0o755); err != nil {
		t.Fatal(err)
	}
	return git
}

func runNvimLazy(t *testing.T, nvim, lazySource, root, git string, extraEnv ...string) (string, error) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, nvim, "--headless", "-u", "NONE", "-c", "lua vim.g.lazy_bootstrap_timeout_ms = 250; dofile([["+lazySource+"]])", "-c", "qa!")
	command.Env = append(os.Environ(), "PATH="+filepath.Dir(git)+string(os.PathListSeparator)+os.Getenv("PATH"), "XDG_DATA_HOME="+filepath.Join(root, "data with spaces"))
	command.Env = append(command.Env, extraEnv...)
	output, err := command.CombinedOutput()
	if ctx.Err() != nil {
		t.Fatalf("headless bootstrap did not terminate: %v", ctx.Err())
	}
	return string(output), err
}

func assertNoLazyStaging(t *testing.T, root string) {
	t.Helper()
	staging, err := filepath.Glob(filepath.Join(root, "data with spaces", "nvim", "lazy", "lazy.nvim.tmp.*"))
	if err != nil {
		t.Fatal(err)
	}
	if len(staging) != 0 {
		t.Fatalf("bootstrap left attempt-owned staging paths: %v", staging)
	}
}

func TestNvimFormatUsesProjectRootsAndDeclaredGoTools(t *testing.T) {
	formatting := readRepoFile(t, "dot_config/nvim/lua/plugins/formatting.lua")
	resolver := readRepoFile(t, "dot_config/nvim/lua/config/go_tool.lua")
	source := formatting + resolver
	for _, required := range []string{"ctx.filename", "dprint.json", "go.mod", "go", "mod", "edit", "-json", "go_tool.formatter"} {
		if !strings.Contains(source, required) {
			t.Errorf("formatter ownership lacks %q", required)
		}
	}
	if strings.Contains(formatting, "vim.fn.getcwd") {
		t.Error("formatter ownership must not depend on the shell/editor cwd")
	}
}

func TestNvimGoToolResolverIsSharedWithTemplLSP(t *testing.T) {
	resolver := readRepoFile(t, "dot_config/nvim/lua/config/go_tool.lua")
	formatting := readRepoFile(t, "dot_config/nvim/lua/plugins/formatting.lua")
	lsp := readRepoFile(t, "dot_config/nvim/lua/plugins/lsp.lua")
	for name, source := range map[string]string{"resolver": resolver, "formatting": formatting, "lsp": lsp} {
		if !strings.Contains(source, "config.go_tool") && name != "resolver" {
			t.Errorf("%s does not use the shared Go tool resolver", name)
		}
	}
	for _, required := range []string{"go", "mod", "edit", "-json", "vim.lsp.rpc.start"} {
		if !strings.Contains(resolver, required) {
			t.Errorf("shared Go tool resolver lacks %q", required)
		}
	}
	if !strings.Contains(lsp, `go_tool.lsp("templ", { "lsp" })`) {
		t.Error("templ LSP does not select a module-declared tool")
	}
}

func TestNvimGoToolRuntimeSelectsModuleToolAndFallback(t *testing.T) {
	nvim, lookupErr := exec.LookPath("nvim")
	if lookupErr != nil {
		t.Skip("nvim is not part of the repository test toolchain")
	}
	root := t.TempDir()
	module := filepath.Join(root, "module with spaces")
	file := filepath.Join(module, "nested", "view.templ")
	if err := os.MkdirAll(filepath.Dir(file), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(module, "go.mod"), []byte("module example.com/test\n\ngo 1.24\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(file, nil, 0o644); err != nil {
		t.Fatal(err)
	}
	bin := filepath.Join(root, "bin")
	if err := os.Mkdir(bin, 0o755); err != nil {
		t.Fatal(err)
	}
	goBin := filepath.Join(bin, "go")
	goSource := "#!/bin/sh\nif [ \"$1 $2\" = 'mod edit' ]; then\n  if [ \"$GO_TOOL_DECLARED\" = 1 ]; then printf '%s\\n' '{\"Tool\":[{\"Path\":\"github.com/a-h/templ/cmd/templ\"}]}' ; else printf '%s\\n' '{\"Tool\":[]}' ; fi\n  exit 0\nfi\nexit 17\n"
	if err := os.WriteFile(goBin, []byte(goSource), 0o755); err != nil {
		t.Fatal(err)
	}

	lua := filepath.Join(root, "go-tool-test.lua")
	luaSource := `package.path = vim.env.DOT_NVIM_LUA .. "/?.lua;" .. package.path
local go_tool = require("config.go_tool")
local expected_declared = vim.env.GO_TOOL_DECLARED == "1"
local ctx = { filename = vim.env.DOT_TEST_FILE }
local formatter = go_tool.formatter("templ")
assert(formatter.command(nil, ctx) == (expected_declared and "go" or "templ"))
assert(vim.deep_equal(formatter.prepend_args(nil, ctx), expected_declared and { "tool", "templ" } or {}))
assert(formatter.cwd(nil, ctx) == (expected_declared and vim.env.DOT_TEST_MODULE or nil))
local captured
vim.lsp.rpc.start = function(command, _, options)
  captured = { command = command, cwd = options.cwd }
  return {}
end
go_tool.lsp("templ", { "lsp" })({ on_exit = function() end }, { root_dir = vim.env.DOT_TEST_MODULE })
local expected_command = expected_declared and { "go", "tool", "templ", "lsp" } or { "templ", "lsp" }
assert(vim.deep_equal(captured.command, expected_command))
assert(captured.cwd == vim.env.DOT_TEST_MODULE)
if expected_declared then
  assert(vim.system(captured.command, { cwd = captured.cwd }):wait().code == 17)
end
`
	if err := os.WriteFile(lua, []byte(luaSource), 0o644); err != nil {
		t.Fatal(err)
	}

	for _, declared := range []string{"1", "0"} {
		command := exec.Command(nvim, "-l", lua)
		command.Env = append(os.Environ(), "PATH="+bin+string(os.PathListSeparator)+os.Getenv("PATH"), "DOT_NVIM_LUA="+filepath.Join(repositoryRoot(t), "dot_config/nvim/lua"), "DOT_TEST_FILE="+file, "DOT_TEST_MODULE="+module, "GO_TOOL_DECLARED="+declared)
		if output, err := command.CombinedOutput(); err != nil {
			t.Fatalf("declared=%s: %v: %s", declared, err, output)
		}
	}
}

func TestNvimFormatterOwnershipRuntime(t *testing.T) {
	nvim, lookupErr := exec.LookPath("nvim")
	if lookupErr != nil {
		t.Skip("nvim is not part of the repository test toolchain")
	}
	root := t.TempDir()
	fixtures := map[string]struct {
		config string
		body   string
	}{
		"biome":          {config: "biome.json", body: "{}\n"},
		"biome-excluded": {config: "biome.json", body: `{"files":{"includes":["**/*.ts"]}}`},
		"prettier":       {config: ".prettierrc", body: "{}\n"},
		"none":           {},
	}
	for name, fixture := range fixtures {
		dir := filepath.Join(root, name)
		if err := os.Mkdir(dir, 0o755); err != nil {
			t.Fatal(err)
		}
		if fixture.config != "" {
			if err := os.WriteFile(filepath.Join(dir, fixture.config), []byte(fixture.body), 0o644); err != nil {
				t.Fatal(err)
			}
		}
		if err := os.WriteFile(filepath.Join(dir, "file.json"), []byte("{}\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	both := filepath.Join(root, "both")
	if err := os.Mkdir(both, 0o755); err != nil {
		t.Fatal(err)
	}
	for _, config := range []string{"biome.json", ".prettierrc"} {
		if err := os.WriteFile(filepath.Join(both, config), []byte("{}\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(both, "file.json"), []byte("{}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	lua := filepath.Join(root, "formatter-owner-test.lua")
	luaSource := `package.path = vim.env.DOT_NVIM_LUA .. "/?.lua;" .. package.path
local specs = dofile(vim.env.DOT_FORMATTING_SOURCE)
local opts = { formatters = {}, formatters_by_ft = {} }
specs[1].opts(nil, opts)
assert(type(opts.formatters_by_ft.json) == "function")
local function check(filename, expected, expected_lsp)
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_name(buf, filename)
  vim.bo[buf].filetype = "json"
  local selected = opts.formatters_by_ft.json(buf)
  assert(selected[1] == expected, filename .. ": expected " .. tostring(expected) .. ", got " .. tostring(selected[1]))
  assert(selected.lsp_format == expected_lsp, filename .. ": wrong lsp fallback")
  vim.api.nvim_buf_delete(buf, { force = true })
end
check(vim.env.DOT_DPRINT_FILE, "dprint", "never")
check(vim.env.DOT_DPRINT_EXCLUDED, nil, "fallback")
check(vim.env.DOT_FIXTURES .. "/biome/file.json", "biome", "never")
check(vim.env.DOT_FIXTURES .. "/biome-excluded/file.json", nil, "fallback")
check(vim.env.DOT_FIXTURES .. "/prettier/file.json", "prettier", "never")
check(vim.env.DOT_FIXTURES .. "/both/file.json", "biome", "never")
check(vim.env.DOT_FIXTURES .. "/none/file.json", nil, "fallback")
local original_path = vim.env.PATH
vim.env.PATH = ""
check(vim.env.DOT_DPRINT_FILE, "dprint", "never")
vim.env.PATH = original_path
`
	if err := os.WriteFile(lua, []byte(luaSource), 0o644); err != nil {
		t.Fatal(err)
	}
	repo := repositoryRoot(t)
	command := exec.Command(nvim, "-l", lua)
	command.Env = append(os.Environ(), "DOT_NVIM_LUA="+filepath.Join(repo, "dot_config/nvim/lua"), "DOT_FORMATTING_SOURCE="+filepath.Join(repo, "dot_config/nvim/lua/plugins/formatting.lua"), "DOT_DPRINT_FILE="+filepath.Join(repo, "dprint.json"), "DOT_DPRINT_EXCLUDED="+filepath.Join(repo, "mise.lock"), "DOT_FIXTURES="+root)
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("formatter ownership fixture: %v: %s", err, output)
	}
}

func TestNvimFormatterOwnershipMatchesCanonicalTools(t *testing.T) {
	nvim, nvimErr := exec.LookPath("nvim")
	dprint, dprintErr := exec.LookPath("dprint")
	biome, biomeErr := exec.LookPath("biome")
	home, homeErr := os.UserHomeDir()
	if nvimErr != nil || dprintErr != nil || biomeErr != nil || homeErr != nil {
		t.Skip("editor formatter runtime dependencies are not in the repository test toolchain")
	}
	prettier := filepath.Join(home, ".local", "share", "nvim", "mason", "bin", "prettier")
	conform := filepath.Join(home, ".local", "share", "nvim", "lazy", "conform.nvim")
	for _, required := range []string{prettier, filepath.Join(conform, "lua", "conform", "init.lua")} {
		if _, err := os.Stat(required); err != nil {
			t.Skip("installed Neovim formatter state is unavailable")
		}
	}

	type fixture struct {
		Path     string `json:"path"`
		Filetype string `json:"filetype"`
		Expected string `json:"expected"`
	}
	root := t.TempDir()
	dprintRoot := filepath.Join(root, "dprint")
	biomeRoot := filepath.Join(root, "biome")
	prettierRoot := filepath.Join(root, "prettier")
	for _, dir := range []string{dprintRoot, biomeRoot, prettierRoot} {
		if err := os.Mkdir(dir, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	dprintConfig := readRepoFile(t, "dprint.json")
	for name, content := range map[string]string{
		filepath.Join(dprintRoot, "dprint.json"):   dprintConfig,
		filepath.Join(biomeRoot, "biome.json"):     "{}\n",
		filepath.Join(prettierRoot, ".prettierrc"): "{}\n",
	} {
		if err := os.WriteFile(name, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}

	inputs := []struct {
		path      string
		filetype  string
		content   string
		canonical string
		args      []string
	}{
		{filepath.Join(dprintRoot, "doc.md"), "markdown", "# Title\n\ntext    \n", dprint, []string{"fmt", "--config", filepath.Join(dprintRoot, "dprint.json"), "--stdin"}},
		{filepath.Join(dprintRoot, "config.toml"), "toml", "[tool]\nb= 2\n", dprint, []string{"fmt", "--config", filepath.Join(dprintRoot, "dprint.json"), "--stdin"}},
		{filepath.Join(dprintRoot, "config.yaml"), "yaml", "a:    1\nb:\n - 2\n", dprint, []string{"fmt", "--config", filepath.Join(dprintRoot, "dprint.json"), "--stdin"}},
		{filepath.Join(dprintRoot, "data.json"), "json", "{\"b\":[2,3],\"a\":1}\n", dprint, []string{"fmt", "--config", filepath.Join(dprintRoot, "dprint.json"), "--stdin"}},
		{filepath.Join(biomeRoot, "data.json"), "json", "{\"b\":[2,3],\"a\":1}\n", biome, []string{"format", "--stdin-file-path"}},
		{filepath.Join(prettierRoot, "app.component.html"), "htmlangular", "<div><span>{{value}}</span></div>\n", prettier, []string{"--stdin-filepath"}},
	}
	fixtures := make([]fixture, 0, len(inputs))
	for _, input := range inputs {
		if err := os.WriteFile(input.path, []byte(input.content), 0o644); err != nil {
			t.Fatal(err)
		}
		args := append(append([]string{}, input.args...), input.path)
		command := exec.Command(input.canonical, args...)
		command.Dir = filepath.Dir(input.path)
		command.Stdin = strings.NewReader(input.content)
		expected, err := command.Output()
		if err != nil {
			t.Fatalf("canonical %s: %v", input.filetype, err)
		}
		fixtures = append(fixtures, fixture{Path: input.path, Filetype: input.filetype, Expected: string(expected)})
	}

	manifest, err := json.Marshal(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	manifestPath := filepath.Join(root, "fixtures.json")
	if err := os.WriteFile(manifestPath, manifest, 0o644); err != nil {
		t.Fatal(err)
	}
	lua := filepath.Join(root, "format-fixtures.lua")
	luaSource := `vim.opt.rtp:prepend(vim.env.DOT_CONFORM)
package.path = vim.env.DOT_NVIM_LUA .. "/?.lua;" .. package.path
local specs = dofile(vim.env.DOT_FORMATTING_SOURCE)
local opts = { default_format_opts = { timeout_ms = 10000, lsp_format = "fallback" }, formatters = {}, formatters_by_ft = {} }
specs[1].opts(nil, opts)
local conform = require("conform")
conform.setup(opts)
local fixtures = vim.json.decode(table.concat(vim.fn.readfile(vim.env.DOT_FIXTURE_MANIFEST), "\n"))
for _, fixture in ipairs(fixtures) do
  vim.cmd.edit(vim.fn.fnameescape(fixture.path))
  local buf = vim.api.nvim_get_current_buf()
  vim.bo[buf].filetype = fixture.filetype
  local format_error
  conform.format({ bufnr = buf, timeout_ms = 10000 }, function(err)
    format_error = err
  end)
  assert(not format_error, fixture.path .. ": " .. tostring(format_error))
  vim.cmd.write()
end
`
	if err := os.WriteFile(lua, []byte(luaSource), 0o644); err != nil {
		t.Fatal(err)
	}
	repo := repositoryRoot(t)
	command := exec.Command(nvim, "-l", lua)
	command.Env = append(os.Environ(), "PATH="+filepath.Dir(prettier)+string(os.PathListSeparator)+os.Getenv("PATH"), "DOT_CONFORM="+conform, "DOT_NVIM_LUA="+filepath.Join(repo, "dot_config/nvim/lua"), "DOT_FORMATTING_SOURCE="+filepath.Join(repo, "dot_config/nvim/lua/plugins/formatting.lua"), "DOT_FIXTURE_MANIFEST="+manifestPath)
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("headless formatter fixtures: %v: %s", err, output)
	}
	for _, fixture := range fixtures {
		actual, err := os.ReadFile(fixture.Path)
		if err != nil {
			t.Fatal(err)
		}
		if string(actual) != fixture.Expected {
			t.Errorf("%s output mismatch\nwant: %q\n got: %q", fixture.Filetype, fixture.Expected, actual)
		}
	}
}

func TestNvimAngularUsesLazyVimExtra(t *testing.T) {
	source := readRepoFile(t, "dot_config/nvim/lazyvim.json")
	if strings.Count(source, "lazyvim.plugins.extras.lang.angular") != 1 {
		t.Fatal("Angular support must be enabled exactly once through LazyVim's extra")
	}
}

func readRepoFile(t *testing.T, name string) string {
	t.Helper()
	root := repositoryRoot(t)
	content, err := os.ReadFile(filepath.Join(root, name))
	if err != nil {
		t.Fatal(err)
	}
	return string(content)
}
