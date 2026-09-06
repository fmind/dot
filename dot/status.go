package dot

import (
	"context"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"
	"time"

	"github.com/urfave/cli/v3"
	"golang.org/x/sync/errgroup"
)

// SystemStatus represents the overall status of external services and git repositories.
type SystemStatus struct {
	Docker       DockerStatus `json:"docker"`
	Repositories []RepoStatus `json:"repositories"`
}

// DockerStatus represents the status of the local Docker daemon.
type DockerStatus struct {
	Details   string `json:"details,omitzero"`
	Installed bool   `json:"installed"`
	Running   bool   `json:"running"`
}

// RepoStatus represents the status of a single Git repository.
type RepoStatus struct {
	Err        error  `json:"-"`
	Name       string `json:"name"`
	ParentBase string `json:"parent"`
	Branch     string `json:"branch"`
	Error      string `json:"error,omitzero"`
	Dirty      bool   `json:"dirty"`
}

// NewStatusCmd constructs the top-level status command.
func NewStatusCmd(state *GlobalState) *cli.Command {
	return &cli.Command{
		Name:    "status",
		Aliases: []string{"s"},
		Usage:   "Show a unified summary of git repositories and Docker status",
		Flags: []cli.Flag{
			&cli.BoolFlag{
				Name:    "json",
				Aliases: []string{"j"},
				Usage:   "Output results in structured JSON format",
			},
		},
		Action: func(ctx context.Context, cmd *cli.Command) error {
			return RunStatus(ctx, state, cmd.Bool("json"))
		},
	}
}

// RunStatus outputs telemetry regarding Docker and git repositories.
func RunStatus(ctx context.Context, state *GlobalState, isJSON bool) error {
	if err := checkGit(state); err != nil {
		return err
	}
	status, err := GatherStatus(ctx, state)
	if err != nil {
		return err
	}
	if isJSON {
		bz, err := json.MarshalIndent(status, "", "  ")
		if err != nil {
			return fmt.Errorf("failed to marshal status: %w", err)
		}
		_, _ = fmt.Fprintln(state.Stdout, string(bz))
		return nil
	}
	RenderStatus(status, state)
	return nil
}

// GatherStatus queries telemetry regarding Docker and git repositories concurrently.
func GatherStatus(ctx context.Context, state *GlobalState) (*SystemStatus, error) {
	g, groupCtx := errgroup.WithContext(ctx)
	g.SetLimit(8)

	var dockerStatus DockerStatus
	g.Go(func() error {
		dockerStatus = gatherDockerStatus(groupCtx, state)
		return nil
	})

	reposToScan := findGitRepos(state)
	repoStatuses := make([]RepoStatus, len(reposToScan))
	for i, path := range reposToScan {
		g.Go(func() error {
			repoStatuses[i] = gatherRepoStatus(groupCtx, state, path)
			return nil
		})
	}

	_ = g.Wait()

	if ctx.Err() != nil {
		return nil, ctx.Err()
	}

	return &SystemStatus{
		Docker:       dockerStatus,
		Repositories: repoStatuses,
	}, nil
}

// probeTimeout bounds each concurrent status probe, mirroring verify's per-checker guard.
const probeTimeout = 30 * time.Second

func gatherDockerStatus(ctx context.Context, state *GlobalState) DockerStatus {
	ctx, cancel := context.WithTimeout(ctx, probeTimeout)
	defer cancel()

	var status DockerStatus
	if _, err := state.Runner.LookPath("docker"); err != nil {
		status.Details = "command not found"
		return status
	}
	status.Installed = true
	info, err := state.Runner.Run(ctx, "", nil, "docker", "info", "--format", "{{.Name}} (Containers: {{.Containers}}, Running: {{.ContainersRunning}})")
	if err != nil {
		if ctx.Err() != nil {
			status.Details = "inspection timed out"
		} else {
			status.Details = "inspection command failed"
		}
		return status
	}
	info = strings.TrimSpace(info)
	if info == "" {
		return status
	}
	if !strings.Contains(info, "(Containers:") || !strings.Contains(info, ", Running:") {
		status.Details = "inspection returned malformed output"
		return status
	}
	status.Running = true
	status.Details = info
	return status
}

func gatherRepoStatus(ctx context.Context, state *GlobalState, path string) RepoStatus {
	ctx, cancel := context.WithTimeout(ctx, probeTimeout)
	defer cancel()

	repoName := filepath.Base(path)
	parentBase := filepath.Base(filepath.Dir(path))

	branch, err := repoBranch(ctx, state, path)
	if err != nil {
		return RepoStatus{
			Name:       repoName,
			ParentBase: parentBase,
			Err:        err,
			Error:      err.Error(),
		}
	}

	status, err := state.Runner.Run(ctx, path, nil, "git", "status", "--porcelain")
	if err != nil {
		return RepoStatus{
			Name:       repoName,
			ParentBase: parentBase,
			Branch:     branch,
			Err:        err,
			Error:      err.Error(),
		}
	}

	return RepoStatus{
		Name:       repoName,
		ParentBase: parentBase,
		Branch:     branch,
		Dirty:      strings.TrimSpace(status) != "",
	}
}

// RenderStatus prints the SystemStatus in a structured terminal output.
func RenderStatus(status *SystemStatus, state *GlobalState) {
	// 1. Docker Status
	section(state.Stdout, "Docker Daemon")
	switch {
	case !status.Docker.Installed:
		_, _ = fmt.Fprintf(state.Stdout, "  %s Not installed.\n", failIcon)
	case status.Docker.Running:
		_, _ = fmt.Fprintf(state.Stdout, "  %s Running: %s\n", passIcon, status.Docker.Details)
	default:
		if status.Docker.Details == "" {
			_, _ = fmt.Fprintf(state.Stdout, "  %s Stopped.\n", failIcon)
		} else {
			_, _ = fmt.Fprintf(state.Stdout, "  %s Stopped or unreachable: %s.\n", failIcon, status.Docker.Details)
		}
	}

	// 2. Git Workspaces Status
	_, _ = fmt.Fprintln(state.Stdout)
	section(state.Stdout, "Git Repositories")
	if len(status.Repositories) == 0 {
		_, _ = fmt.Fprintln(state.Stdout, "  No repositories found in configured pull directories.")
		return
	}
	for _, repo := range status.Repositories {
		dirty := ""
		if repo.Dirty {
			dirty = " [" + yellow("dirty") + "]"
		}
		branch := repo.Branch
		if repo.Err != nil {
			branch = "error"
		}
		_, _ = fmt.Fprintf(state.Stdout, "  ▶ %s/%s [%s]%s\n", repo.ParentBase, repo.Name, branch, dirty)
	}
}
