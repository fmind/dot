package dot

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

// decodeSessionIDs parses a sqlite3 -json `SELECT id ...` result. Idempotence is
// decided later from the agent-scoped fingerprint, never from a bare session ID.
func decodeSessionIDs(label, output string) ([]string, error) {
	output = strings.TrimSpace(output)
	if output == "" || output == "[]" {
		return nil, nil
	}

	var rows []struct {
		ID string `json:"id"`
	}
	if err := json.Unmarshal([]byte(output), &rows); err != nil {
		return nil, fmt.Errorf("failed to decode %s session query result: %w", label, err)
	}
	if rows == nil {
		return nil, fmt.Errorf("failed to decode %s session query result: expected a JSON array", label)
	}

	sessionIDs := make([]string, 0, len(rows))
	seen := make(map[string]bool)
	for rowNumber, row := range rows {
		sessionID := row.ID
		if !isValidSessionID(sessionID) {
			return nil, fmt.Errorf("malformed %s session row %d: invalid session ID %q", label, rowNumber+1, sessionID)
		}
		if seen[sessionID] {
			return nil, fmt.Errorf("malformed %s session rows: duplicate session ID %q", label, sessionID)
		}
		seen[sessionID] = true
		sessionIDs = append(sessionIDs, sessionID)
	}
	return sessionIDs, nil
}

// sqliteSweep describes how one SQLite-backed agent store is swept end to end.
// OpenCode and Copilot differ only in their queries, row shape, and per-row
// validation, so the sweep itself is written once and parameterized here.
type sqliteSweep[R any] struct {
	// sessionOf reads the owning session ID from a row.
	sessionOf func(R) string
	// validate rejects a malformed row; rowNumber is 1-based for the message.
	validate func(row R, rowNumber int) error
	// parse turns one session's rows into normalized log lines.
	parse func(sessionID string, rows []R) ([]SessionLogLine, error)
	// agent is the canonical agent name; sourceType labels the ingested generation.
	agent      string
	sourceType string
	// label names the store in error messages; rowNoun and rowNounPlural name its
	// detail rows, singular for one bad row and plural for a failed batch query.
	label         string
	rowNoun       string
	rowNounPlural string
	// sessionsQuery enumerates the session IDs; rowsQuery takes one %s filter clause.
	sessionsQuery string
	rowsQuery     string
	// filterColumn is the qualified column the batched IN filter targets.
	filterColumn string
}

// syncSQLiteSessions enumerates every session in a SQLite-backed store, fetches all
// detail rows in one batched query, groups them per session, and ingests each
// lineage. Sessions whose rows produce no records are still recorded, so an empty
// session is proven empty rather than left looking unprocessed. It returns the
// number of sessions newly ingested.
func syncSQLiteSessions[R any](ctx context.Context, state *GlobalState, dbPath string, sweep sqliteSweep[R]) (int, error) {
	output, err := runSQLiteJSON(ctx, state, dbPath, sweep.sessionsQuery)
	if err != nil {
		return 0, fmt.Errorf("failed to query %s sessions: %w", sweep.label, err)
	}
	sessionIDs, err := decodeSessionIDs(sweep.label, output)
	if err != nil {
		return 0, err
	}
	if len(sessionIDs) == 0 {
		return 0, nil
	}

	quoted := make([]string, len(sessionIDs))
	requested := make(map[string]bool, len(sessionIDs))
	for index, sessionID := range sessionIDs {
		// Session IDs were validated above, so the exact value is safe to use as a
		// SQLite string literal without silently changing its identity.
		quoted[index] = "'" + sessionID + "'"
		requested[sessionID] = true
	}

	recordEmpty := func(sessionID string) error {
		_, writeErr := writeSessionLogs(ctx, state, sweep.agent, sessionID, nil, sessionSource{Type: sweep.sourceType})
		return writeErr
	}

	filter := sweep.filterColumn + " IN (" + strings.Join(quoted, ",") + ")"
	rowOutput, err := runSQLiteJSON(ctx, state, dbPath, fmt.Sprintf(sweep.rowsQuery, filter))
	if err != nil {
		return 0, fmt.Errorf("failed to query %s %s: %w", sweep.label, sweep.rowNounPlural, err)
	}
	rowOutput = strings.TrimSpace(rowOutput)
	if rowOutput == "" || rowOutput == "[]" {
		for _, sessionID := range sessionIDs {
			if writeErr := recordEmpty(sessionID); writeErr != nil {
				return 0, writeErr
			}
		}
		return 0, nil
	}

	var rows []R
	if err := json.Unmarshal([]byte(rowOutput), &rows); err != nil {
		return 0, fmt.Errorf("failed to decode %s %s query result: %w", sweep.label, sweep.rowNoun, err)
	}
	if rows == nil {
		return 0, fmt.Errorf("failed to decode %s %s query result: expected a JSON array", sweep.label, sweep.rowNoun)
	}

	sessionRows := make(map[string][]R, len(sessionIDs))
	for index, row := range rows {
		rowNumber := index + 1
		sessionID := sweep.sessionOf(row)
		if !isValidSessionID(sessionID) {
			return 0, fmt.Errorf("malformed %s %s row %d: invalid session ID %q", sweep.label, sweep.rowNoun, rowNumber, sessionID)
		}
		if !requested[sessionID] {
			return 0, fmt.Errorf("malformed %s %s row %d: unexpected session ID %q", sweep.label, sweep.rowNoun, rowNumber, sessionID)
		}
		if sweep.validate != nil {
			if err := sweep.validate(row, rowNumber); err != nil {
				return 0, err
			}
		}
		sessionRows[sessionID] = append(sessionRows[sessionID], row)
	}

	count := 0
	for _, sessionID := range sessionIDs {
		rows := sessionRows[sessionID]
		logs, parseErr := sweep.parse(sessionID, rows)
		if parseErr != nil {
			return 0, fmt.Errorf("failed to parse %s session %q: %w", sweep.label, sessionID, parseErr)
		}
		if len(logs) == 0 {
			if writeErr := recordEmpty(sessionID); writeErr != nil {
				return 0, writeErr
			}
			continue
		}
		fingerprint, fingerprintErr := fingerprintJSON(rows)
		if fingerprintErr != nil {
			return 0, fingerprintErr
		}
		result, writeErr := writeSessionLogs(ctx, state, sweep.agent, sessionID, logs, sessionSource{Type: sweep.sourceType, Fingerprint: fingerprint})
		if writeErr != nil {
			return 0, fmt.Errorf("failed to write %s session %q: %w", sweep.label, sessionID, writeErr)
		}
		if result.Status == sessionIngested {
			count++
		}
	}
	return count, nil
}

// runSQLiteJSON runs one read-only query against an agent's SQLite store. `-init
// /dev/null` keeps a user's ~/.sqliterc from injecting output settings that would
// corrupt the JSON this parser depends on. Read-only mode also prevents a missing
// or concurrently removed source from being replaced with an empty database.
func runSQLiteJSON(ctx context.Context, state *GlobalState, dbPath, query string) (string, error) {
	return state.Runner.Run(ctx, "", nil, "sqlite3", "-readonly", "-init", os.DevNull, "-json", dbPath, query)
}
