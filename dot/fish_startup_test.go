package dot

import (
	"os/exec"
	"strings"
	"testing"
)

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
