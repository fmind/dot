package dot

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRunStatus_JSON(t *testing.T) {
	// A repository whose branch lookup fails exercises the RepoStatus.Error serialization.
	tempDir := t.TempDir()
	repoDir := filepath.Join(tempDir, "brokenrepo")
	if err := os.MkdirAll(filepath.Join(repoDir, ".git"), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}

	runner := &FakeRunner{
		LookPathFunc: func(name string) (string, error) { return "/bin/" + name, nil },
		RunFunc: func(_ context.Context, _ string, _ io.Reader, name string, args ...string) (string, error) {
			switch name {
			case "docker":
				return "penguin (Containers: 1, Running: 1)", nil
			case "git":
				if len(args) > 0 && args[0] == "branch" {
					return "", errors.New("not a git repository")
				}
			}
			return "", nil
		},
	}
	state := newTestState(runner)
	state.Config.Pull.Directories = []string{tempDir}
	var buf bytes.Buffer
	state.Stdout = &buf

	if err := RunStatus(context.Background(), state, true); err != nil {
		t.Fatalf("RunStatus json: %v", err)
	}

	var got SystemStatus
	if err := json.Unmarshal(buf.Bytes(), &got); err != nil {
		t.Fatalf("output is not valid JSON: %v (%q)", err, buf.String())
	}
	if !got.Docker.Installed || !got.Docker.Running {
		t.Errorf("expected docker installed+running, got %+v", got.Docker)
	}
	if len(got.Repositories) != 1 || got.Repositories[0].Error == "" {
		t.Errorf("expected one repository carrying a serialized error, got %+v", got.Repositories)
	}
}

func TestGatherRepoStatus_StatusFailureIsReported(t *testing.T) {
	runner := &FakeRunner{
		RunFunc: func(_ context.Context, _ string, _ io.Reader, name string, args ...string) (string, error) {
			if name == "git" && args[0] == "branch" {
				return "main\n", nil
			}
			if name == "git" && args[0] == "status" {
				return "", errors.New("status unavailable")
			}
			return "", nil
		},
	}

	got := gatherRepoStatus(context.Background(), newTestState(runner), t.TempDir())
	if got.Err == nil || got.Error == "" {
		t.Fatalf("expected repository status error, got %+v", got)
	}
	if got.Dirty {
		t.Fatalf("repository with unknown status must not be reported dirty or clean: %+v", got)
	}
}

func TestRenderStatus(t *testing.T) {
	state := newTestState(&FakeRunner{})

	tests := []struct {
		name     string
		status   *SystemStatus
		contains []string
	}{
		{
			name:     "tools missing and no repositories",
			status:   &SystemStatus{},
			contains: []string{"Not installed.", "No repositories found"},
		},
		{
			name: "tools installed but down",
			status: &SystemStatus{
				Docker: DockerStatus{Installed: true},
			},
			contains: []string{"Stopped."},
		},
		{
			name: "everything up with a dirty and a broken repository",
			status: &SystemStatus{
				Docker: DockerStatus{Installed: true, Running: true, Details: "28.0.0"},
				Repositories: []RepoStatus{
					{Name: "dotfiles", ParentBase: "externals", Branch: "main", Dirty: true},
					{Name: "broken", ParentBase: "fmind", Err: errors.New("boom")},
				},
			},
			contains: []string{
				"Running: 28.0.0",
				"externals/dotfiles [main] [dirty]",
				// A repository that failed to probe must render as "error", never as a blank branch.
				"fmind/broken [error]",
			},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			var stdout bytes.Buffer
			state.Stdout = &stdout
			RenderStatus(tc.status, state)

			// Styling is applied unconditionally and stripped downstream, so compare
			// against the plain text a piped consumer would see.
			got := ansiPattern.ReplaceAllString(stdout.String(), "")
			for _, want := range tc.contains {
				if !strings.Contains(got, want) {
					t.Errorf("expected output to contain %q, got:\n%s", want, got)
				}
			}
		})
	}
}

func TestServiceStatusDistinguishesProbeFailureFromStopped(t *testing.T) {
	for _, test := range []struct {
		gather  func(*GlobalState) string
		runErr  error
		name    string
		output  string
		wantErr bool
	}{
		{name: "docker stopped", output: "", gather: func(state *GlobalState) string { return gatherDockerStatus(context.Background(), state).Details }},
		{name: "docker error", runErr: errors.New("credential-like-private-detail"), wantErr: true, gather: func(state *GlobalState) string { return gatherDockerStatus(context.Background(), state).Details }},
	} {
		t.Run(test.name, func(t *testing.T) {
			state := newTestState(&FakeRunner{RunFunc: func(context.Context, string, io.Reader, string, ...string) (string, error) {
				return test.output, test.runErr
			}})
			details := test.gather(state)
			if (details != "") != test.wantErr {
				t.Fatalf("details = %q, want diagnostic=%v", details, test.wantErr)
			}
			if strings.Contains(details, "credential-like-private-detail") {
				t.Fatal("diagnostic exposed unrestricted subprocess error")
			}
		})
	}
}
