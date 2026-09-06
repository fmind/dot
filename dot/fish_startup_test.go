package dot

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestFishNoninteractiveStartupResolvesMiseTools(t *testing.T) {
	fish, err := exec.LookPath("fish")
	if err != nil {
		t.Fatal(err)
	}
	home := t.TempDir()
	t.Setenv("HOME", home)
	t.Setenv("PATH", "/usr/bin:/bin")
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(home, ".config"))
	t.Setenv("XDG_DATA_HOME", filepath.Join(home, ".local", "share"))
	shim := filepath.Join(home, ".local", "share", "mise", "shims", "dot-fish-startup-probe")
	if err := os.MkdirAll(filepath.Dir(shim), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(shim, []byte("#!/bin/sh\nexit 0\n"), 0o700); err != nil {
		t.Fatal(err)
	}
	// Normal startup installs Fish's fish_user_paths handler; the disposable
	// config directory keeps user configuration out without disabling that handler.
	command := exec.Command(fish, "-c",
		`source "$argv[1]"; source "$argv[2]"; command -q dot-fish-startup-probe`,
		readRepoPath(t, "dot_config/fish/conf.d/paths.fish"), readRepoPath(t, "dot_config/fish/conf.d/plugins.fish"))
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("noninteractive Fish cannot resolve a mise tool: %v: %s", err, output)
	}
}

func TestFishStartupKeepsGeneratorsInteractive(t *testing.T) {
	source := readRepoFile(t, "dot_config/fish/conf.d/plugins.fish")
	if strings.Contains(source, "mise activate fish --shims") {
		t.Fatal("noninteractive Fish must use the static mise shims PATH, not generate activation code")
	}
	for _, generator := range []string{"mise activate fish", "carapace _carapace", "atuin init fish", "starship init fish", "zoxide init fish"} {
		if !strings.Contains(source, generator) {
			t.Fatalf("interactive setup lost %q", generator)
		}
	}
}

func TestFishStartupSourceParses(t *testing.T) {
	command := exec.Command("fish", "--no-config", "--no-execute", readRepoPath(t, "dot_config/fish/conf.d/plugins.fish"))
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("Fish startup source is invalid: %v: %s", err, output)
	}
}

func readRepoPath(t *testing.T, name string) string {
	t.Helper()
	return repositoryRoot(t) + "/" + name
}
