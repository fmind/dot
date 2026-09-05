package dot

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestBootstrapRejectsUnsupportedMiseBeforeMutation(t *testing.T) {
	home, bin, log := bootstrapFixture(t, "2025.1.0")
	command := bootstrapCommand(t, home, bin, log)
	output, err := command.CombinedOutput()
	if err == nil || !strings.Contains(string(output), "mise 2026.9.1 or newer is required") {
		t.Fatalf("unsupported mise result = %v\n%s", err, output)
	}
	if calls := readOptionalFile(t, log); strings.Contains(calls, "chezmoi ") || strings.Contains(calls, "git ") {
		t.Fatalf("unsupported mise mutated bootstrap state: %s", calls)
	}
}

func TestBootstrapFirstInstallAndRerunAreBounded(t *testing.T) {
	home, bin, log := bootstrapFixture(t, "2026.9.1")
	for range 2 {
		command := bootstrapCommand(t, home, bin, log)
		if output, err := command.CombinedOutput(); err != nil {
			t.Fatalf("bootstrap failed: %v\n%s", err, output)
		}
	}
	calls := readOptionalFile(t, log)
	for _, expected := range []string{"chezmoi init --force --source", "mise trust -y", "mise -C", "run install"} {
		if !strings.Contains(calls, expected) {
			t.Errorf("bootstrap calls lack %q:\n%s", expected, calls)
		}
	}
	if strings.Contains(calls, "git ") {
		t.Fatalf("CI/SKIP_GIT_PULL rerun unexpectedly fetched the repository: %s", calls)
	}
	if _, err := os.Stat(filepath.Join(home, ".config", "chezmoi", "key.txt")); !os.IsNotExist(err) {
		t.Fatal("fixture unexpectedly provisioned an age key")
	}
}

func bootstrapFixture(t *testing.T, version string) (string, string, string) {
	t.Helper()
	home := t.TempDir()
	source := filepath.Join(home, ".local", "share", "chezmoi")
	if err := os.MkdirAll(filepath.Dir(source), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(repositoryRoot(t), source); err != nil {
		t.Fatal(err)
	}
	bin := filepath.Join(home, "bin")
	if err := os.MkdirAll(bin, 0o700); err != nil {
		t.Fatal(err)
	}
	log := filepath.Join(home, "calls.log")
	writeExecutable(t, filepath.Join(bin, "mise"), "#!/bin/sh\nif [ \"$1\" = --version ]; then echo '"+version+" linux-x64'; else printf 'mise %s\\n' \"$*\" >>\"$BOOTSTRAP_LOG\"; fi\n")
	writeExecutable(t, filepath.Join(bin, "chezmoi"), "#!/bin/sh\nprintf 'chezmoi %s\\n' \"$*\" >>\"$BOOTSTRAP_LOG\"\n")
	writeExecutable(t, filepath.Join(bin, "git"), "#!/bin/sh\nprintf 'git %s\\n' \"$*\" >>\"$BOOTSTRAP_LOG\"\n")
	writeExecutable(t, filepath.Join(bin, "curl"), "#!/bin/sh\nexit 99\n")
	return home, bin, log
}

func bootstrapCommand(t *testing.T, home, bin, log string) *exec.Cmd {
	t.Helper()
	command := exec.Command("bash", readRepoPath(t, "install.sh"))
	command.Env = []string{"HOME=" + home, "PATH=" + bin + ":/usr/bin:/bin", "BOOTSTRAP_LOG=" + log, "CI=true", "SKIP_GIT_PULL=true"}
	return command
}

func writeExecutable(t *testing.T, path, content string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0o700); err != nil {
		t.Fatal(err)
	}
}

func readOptionalFile(t *testing.T, path string) string {
	t.Helper()
	content, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return ""
	}
	if err != nil {
		t.Fatal(err)
	}
	return string(content)
}
