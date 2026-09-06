package dot

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"path/filepath"
	"strings"
)

// usageSyncCandidate is one session a backfill sweep found in a raw harness store.
type usageSyncCandidate struct {
	SessionID string
	CWD       string
	// Path is the transcript to read. It stays empty for stores whose extractor
	// resolves its own source (databases, and Grok's signals.json).
	Path string
}

// usageSyncSource backfills one harness: enumerate the raw store, then turn every
// candidate it yields into a usage record. Splitting the two halves keeps the six
// stores from repeating the extract-write-count block they used to copy verbatim.
type usageSyncSource struct {
	enumerate func(ctx context.Context, state *GlobalState, root string) ([]usageSyncCandidate, error)
	extract   func(ctx context.Context, state *GlobalState, candidate usageSyncCandidate) (*UsageRecord, error)
}

// syncUsage backfills one store and returns how many records it wrote. A missing store
// is not an error -- that harness simply is not installed -- but an unreadable one
// is: reporting "Synced 0 usage records" over a permission error is how a broken
// backfill used to look exactly like an empty one.
func (definition agentDefinition) syncUsage(ctx context.Context, state *GlobalState) (int, error) {
	root, present, err := definition.sourcePath(state.Config.Agent)
	if err != nil || !present {
		return 0, err
	}

	candidates, err := definition.Usage.enumerate(ctx, state, root)
	if err != nil {
		return 0, fmt.Errorf("failed to scan %s usage sources: %w", definition.Agent, err)
	}
	written := 0
	for _, candidate := range candidates {
		record, extractErr := definition.Usage.extract(ctx, state, candidate)
		if extractErr != nil {
			return written, fmt.Errorf("failed to extract %s usage for session %s: %w", definition.Agent, candidate.SessionID, extractErr)
		}
		if record == nil {
			continue
		}
		if writeErr := WriteUsageRecord(*record); writeErr != nil {
			return written, fmt.Errorf("failed to write %s usage for session %s: %w", definition.Agent, candidate.SessionID, writeErr)
		}
		written++
	}
	return written, nil
}

// transcriptCandidates walks a directory store and yields one candidate per JSONL
// transcript whose name maps to a session id.
func transcriptCandidates(root string, sessionIDOf func(name string) string) ([]usageSyncCandidate, error) {
	var candidates []usageSyncCandidate
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".jsonl") {
			return nil
		}
		sessionID := sessionIDOf(entry.Name())
		if sessionID == "" {
			return nil
		}
		candidates = append(candidates, usageSyncCandidate{SessionID: sessionID, Path: path})
		return nil
	})
	return candidates, err
}

// sqliteCandidates reads session identities out of a SQLite-backed store.
func sqliteCandidates(ctx context.Context, state *GlobalState, dbPath, query string) ([]usageSyncCandidate, error) {
	out, err := runSQLiteJSON(ctx, state, dbPath, query)
	if err != nil {
		return nil, err
	}
	trimmed := strings.TrimSpace(out)
	if trimmed == "" || trimmed == "[]" {
		return nil, nil
	}
	var rows []struct {
		ID  string `json:"id"`
		CWD string `json:"cwd"`
	}
	if err := json.Unmarshal([]byte(trimmed), &rows); err != nil {
		return nil, fmt.Errorf("failed to parse session query result: %w", err)
	}
	candidates := make([]usageSyncCandidate, 0, len(rows))
	for _, row := range rows {
		candidates = append(candidates, usageSyncCandidate{SessionID: row.ID, CWD: row.CWD})
	}
	return candidates, nil
}

// RunAgentUsageSync scans existing raw session stores and backfills/refreshes usage records.
func RunAgentUsageSync(ctx context.Context, state *GlobalState) error {
	syncedCount := 0
	harnessesSynced := 0
	for _, definition := range agentDefinitions() {
		written, err := definition.syncUsage(ctx, state)
		if err != nil {
			return err
		}
		if written > 0 {
			reportSyncOutcome(state, definition.Agent, syncOutcome{verb: "recorded", count: written})
			harnessesSynced++
			syncedCount += written
		}
	}

	_, _ = fmt.Fprintf(state.Stdout, "Synced %d usage records across %d harnesses into ~/.agents/usages\n", syncedCount, harnessesSynced)
	return nil
}
