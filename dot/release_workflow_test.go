package dot

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestReleaseWorkflowGatesExactTaggedSHA(t *testing.T) {
	workflow := readRepoFile(t, ".github/workflows/cd.yml")
	for _, required := range []string{"actions: read", "release-exact-sha.sh", "GITHUB_REF_NAME", "gh release view"} {
		if !strings.Contains(workflow, required) {
			t.Errorf("release workflow lacks %q", required)
		}
	}
}

func TestReleaseWorkflowGateRejectsWrongSHAAndFailedCI(t *testing.T) {
	repo := t.TempDir()
	runGit(t, repo, "init", "-q")
	runGit(t, repo, "config", "user.name", "test")
	runGit(t, repo, "config", "user.email", "test@example.invalid")
	if err := os.WriteFile(filepath.Join(repo, "fixture"), []byte("fixture"), 0o600); err != nil {
		t.Fatal(err)
	}
	runGit(t, repo, "add", "fixture")
	runGit(t, repo, "commit", "-qm", "fixture")
	sha := strings.TrimSpace(runGit(t, repo, "rev-parse", "HEAD"))
	runGit(t, repo, "tag", "v1.0.0")

	bin := filepath.Join(repo, "bin")
	if err := os.Mkdir(bin, 0o700); err != nil {
		t.Fatal(err)
	}
	gh := filepath.Join(bin, "gh")
	if err := os.WriteFile(gh, []byte("#!/bin/sh\nprintf '%s\\n' \"$GH_FIXTURE\"\n"), 0o700); err != nil {
		t.Fatal(err)
	}

	t.Run("success", func(t *testing.T) {
		runReleaseGate(t, repo, bin, sha, `[{"databaseId":1,"headSha":"`+sha+`","status":"completed","conclusion":"success","workflowName":"CI","createdAt":"2026-09-05T00:00:00Z"}]`, true)
	})
	t.Run("wrong sha only", func(t *testing.T) {
		runReleaseGate(t, repo, bin, sha, `[{"databaseId":1,"headSha":"wrong","status":"completed","conclusion":"success","workflowName":"CI","createdAt":"2026-09-05T00:00:00Z"}]`, false)
	})
	t.Run("failed", func(t *testing.T) {
		runReleaseGate(t, repo, bin, sha, `[{"databaseId":1,"headSha":"`+sha+`","status":"completed","conclusion":"failure","workflowName":"CI","createdAt":"2026-09-05T00:00:00Z"}]`, false)
	})
}

func runReleaseGate(t *testing.T, repo, bin, sha, fixture string, wantSuccess bool) {
	t.Helper()
	command := exec.Command(readRepoPath(t, "dot/scripts/release-exact-sha.sh"))
	command.Dir = repo
	command.Env = append(os.Environ(), "PATH="+bin+":"+os.Getenv("PATH"), "GITHUB_SHA="+sha, "GITHUB_REF_NAME=v1.0.0", "GH_FIXTURE="+fixture, "RELEASE_GATE_ATTEMPTS=1", "RELEASE_GATE_INTERVAL_SECONDS=0")
	err := command.Run()
	if (err == nil) != wantSuccess {
		t.Fatalf("gate error = %v, want success %v", err, wantSuccess)
	}
}

func runGit(t *testing.T, dir string, args ...string) string {
	t.Helper()
	command := exec.Command("git", args...)
	command.Dir = dir
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v: %v: %s", args, err, output)
	}
	return string(output)
}
