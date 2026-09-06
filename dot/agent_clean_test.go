package dot

import (
	"bytes"
	"context"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/urfave/cli/v3"
)

func TestParseCleanTargets(t *testing.T) {
	tests := []struct {
		name    string
		args    []string
		want    []string
		wantErr bool
	}{
		{
			name: "empty args defaults to all",
			args: nil,
			want: []string{"prompts", "proposals", "reports"},
		},
		{
			name: "explicit all",
			args: []string{"all"},
			want: []string{"prompts", "proposals", "reports"},
		},
		{
			name: "uppercase ALL",
			args: []string{"ALL"},
			want: []string{"prompts", "proposals", "reports"},
		},
		{
			name: "prompts only",
			args: []string{"prompts"},
			want: []string{"prompts"},
		},
		{
			name: "proposals only",
			args: []string{"proposals"},
			want: []string{"proposals"},
		},
		{
			name: "reports only",
			args: []string{"reports"},
			want: []string{"reports"},
		},
		{
			name: "all three as separate args",
			args: []string{"prompts", "proposals", "reports"},
			want: []string{"prompts", "proposals", "reports"},
		},
		{
			name: "comma separated",
			args: []string{"prompts,proposals,reports"},
			want: []string{"prompts", "proposals", "reports"},
		},
		{
			name: "all and prompts combined",
			args: []string{"all", "prompts"},
			want: []string{"prompts", "proposals", "reports"},
		},
		{
			name:    "unknown target",
			args:    []string{"unknown"},
			wantErr: true,
		},
		{
			name:    "comma separated with unknown target",
			args:    []string{"prompts,invalid"},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseCleanTargets(tt.args)
			if (err != nil) != tt.wantErr {
				t.Fatalf("parseCleanTargets() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && !reflect.DeepEqual(got, tt.want) {
				t.Errorf("parseCleanTargets() = %v, want %v", got, tt.want)
			}
		})
	}
}

func newCleanTestState(root string, out *bytes.Buffer) *GlobalState {
	runner := &FakeRunner{
		RunFunc: func(_ context.Context, _ string, _ io.Reader, name string, args ...string) (string, error) {
			if name == "git" && len(args) == 2 && args[0] == "rev-parse" && args[1] == "--show-toplevel" {
				return root + "\n", nil
			}
			return "", nil
		},
	}
	state := newTestState(runner)
	state.Stdout = out
	return state
}

func TestRunAgentClean_AllDefault(t *testing.T) {
	tempDir := t.TempDir()
	promptsDir := filepath.Join(tempDir, ".agents", "prompts")
	proposalsDir := filepath.Join(tempDir, ".agents", "proposals")
	reportsDir := filepath.Join(tempDir, ".agents", "reports")
	skillsDir := filepath.Join(tempDir, ".agents", "skills", "custom")

	if err := os.MkdirAll(promptsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(proposalsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(reportsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(skillsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	prompt1 := filepath.Join(promptsDir, "TASK.md")
	prompt2 := filepath.Join(promptsDir, "PLAN.md")
	prop1 := filepath.Join(proposalsDir, "FEAT.md")
	rep1 := filepath.Join(reportsDir, "AUDIT.html")
	preservedSkill := filepath.Join(skillsDir, "SKILL.md")

	for _, path := range []string{prompt1, prompt2, prop1, rep1, preservedSkill} {
		if err := os.WriteFile(path, []byte("content"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	var out bytes.Buffer
	state := newCleanTestState(tempDir, &out)

	if err := RunAgentClean(context.Background(), state, nil, false); err != nil {
		t.Fatalf("RunAgentClean failed: %v", err)
	}

	// Verify prompt, proposal, and report files were removed
	for _, path := range []string{prompt1, prompt2, prop1, rep1} {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Errorf("file %s should have been removed", path)
		}
	}

	// Verify skills directory and file were untouched
	if _, err := os.Stat(preservedSkill); err != nil {
		t.Errorf("skill file %s should be preserved: %v", preservedSkill, err)
	}

	// Verify prompts, proposals, and reports directories still exist
	for _, dir := range []string{promptsDir, proposalsDir, reportsDir} {
		if _, err := os.Stat(dir); err != nil {
			t.Errorf("directory %s should still exist: %v", dir, err)
		}
	}

	output := out.String()
	if !strings.Contains(output, "Cleaned 2 file(s) in .agents/prompts") {
		t.Errorf("expected clean prompts message in output: %s", output)
	}
	if !strings.Contains(output, "Cleaned 1 file(s) in .agents/proposals") {
		t.Errorf("expected clean proposals message in output: %s", output)
	}
	if !strings.Contains(output, "Cleaned 1 file(s) in .agents/reports") {
		t.Errorf("expected clean reports message in output: %s", output)
	}
}

func TestRunAgentClean_PromptsOnly(t *testing.T) {
	tempDir := t.TempDir()
	promptsDir := filepath.Join(tempDir, ".agents", "prompts")
	proposalsDir := filepath.Join(tempDir, ".agents", "proposals")

	if err := os.MkdirAll(promptsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(proposalsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	promptFile := filepath.Join(promptsDir, "TASK.md")
	propFile := filepath.Join(proposalsDir, "FEAT.md")

	for _, path := range []string{promptFile, propFile} {
		if err := os.WriteFile(path, []byte("content"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	var out bytes.Buffer
	state := newCleanTestState(tempDir, &out)

	if err := RunAgentClean(context.Background(), state, []string{"prompts"}, false); err != nil {
		t.Fatalf("RunAgentClean failed: %v", err)
	}

	if _, err := os.Stat(promptFile); !os.IsNotExist(err) {
		t.Errorf("prompt file should have been removed: %s", promptFile)
	}
	if _, err := os.Stat(propFile); err != nil {
		t.Errorf("proposal file should be preserved: %s", propFile)
	}

	output := out.String()
	if !strings.Contains(output, "Cleaned 1 file(s) in .agents/prompts") {
		t.Errorf("expected clean prompts message in output: %s", output)
	}
	if strings.Contains(output, ".agents/proposals") {
		t.Errorf("proposals should not have been mentioned in output: %s", output)
	}
}

func TestRunAgentClean_ProposalsOnly(t *testing.T) {
	tempDir := t.TempDir()
	promptsDir := filepath.Join(tempDir, ".agents", "prompts")
	proposalsDir := filepath.Join(tempDir, ".agents", "proposals")

	if err := os.MkdirAll(promptsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(proposalsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	promptFile := filepath.Join(promptsDir, "TASK.md")
	propFile := filepath.Join(proposalsDir, "FEAT.md")

	for _, path := range []string{promptFile, propFile} {
		if err := os.WriteFile(path, []byte("content"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	var out bytes.Buffer
	state := newCleanTestState(tempDir, &out)

	if err := RunAgentClean(context.Background(), state, []string{"proposals"}, false); err != nil {
		t.Fatalf("RunAgentClean failed: %v", err)
	}

	if _, err := os.Stat(propFile); !os.IsNotExist(err) {
		t.Errorf("proposal file should have been removed: %s", propFile)
	}
	if _, err := os.Stat(promptFile); err != nil {
		t.Errorf("prompt file should be preserved: %s", promptFile)
	}

	output := out.String()
	if !strings.Contains(output, "Cleaned 1 file(s) in .agents/proposals") {
		t.Errorf("expected clean proposals message in output: %s", output)
	}
	if strings.Contains(output, ".agents/prompts") {
		t.Errorf("prompts should not have been mentioned in output: %s", output)
	}
}

func TestRunAgentClean_ReportsOnly(t *testing.T) {
	tempDir := t.TempDir()
	promptsDir := filepath.Join(tempDir, ".agents", "prompts")
	reportsDir := filepath.Join(tempDir, ".agents", "reports")

	if err := os.MkdirAll(promptsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(reportsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	promptFile := filepath.Join(promptsDir, "TASK.md")
	repFile := filepath.Join(reportsDir, "AUDIT.html")

	for _, path := range []string{promptFile, repFile} {
		if err := os.WriteFile(path, []byte("content"), 0o600); err != nil {
			t.Fatal(err)
		}
	}

	var out bytes.Buffer
	state := newCleanTestState(tempDir, &out)

	if err := RunAgentClean(context.Background(), state, []string{"reports"}, false); err != nil {
		t.Fatalf("RunAgentClean failed: %v", err)
	}

	if _, err := os.Stat(repFile); !os.IsNotExist(err) {
		t.Errorf("report file should have been removed: %s", repFile)
	}
	if _, err := os.Stat(promptFile); err != nil {
		t.Errorf("prompt file should be preserved: %s", promptFile)
	}

	output := out.String()
	if !strings.Contains(output, "Cleaned 1 file(s) in .agents/reports") {
		t.Errorf("expected clean reports message in output: %s", output)
	}
	if strings.Contains(output, ".agents/prompts") {
		t.Errorf("prompts should not have been mentioned in output: %s", output)
	}
}

func TestRunAgentClean_DryRun(t *testing.T) {
	tempDir := t.TempDir()
	promptsDir := filepath.Join(tempDir, ".agents", "prompts")

	if err := os.MkdirAll(promptsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	promptFile := filepath.Join(promptsDir, "TASK.md")
	if err := os.WriteFile(promptFile, []byte("content"), 0o600); err != nil {
		t.Fatal(err)
	}

	var out bytes.Buffer
	state := newCleanTestState(tempDir, &out)

	if err := RunAgentClean(context.Background(), state, []string{"prompts"}, true); err != nil {
		t.Fatalf("RunAgentClean failed: %v", err)
	}

	// In dry-run, file should NOT be removed
	if _, err := os.Stat(promptFile); err != nil {
		t.Errorf("file should still exist in dry-run mode: %v", err)
	}

	output := out.String()
	if !strings.Contains(output, "Would clean 1 file(s) in .agents/prompts") {
		t.Errorf("expected dry-run message: %s", output)
	}
	if !strings.Contains(output, ".agents/prompts/TASK.md") {
		t.Errorf("expected previewed file path in output: %s", output)
	}
}

func TestRunAgentClean_NonExistentDirectories(t *testing.T) {
	tempDir := t.TempDir()
	var out bytes.Buffer
	state := newCleanTestState(tempDir, &out)

	if err := RunAgentClean(context.Background(), state, nil, false); err != nil {
		t.Fatalf("RunAgentClean failed: %v", err)
	}

	output := out.String()
	if !strings.Contains(output, "Cleaned 0 file(s) in .agents/prompts") {
		t.Errorf("expected 0 files cleaned for prompts: %s", output)
	}
	if !strings.Contains(output, "Cleaned 0 file(s) in .agents/proposals") {
		t.Errorf("expected 0 files cleaned for proposals: %s", output)
	}
	if !strings.Contains(output, "Cleaned 0 file(s) in .agents/reports") {
		t.Errorf("expected 0 files cleaned for reports: %s", output)
	}
}

func TestRunAgentClean_Subdirectories(t *testing.T) {
	tempDir := t.TempDir()
	subDir := filepath.Join(tempDir, ".agents", "prompts", "nested")
	if err := os.MkdirAll(subDir, 0o755); err != nil {
		t.Fatal(err)
	}
	nestedFile := filepath.Join(subDir, "SUB.md")
	if err := os.WriteFile(nestedFile, []byte("content"), 0o600); err != nil {
		t.Fatal(err)
	}

	var out bytes.Buffer
	state := newCleanTestState(tempDir, &out)

	if err := RunAgentClean(context.Background(), state, []string{"prompts"}, false); err != nil {
		t.Fatalf("RunAgentClean failed: %v", err)
	}

	if _, err := os.Stat(subDir); !os.IsNotExist(err) {
		t.Errorf("subdirectory should have been removed: %s", subDir)
	}
}

func TestAgentCleanCLI_ShortcutAndArgs(t *testing.T) {
	tempDir := t.TempDir()
	promptsDir := filepath.Join(tempDir, ".agents", "prompts")
	proposalsDir := filepath.Join(tempDir, ".agents", "proposals")
	reportsDir := filepath.Join(tempDir, ".agents", "reports")

	if err := os.MkdirAll(promptsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(proposalsDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(reportsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	makeFiles := func() {
		_ = os.WriteFile(filepath.Join(promptsDir, "P.md"), []byte("p"), 0o600)
		_ = os.WriteFile(filepath.Join(proposalsDir, "PR.md"), []byte("pr"), 0o600)
		_ = os.WriteFile(filepath.Join(reportsDir, "R.html"), []byte("r"), 0o600)
	}

	makeFiles()

	var out bytes.Buffer
	state := newCleanTestState(tempDir, &out)
	app := &cli.Command{
		Commands: []*cli.Command{
			NewAgentCmd(state),
		},
	}

	// Test full command `dot agent clean`
	if err := app.Run(context.Background(), []string{"dot", "agent", "clean"}); err != nil {
		t.Fatalf("dot agent clean failed: %v", err)
	}
	if !strings.Contains(out.String(), "Cleaned 1 file(s) in .agents/prompts") {
		t.Errorf("unexpected output: %s", out.String())
	}

	// Recreate files and test shortcut `dot a c`
	out.Reset()
	makeFiles()
	if err := app.Run(context.Background(), []string{"dot", "a", "c"}); err != nil {
		t.Fatalf("dot a c failed: %v", err)
	}
	if !strings.Contains(out.String(), "Cleaned 1 file(s) in .agents/prompts") ||
		!strings.Contains(out.String(), "Cleaned 1 file(s) in .agents/proposals") ||
		!strings.Contains(out.String(), "Cleaned 1 file(s) in .agents/reports") {
		t.Errorf("unexpected output for dot a c: %s", out.String())
	}

	// Recreate files and test shortcut with target `dot a c prompts`
	out.Reset()
	makeFiles()
	if err := app.Run(context.Background(), []string{"dot", "a", "c", "prompts"}); err != nil {
		t.Fatalf("dot a c prompts failed: %v", err)
	}
	if !strings.Contains(out.String(), "Cleaned 1 file(s) in .agents/prompts") {
		t.Errorf("unexpected output: %s", out.String())
	}
	if strings.Contains(out.String(), "proposals") || strings.Contains(out.String(), "reports") {
		t.Errorf("proposals and reports should not be cleaned: %s", out.String())
	}

	// Recreate files and test shortcut with target `dot a c reports`
	out.Reset()
	makeFiles()
	if err := app.Run(context.Background(), []string{"dot", "a", "c", "reports"}); err != nil {
		t.Fatalf("dot a c reports failed: %v", err)
	}
	if !strings.Contains(out.String(), "Cleaned 1 file(s) in .agents/reports") {
		t.Errorf("unexpected output: %s", out.String())
	}
	if strings.Contains(out.String(), "prompts") || strings.Contains(out.String(), "proposals") {
		t.Errorf("prompts and proposals should not be cleaned: %s", out.String())
	}

	// Invalid target should fail
	if err := app.Run(context.Background(), []string{"dot", "a", "c", "badtarget"}); err == nil {
		t.Errorf("expected error for invalid target, got nil")
	}
}

func TestRunAgentCleanRejectsSymlinkDirectories(t *testing.T) {
	for _, component := range []string{".agents", ".agents/prompts"} {
		t.Run(component, func(t *testing.T) {
			root := t.TempDir()
			outside := t.TempDir()
			if err := os.MkdirAll(filepath.Join(outside, "prompts"), 0o700); err != nil {
				t.Fatal(err)
			}
			for _, name := range []string{"keep.md", "prompts/keep.md"} {
				if err := os.WriteFile(filepath.Join(outside, name), []byte("preserve"), 0o600); err != nil {
					t.Fatal(err)
				}
			}
			link := filepath.Join(root, component)
			if err := os.MkdirAll(filepath.Dir(link), 0o700); err != nil {
				t.Fatal(err)
			}
			if err := os.Symlink(outside, link); err != nil {
				t.Fatal(err)
			}
			var out bytes.Buffer
			state := newCleanTestState(root, &out)
			if err := RunAgentClean(t.Context(), state, []string{"prompts"}, false); err == nil {
				t.Error("must reject a symlinked cleanup directory")
			}
			for _, name := range []string{"keep.md", "prompts/keep.md"} {
				if _, err := os.Stat(filepath.Join(outside, name)); err != nil {
					t.Errorf("outside file changed: %v", err)
				}
			}
		})
	}
}
