package dot

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestSecurityWorkflowPublishesUnfixedReportWithoutWeakeningGate(t *testing.T) {
	workflow := readRepoFile(t, ".github/workflows/security.yml")
	for _, required := range []string{"mise run report:vuln", "actions/upload-artifact@v7", "mise run check:scan", "retention-days: 14"} {
		if !strings.Contains(workflow, required) {
			t.Errorf("security workflow lacks %q", required)
		}
	}
	script := readRepoFile(t, "dot/scripts/report-vuln.sh")
	for _, required := range []string{"--scanners vuln", "--ignore-unfixed=false", "--exit-code 0", "--format json"} {
		if !strings.Contains(script, required) {
			t.Errorf("advisory report lacks %q", required)
		}
	}
	rootTask := readRepoFile(t, "mise.toml")
	if !strings.Contains(rootTask, "trivy --config trivy.yaml fs --tf-vars") {
		t.Error("blocking Trivy gate was weakened or removed")
	}
}

func TestTaskVulnReportPropagatesScannerFailure(t *testing.T) {
	bin := t.TempDir()
	trivy := filepath.Join(bin, "trivy")
	if err := os.WriteFile(trivy, []byte("#!/bin/sh\nexit 42\n"), 0o700); err != nil {
		t.Fatal(err)
	}
	output := filepath.Join(t.TempDir(), "report.json")
	command := exec.Command(readRepoPath(t, "dot/scripts/report-vuln.sh"), output)
	command.Dir = repositoryRoot(t)
	command.Env = append(os.Environ(), "PATH="+bin+":"+os.Getenv("PATH"))
	if err := command.Run(); err == nil {
		t.Fatal("scanner execution failure must fail the informational report task")
	}
}
