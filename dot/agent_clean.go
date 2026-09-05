package dot

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"github.com/urfave/cli/v3"
)

const (
	cleanTargetAll       = "all"
	cleanTargetPrompts   = "prompts"
	cleanTargetProposals = "proposals"
)

var validCleanTargets = map[string]struct{}{
	cleanTargetAll:       {},
	cleanTargetPrompts:   {},
	cleanTargetProposals: {},
}

// NewAgentCleanCmd constructs the `dot agent clean` command.
func NewAgentCleanCmd(state *GlobalState) *cli.Command {
	return &cli.Command{
		Name:      "clean",
		Aliases:   []string{"c"},
		Usage:     "Clean up content in .agents/{prompts,proposals}",
		ArgsUsage: "[all|prompts|proposals]",
		Flags: []cli.Flag{
			&cli.BoolFlag{
				Name:    "dry-run",
				Aliases: []string{"n"},
				Usage:   "Preview files that would be removed without deleting them",
			},
		},
		Action: func(ctx context.Context, cmd *cli.Command) error {
			return RunAgentClean(ctx, state, cmd.Args().Slice(), cmd.Bool("dry-run"))
		},
	}
}

// parseCleanTargets normalizes and validates target operands. If no arguments are
// given, it defaults to all targets (prompts and proposals).
func parseCleanTargets(args []string) ([]string, error) {
	if len(args) == 0 {
		return []string{cleanTargetPrompts, cleanTargetProposals}, nil
	}

	cleanPrompts := false
	cleanProposals := false

	for _, rawArg := range args {
		for token := range strings.SplitSeq(rawArg, ",") {
			token = strings.ToLower(strings.TrimSpace(token))
			if token == "" {
				continue
			}
			if _, ok := validCleanTargets[token]; !ok {
				return nil, fmt.Errorf("unknown target %q: must be one of all, prompts, proposals", token)
			}
			switch token {
			case cleanTargetAll:
				cleanPrompts = true
				cleanProposals = true
			case cleanTargetPrompts:
				cleanPrompts = true
			case cleanTargetProposals:
				cleanProposals = true
			}
		}
	}

	var targets []string
	if cleanPrompts {
		targets = append(targets, cleanTargetPrompts)
	}
	if cleanProposals {
		targets = append(targets, cleanTargetProposals)
	}
	return targets, nil
}

// resolveProjectRoot finds the repository root using git rev-parse, falling back to CWD.
func resolveProjectRoot(ctx context.Context, state *GlobalState) (string, error) {
	if state != nil && state.Runner != nil {
		out, err := state.Runner.Run(ctx, "", nil, "git", "rev-parse", "--show-toplevel")
		if err == nil && strings.TrimSpace(out) != "" {
			return strings.TrimSpace(out), nil
		}
	}
	cwd, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("failed to get current working directory: %w", err)
	}
	return cwd, nil
}

// RunAgentClean removes generated contents inside .agents/prompts and/or .agents/proposals.
func RunAgentClean(ctx context.Context, state *GlobalState, args []string, dryRun bool) error {
	targets, err := parseCleanTargets(args)
	if err != nil {
		return err
	}

	projectRoot, err := resolveProjectRoot(ctx, state)
	if err != nil {
		return err
	}

	for _, target := range targets {
		if err := cleanTargetDirectory(state, projectRoot, target, dryRun); err != nil {
			return err
		}
	}
	return nil
}

func cleanTargetDirectory(state *GlobalState, projectRoot, target string, dryRun bool) error {
	relDir := filepath.Join(".agents", target)
	root, err := os.OpenRoot(projectRoot)
	if err != nil {
		return fmt.Errorf("open cleanup root: %w", err)
	}
	defer func() { _ = root.Close() }()

	// Refuse redirected cleanup directories, and confine every operation to the
	// opened root so a concurrent symlink replacement cannot escape the repository.
	for _, component := range []string{".agents", relDir} {
		info, statErr := root.Lstat(component)
		if errors.Is(statErr, os.ErrNotExist) {
			break
		}
		if statErr != nil {
			return fmt.Errorf("inspect %s: %w", component, statErr)
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("refusing symlinked cleanup directory %s", component)
		}
	}

	verb := "Cleaned"
	if dryRun {
		verb = "Would clean"
	}

	directory, err := root.OpenRoot(relDir)
	if errors.Is(err, os.ErrNotExist) {
		_, _ = fmt.Fprintf(state.Stdout, "%s %s 0 file(s) in %s\n", passIcon, verb, relDir)
		return nil
	}
	if err != nil {
		return fmt.Errorf("failed to read %s: %w", relDir, err)
	}

	defer func() { _ = directory.Close() }()
	entries, err := fs.ReadDir(directory.FS(), ".")
	if err != nil {
		return fmt.Errorf("read %s: %w", relDir, err)
	}

	count := 0
	for _, entry := range entries {
		itemRel := filepath.Join(relDir, entry.Name())

		if dryRun {
			_, _ = fmt.Fprintf(state.Stdout, "  %s %s\n", skipIcon, itemRel)
			count++
			continue
		}

		if err := directory.RemoveAll(entry.Name()); err != nil {
			return fmt.Errorf("failed to remove %s: %w", itemRel, err)
		}
		count++
		state.Logger.Debug("Removed agent file", "path", itemRel)
	}

	_, _ = fmt.Fprintf(state.Stdout, "%s %s %d file(s) in %s\n", passIcon, verb, count, relDir)
	return nil
}
