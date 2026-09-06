package dot

import (
	"context"
	"fmt"
	"io/fs"
	"path/filepath"
	"strings"
)

// Whole-store sweeps behind `dot agent session sync`. The per-agent ingestion
// entrypoints are driven one session at a time by hooks; this file is
// the batch counterpart that walks every store and replays them through the same
// loggers, so a machine that missed hook events can still be brought up to date.

// syncOutcome is one agent's contribution to a sync run.
type syncOutcome struct {
	// verb distinguishes a store dot walked file by file ("checked") from one it
	// swept and ingested wholesale ("ingested").
	verb  string
	count int
}

// reportSyncOutcome prints one agent's tally. A blank line precedes any non-empty
// tally so per-session output stays visually separated from the summary.
func reportSyncOutcome(state *GlobalState, agent string, outcome syncOutcome) {
	if outcome.count > 0 {
		_, _ = fmt.Fprintln(state.Stderr)
	}
	_, _ = fmt.Fprintf(state.Stderr, "%s: %d %s\n", agent, outcome.count, outcome.verb)
}

// syncTranscriptSessions walks a JSONL transcript tree, ingesting every file whose
// path yields a session ID. The discovered path is handed to the per-agent logger as
// a synthetic hook payload so it never has to rediscover the file. The whole path is
// passed because not every agent names its transcript after the session: Grok names
// the containing directory instead.
func syncTranscriptSessions(ctx context.Context, sourceState *GlobalState, root, label string, sessionIDOf func(path string) string, log agentSessionLogger) (int, error) {
	count := 0
	walkErr := filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".jsonl") {
			return nil
		}
		sessionID := sessionIDOf(path)
		if sessionID == "" {
			return nil
		}
		transcriptState, stateErr := sessionStateWithTranscript(sourceState, sessionID, path)
		if stateErr != nil {
			return stateErr
		}
		if logErr := log(ctx, transcriptState, sessionID, ""); logErr != nil {
			return fmt.Errorf("failed to sync %s session %s: %w", label, sessionID, logErr)
		}
		count++
		return nil
	})
	if walkErr != nil {
		return 0, fmt.Errorf("failed to scan %s sessions: %w", label, walkErr)
	}
	return count, nil
}

// RunAgentSessionSync scans all agent storage and triggers logging for unprocessed sessions.
func RunAgentSessionSync(ctx context.Context, state *GlobalState) error {
	// Batch ingestion has no hook payload and must not consume the caller's stdin.
	noStdinState := *state
	noStdinState.Stdin = nil
	total := 0
	for _, definition := range agentDefinitions() {
		root, present, err := definition.sourcePath(state.Config.Agent)
		if err != nil {
			return err
		}
		if !present {
			continue
		}
		count, err := definition.SyncSessions(ctx, &noStdinState, root)
		if err != nil {
			return err
		}
		verb := "checked"
		if definition.Database {
			verb = "ingested"
		}
		reportSyncOutcome(state, definition.Agent, syncOutcome{verb: verb, count: count})
		total += count
	}
	_, _ = fmt.Fprintf(state.Stderr, "agent-session-sync: done (%d total processed)\n", total)
	return nil
}
