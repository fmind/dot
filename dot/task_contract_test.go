package dot

import (
	"bufio"
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestTaskGitleaksRedactsSyntheticFinding(t *testing.T) {
	gitleaks, err := exec.LookPath("gitleaks")
	if err != nil {
		t.Fatal("gitleaks is required for task contract tests")
	}
	fixture := t.TempDir()
	// Materialize the synthetic credential only in the disposable scan fixture.
	const planted = "glpat-" + "abcdefghijklmnopqrst"
	if writeErr := os.WriteFile(filepath.Join(fixture, "fixture.txt"), []byte("token = \""+planted+"\"\n"), 0o600); writeErr != nil {
		t.Fatal(writeErr)
	}
	report := filepath.Join(fixture, "report.json")
	cmd := exec.Command(gitleaks, "dir", fixture, "--redact=100", "--no-banner", "--report-format=json", "--report-path", report)
	output, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatal("synthetic credential was not detected")
	}
	reportContent, readErr := os.ReadFile(report)
	if readErr != nil {
		t.Fatal(readErr)
	}
	if bytes.Contains(output, []byte(planted)) || bytes.Contains(reportContent, []byte(planted)) {
		t.Fatal("gitleaks exposed the unredacted synthetic credential")
	}
}

func TestTaskFormatHelpersHonorExplicitFiles(t *testing.T) {
	repo := repositoryRoot(t)
	for _, test := range []struct {
		name     string
		script   string
		selected string
		sibling  string
	}{
		{name: "go", script: "format-go.sh", selected: "package sample\nfunc Selected( ){ }\n", sibling: "package sample\nfunc Sibling( ){ }\n"},
		{name: "python", script: "format-python.sh", selected: "def selected( ):\n return 1\n", sibling: "def sibling( ):\n return 1\n"},
		{name: "lua", script: "format-lua.sh", selected: "local  selected={1,2}\n", sibling: "local  sibling={1,2}\n"},
		{name: "shell", script: "format-shell.sh", selected: "#!/bin/sh\nif true;then echo selected;fi\n", sibling: "#!/bin/sh\nif true;then echo sibling;fi\n"},
	} {
		t.Run(test.name, func(t *testing.T) {
			dir := filepath.Join(t.TempDir(), "path with spaces")
			if err := os.MkdirAll(dir, 0o700); err != nil {
				t.Fatal(err)
			}
			ext := map[string]string{"go": ".go", "python": ".py", "lua": ".lua", "shell": ".sh"}[test.name]
			selected := filepath.Join(dir, "selected"+ext)
			sibling := filepath.Join(dir, "sibling"+ext)
			if err := os.WriteFile(selected, []byte(test.selected), 0o600); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(sibling, []byte(test.sibling), 0o600); err != nil {
				t.Fatal(err)
			}
			cmd := exec.Command(filepath.Join(repo, "dot", "scripts", test.script), selected)
			cmd.Dir = repo
			if output, err := cmd.CombinedOutput(); err != nil {
				t.Fatalf("format selected file: %v\n%s", err, output)
			}
			selectedAfter, err := os.ReadFile(selected)
			if err != nil {
				t.Fatal(err)
			}
			if bytes.Equal(selectedAfter, []byte(test.selected)) {
				t.Fatal("selected file was not formatted")
			}
			siblingAfter, err := os.ReadFile(sibling)
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(siblingAfter, []byte(test.sibling)) {
				t.Fatal("unselected sibling was modified")
			}
		})
	}
}

func TestTaskToolsPropagatesInventoryFailures(t *testing.T) {
	realMise, err := exec.LookPath("mise")
	if err != nil {
		t.Fatal("mise is required for task contract tests")
	}
	fakeDir := t.TempDir()
	fake := `#!/bin/sh
case "$*" in
  *"tasks validate"*) [ "${TASK_TOOLS_CASE:-}" != "validate-failure" ] || exit 43 ;;
  "prune --dry-run")
    case "${TASK_TOOLS_CASE:-}" in
      prune-failure) echo "inventory unavailable" >&2; exit 42 ;;
      orphan) echo "tool@1: no tracked config or tool stub requires this version" ;;
    esac
    ;;
esac
`
	if err := os.WriteFile(filepath.Join(fakeDir, "mise"), []byte(fake), 0o700); err != nil {
		t.Fatal(err)
	}

	for _, test := range []struct {
		name    string
		mode    string
		wantErr bool
	}{
		{name: "clean"},
		{name: "orphan", mode: "orphan", wantErr: true},
		{name: "prune failure", mode: "prune-failure", wantErr: true},
		{name: "validation failure", mode: "validate-failure", wantErr: true},
	} {
		t.Run(test.name, func(t *testing.T) {
			cmd := exec.Command(realMise, "-C", repositoryRoot(t), "run", "check:tools")
			cmd.Env = append(os.Environ(), "PATH="+fakeDir+string(os.PathListSeparator)+os.Getenv("PATH"), "TASK_TOOLS_CASE="+test.mode)
			output, err := cmd.CombinedOutput()
			if (err != nil) != test.wantErr {
				t.Fatalf("error = %v, wantErr %v\n%s", err, test.wantErr, output)
			}
		})
	}
}

func TestTaskContractFormattersAcceptExactFileLists(t *testing.T) {
	repo := repositoryRoot(t)
	for _, test := range []struct {
		file  string
		tasks []string
	}{
		{file: "mise.toml", tasks: []string{"format:go", "format:lua", "format:python", "format:shell"}},
		{file: "dot/mise.toml", tasks: []string{"format:go"}},
	} {
		content, err := os.ReadFile(filepath.Join(repo, test.file))
		if err != nil {
			t.Fatal(err)
		}
		for _, task := range test.tasks {
			marker := `[tasks."` + task + `"]`
			start := strings.Index(string(content), marker)
			if start < 0 {
				t.Errorf("%s: missing %s", test.file, marker)
				continue
			}
			block := string(content[start:])
			if next := strings.Index(block[len(marker):], "\n[tasks."); next >= 0 {
				block = block[:len(marker)+next]
			}
			forwardsArgs := strings.Contains(block, `$@`) || strings.Contains(block, "dot/scripts/format-")
			if !strings.Contains(block, "raw_args = true") || !forwardsArgs {
				t.Errorf("%s: %s must forward an explicit argv list to every formatter", test.file, task)
			}
		}
	}
}

func TestTaskContractChecksAreReadOnlyAndComplete(t *testing.T) {
	repo := repositoryRoot(t)
	var combined strings.Builder
	for _, relative := range []string{"mise.toml", "dot/scripts/check-fish.sh", "dot/scripts/check-shell.sh"} {
		content, err := os.ReadFile(filepath.Join(repo, relative))
		if err != nil {
			t.Fatal(err)
		}
		combined.Write(content)
	}
	for _, required := range []string{
		`"check:fish"`,
		"fish --no-config --no-execute",
		"shfmt -d -i 2 -s",
		"ruff format --check",
		"chezmoi execute-template --with-stdin --file",
	} {
		if !strings.Contains(combined.String(), required) {
			t.Errorf("mise.toml: missing read-only check contract %q", required)
		}
	}
}

func TestTaskContractGitleaksCommandsRedactFindings(t *testing.T) {
	repo := repositoryRoot(t)
	commandFiles := make([]string, 0)
	err := filepath.WalkDir(repo, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		relative, err := filepath.Rel(repo, path)
		if err != nil {
			return err
		}
		if entry.IsDir() && (relative == ".git" || relative == ".agents/prompts" || relative == ".agents/proposals") {
			return filepath.SkipDir
		}
		if entry.IsDir() || relative == "dot/task_contract_test.go" {
			return nil
		}
		switch filepath.Ext(path) {
		case ".md", ".toml", ".yaml", ".yml":
			commandFiles = append(commandFiles, relative)
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	for _, relative := range commandFiles {
		file, err := os.Open(filepath.Join(repo, relative))
		if err != nil {
			t.Fatal(err)
		}
		scanner := bufio.NewScanner(file)
		for line := 1; scanner.Scan(); line++ {
			text := strings.TrimSpace(scanner.Text())
			if strings.Contains(text, "gitleaks git ") || strings.Contains(text, "gitleaks dir ") {
				if !strings.Contains(text, "--redact=100") {
					t.Errorf("%s:%d: executable gitleaks command must use --redact=100", relative, line)
				}
			}
		}
		if err := scanner.Err(); err != nil {
			t.Fatal(err)
		}
		if err := file.Close(); err != nil {
			t.Fatal(err)
		}
	}
}
