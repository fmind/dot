package dot

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestCloudRunSkillBuildReceipt(t *testing.T) {
	var workflow struct {
		Jobs map[string]struct {
			Steps []struct {
				ID    string            `yaml:"id"`
				Run   string            `yaml:"run"`
				Uses  string            `yaml:"uses"`
				With  map[string]string `yaml:"with"`
				Shell string            `yaml:"shell"`
			} `yaml:"steps"`
		} `yaml:"jobs"`
	}
	if err := yaml.Unmarshal([]byte(readRepoFile(t, "skills/cloud-run/references/deploy.yml")), &workflow); err != nil {
		t.Fatal(err)
	}
	var script string
	var runtimeIdentity bool
	for _, step := range workflow.Jobs["deploy-cloud-run"].Steps {
		if step.ID == "image" {
			script = step.Run
			if step.Shell != "bash" {
				t.Fatal("image receipt requires the declared Bash failure semantics")
			}
		}
		if strings.HasPrefix(step.Uses, "google-github-actions/deploy-cloudrun@") {
			runtimeIdentity = strings.Contains(step.With["flags"], "--service-account=${{ vars.GCP_RUNTIME_SA }}")
		}
	}
	if script == "" || !runtimeIdentity {
		t.Fatal("deployment template must build an image receipt and select its runtime identity")
	}
	const digest = "registry.example/app@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	for _, test := range []struct {
		name           string
		receipt        string
		exit           string
		wantOK         bool
		missingRuntime bool
	}{
		{name: "digest", receipt: digest + "\n", exit: "0", wantOK: true},
		{name: "failed build with receipt", receipt: digest + "\n", exit: "7"},
		{name: "missing receipt", exit: "0"},
		{name: "tag instead of digest", receipt: "registry.example/app:latest\n", exit: "0"},
		{name: "multiple images", receipt: digest + "\n" + digest + "\n", exit: "0"},
		{name: "missing runtime identity", receipt: digest + "\n", exit: "0", missingRuntime: true},
	} {
		t.Run(test.name, func(t *testing.T) {
			root := t.TempDir()
			bin := filepath.Join(root, "bin")
			writeStarterFile(t, root, "bin/mise", `#!/usr/bin/env bash
set -eu
touch "$RUNNER_TEMP/build-called"
test "$1" = run && test "$2" = build:image && test "$3" = -- && test "$4" = --push=true && test "$5" = --image-refs
if [ -n "$BUILD_RECEIPT" ]; then printf '%s' "$BUILD_RECEIPT" > "$6"; fi
exit "$BUILD_EXIT"
`)
			if err := os.Chmod(filepath.Join(bin, "mise"), 0o700); err != nil {
				t.Fatal(err)
			}
			writeStarterFile(t, root, "output", "")
			runtimeAccount := "service-runtime@example-project.iam.gserviceaccount.com"
			if test.missingRuntime {
				runtimeAccount = ""
			}
			cmd := exec.CommandContext(t.Context(), "bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script)
			cmd.Dir = root
			cmd.Env = append(os.Environ(), "PATH="+bin+":"+os.Getenv("PATH"), "RUNNER_TEMP="+root,
				"GITHUB_OUTPUT="+filepath.Join(root, "output"), "BUILD_RECEIPT="+test.receipt, "BUILD_EXIT="+test.exit, "GCP_RUNTIME_SA="+runtimeAccount)
			output, err := cmd.CombinedOutput()
			if (err == nil) != test.wantOK {
				t.Fatalf("build result = %v, want success %v: %s", err, test.wantOK, output)
			}
			receipt, err := os.ReadFile(filepath.Join(root, "output"))
			if err != nil {
				t.Fatal(err)
			}
			want := ""
			if test.wantOK {
				want = "ref=" + digest + "\n"
			}
			if string(receipt) != want {
				t.Fatalf("deployment output = %q, want %q", receipt, want)
			}
			if test.missingRuntime {
				if _, err := os.Stat(filepath.Join(root, "build-called")); !os.IsNotExist(err) {
					t.Fatal("missing runtime identity must fail before publishing an image")
				}
			}
		})
	}
}

func TestOpengrepSkillReconcilesPinnedRules(t *testing.T) {
	source := t.TempDir()
	runGit(t, source, "init", "-q")
	writeStarterFile(t, source, "rule.yaml", "first version\n")
	first := commitSkillRule(t, source)
	writeStarterFile(t, source, "rule.yaml", "second version\n")
	second := commitSkillRule(t, source)
	script := readRepoPath(t, "skills/opengrep/scripts/install-rules.sh")
	for _, initial := range []string{"missing", "empty", "initialized"} {
		t.Run(initial, func(t *testing.T) {
			rules := filepath.Join(t.TempDir(), "rules")
			if initial != "missing" {
				if err := os.Mkdir(rules, 0o700); err != nil {
					t.Fatal(err)
				}
			}
			if initial == "initialized" {
				runGit(t, rules, "init", "-q")
			}
			install := func(pin, remote string, wantOK bool) {
				t.Helper()
				cmd := exec.CommandContext(t.Context(), "bash", script, pin, rules, remote)
				output, err := cmd.CombinedOutput()
				if (err == nil) != wantOK {
					t.Fatalf("install %s: %v, want success %v: %s", pin, err, wantOK, output)
				}
			}
			install(first, source, true)
			// The cached pin must work offline; a changed pin must update existing rules.
			install(first, filepath.Join(source, "unavailable"), true)
			install(second, source, true)
			if head := strings.TrimSpace(runGit(t, rules, "rev-parse", "HEAD")); head != second {
				t.Fatalf("updated rules HEAD = %s, want %s", head, second)
			}
			writeStarterFile(t, rules, "rule.yaml", "local work\n")
			install(first, source, false)
			data, err := os.ReadFile(filepath.Join(rules, "rule.yaml"))
			if err != nil || string(data) != "local work\n" {
				t.Fatalf("local rule was not preserved: %v, %q", err, data)
			}
		})
	}
}

func commitSkillRule(t *testing.T, directory string) string {
	t.Helper()
	runGit(t, directory, "add", "rule.yaml")
	runGit(t, directory, "-c", "core.hooksPath="+os.DevNull, "-c", "commit.gpgsign=false",
		"-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "rule fixture")
	return strings.TrimSpace(runGit(t, directory, "rev-parse", "HEAD"))
}
