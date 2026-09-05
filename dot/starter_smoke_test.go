package dot

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"testing"
)

func TestStarterSmoke(t *testing.T) {
	if os.Getenv("DOT_STARTER_SMOKE") != "1" {
		t.Skip("run with mise run test:starters")
	}
	t.Run("go-cli", smokeGoCLI)
	t.Run("python-library", smokePythonLibrary)
	t.Run("typescript-library", smokeTypeScriptLibrary)
}

func smokeGoCLI(t *testing.T) {
	root := t.TempDir()
	module := "example.com/starter"
	writeStarterFile(t, root, "go.mod", "module "+module+"\n\ngo 1.25\n\nrequire (\n\tgithub.com/caarlos0/env/v11 v11.3.1\n\tgithub.com/urfave/cli/v3 v3.6.1\n)\n")
	copyStarterTemplate(t, root, "skills/go-stack/references/cli.go", "cmd/starter/main.go", map[string]string{"<import_path>": module, "<package>": "starter", "<slug>": "starter"})
	copyStarterTemplate(t, root, "skills/go-stack/references/config.go", "config/config.go", nil)
	copyStarterTemplate(t, root, "skills/go-stack/references/lib.go", "starter.go", map[string]string{"<slug>": "starter"})
	copyStarterTemplate(t, root, "skills/go-stack/references/lib_test.go", "starter_test.go", map[string]string{"<package>": "starter"})
	runStarter(t, root, "go", "mod", "tidy")
	runStarter(t, root, "gofmt", "-w", "cmd/starter/main.go", "config/config.go", "starter.go")
	runStarter(t, root, "go", "vet", "./...")
	runStarter(t, root, "go", "test", "./...")
	runStarter(t, root, "go", "build", "./cmd/starter")
}

func smokePythonLibrary(t *testing.T) {
	root := t.TempDir()
	template := readRepoFile(t, "skills/python-stack/references/pyproject.toml.template")
	pythonVersion := strings.TrimSpace(runStarter(t, root, "python", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"))
	template = strings.NewReplacer("<slug>", "starter-py", "<package>", "starter_py", "<description>", "Starter library", "<holder>", "Fmind", "<latest_stable_version_major_minor>", pythonVersion).Replace(template)
	template = regexp.MustCompile(`(?s)dependencies = \[.*?\]\n\n\[dependency-groups\]`).ReplaceAllString(template, "dependencies = []\n\n[dependency-groups]")
	template = regexp.MustCompile(`(?s)\n\[project\.scripts\].*?\n\[build-system\]`).ReplaceAllString(template, "\n[build-system]")
	template = strings.ReplaceAll(template, "  \"testcontainers[postgres]>=4.15.0\",  # web integration tests; drop for non-web projects\n", "")
	writeStarterFile(t, root, "pyproject.toml", template)
	copyStarterTemplate(t, root, "skills/python-stack/references/init-library.py", "src/starter_py/__init__.py", map[string]string{"<description>": "Starter library"})
	copyStarterTemplate(t, root, "skills/python-stack/references/test_library.py", "tests/test_library.py", map[string]string{"<package>": "starter_py"})
	writeStarterFile(t, root, "README.md", "# Starter Python\n")
	writeStarterFile(t, root, "LICENSE", "MIT\n")
	runStarter(t, root, "uv", "lock")
	runStarter(t, root, "uv", "sync", "--locked")
	runStarter(t, root, "uv", "run", "ruff", "check")
	runStarter(t, root, "uv", "run", "ruff", "format", "--check")
	runStarter(t, root, "uv", "run", "ty", "check")
	runStarter(t, root, "uv", "run", "pytest")
	runStarter(t, root, "uv", "build")
}

func smokeTypeScriptLibrary(t *testing.T) {
	root := t.TempDir()
	manifestSource := strings.NewReplacer("<slug>", "starter-ts", "<description>", "Starter library", "<pinned>", "11.25.0").Replace(readRepoFile(t, "skills/typescript-stack/references/package.json.template"))
	var manifest map[string]any
	if err := json.Unmarshal([]byte(manifestSource), &manifest); err != nil {
		t.Fatal(err)
	}
	manifest["dependencies"] = map[string]any{}
	delete(manifest, "bin")
	encoded, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	writeStarterFile(t, root, "package.json", string(encoded)+"\n")
	for _, name := range []string{"lib.ts", "lib.test.ts", "index.ts"} {
		copyStarterTemplate(t, root, "skills/typescript-stack/references/"+name, "src/"+name, nil)
	}
	for _, name := range []string{"tsconfig.json", "tsconfig.build.json", "biome.json", "knip.json", "gitignore"} {
		copyStarterTemplate(t, root, "skills/typescript-stack/references/"+name, name, nil)
	}
	if err := os.Rename(filepath.Join(root, "gitignore"), filepath.Join(root, ".gitignore")); err != nil {
		t.Fatal(err)
	}
	runStarter(t, root, "pnpm", "install", "--frozen-lockfile=false")
	runStarter(t, root, "pnpm", "exec", "biome", "check", "--write", "--no-errors-on-unmatched")
	runStarter(t, root, "pnpm", "exec", "tsc", "--noEmit")
	runStarter(t, root, "pnpm", "exec", "vitest", "run")
	runStarter(t, root, "pnpm", "exec", "tsc", "--project", "tsconfig.build.json")
	runStarter(t, root, "pnpm", "exec", "knip")
}

func copyStarterTemplate(t *testing.T, root, source, destination string, replacements map[string]string) {
	t.Helper()
	content := readRepoFile(t, source)
	for old, replacement := range replacements {
		content = strings.ReplaceAll(content, old, replacement)
	}
	if strings.Contains(content, "<slug>") || strings.Contains(content, "<package>") || strings.Contains(content, "<import_path>") {
		t.Fatalf("%s retains an unresolved required placeholder", source)
	}
	writeStarterFile(t, root, destination, content)
}

func writeStarterFile(t *testing.T, root, name, content string) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(name))
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
}

func runStarter(t *testing.T, dir, name string, args ...string) string {
	t.Helper()
	command := exec.Command(name, args...)
	command.Dir = dir
	command.Env = append(os.Environ(), "CI=1", "NO_COLOR=1")
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("%s %s (%s/%s): %v\n%s", name, strings.Join(args, " "), runtime.GOOS, runtime.GOARCH, err, output)
	}
	t.Logf("%s %s: ok", name, strings.Join(args, " "))
	return string(output)
}
