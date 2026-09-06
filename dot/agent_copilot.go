package dot

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"
)

// CopilotRow is a joined session/turn row returned by sqlite3 -json from Copilot's session-store.db.
type CopilotRow struct {
	SessionID         string `json:"session_id"`
	UserMessage       string `json:"user_message"`
	AssistantResponse string `json:"assistant_response"`
	Timestamp         string `json:"timestamp"`
	CWD               string `json:"cwd"`
	TurnIndex         int    `json:"turn_index"`
}

// parseCopilotRows expands Copilot's per-turn user/assistant columns into session log lines.
// Copilot stores each turn as one row carrying both the prompt and the response, so a single
// row can yield up to two lines. NULL columns decode to empty strings and are skipped.
func parseCopilotRows(sessionID, fallbackCWD string, rows []CopilotRow) []SessionLogLine {
	logs := make([]SessionLogLine, 0, len(rows)*2)
	for _, row := range rows {
		logCWD := row.CWD
		if logCWD == "" {
			logCWD = fallbackCWD
		}
		logCWD = resolveCWD(logCWD)

		if strings.TrimSpace(row.UserMessage) != "" {
			logs = append(logs, SessionLogLine{
				TS:      row.Timestamp,
				Agent:   "copilot",
				SID:     sessionID,
				Role:    "user",
				Content: row.UserMessage,
				CWD:     logCWD,
			})
		}
		if strings.TrimSpace(row.AssistantResponse) != "" {
			logs = append(logs, SessionLogLine{
				TS:      row.Timestamp,
				Agent:   "copilot",
				SID:     sessionID,
				Role:    "assistant",
				Content: row.AssistantResponse,
				CWD:     logCWD,
			})
		}
	}
	return logs
}

// RunAgentSessionLogCopilot reads a single Copilot session from its store and logs it.
// The Copilot sessionEnd hook supplies only identity/lifecycle metadata, so the
// transcript remains sourced from this store-backed query.
func RunAgentSessionLogCopilot(ctx context.Context, state *GlobalState, sessionID, cwd string) error {
	// Copilot's sessionEnd hook carries no transcript payload, so identity comes from
	// the operands alone and stdin is never consumed here.
	if sessionID == "" {
		return errors.New("missing session_id")
	}
	if !isValidSessionID(sessionID) {
		return fmt.Errorf("invalid session_id format: %q", sessionID)
	}
	cwd = resolveCWD(cwd)

	dbPath, err := state.Config.Agent.SourceRoot(sessionStoreCopilot)
	if err != nil {
		return err
	}
	if _, statErr := os.Stat(dbPath); os.IsNotExist(statErr) {
		return fmt.Errorf("copilot database not found at %s", dbPath)
	}

	sqlQuery := fmt.Sprintf(copilotTurnsQuery, "t.session_id = '"+sessionID+"'")
	out, err := runSQLiteJSON(ctx, state, dbPath, sqlQuery)
	if err != nil {
		return err
	}

	out = strings.TrimSpace(out)
	if out == "" || out == "[]" {
		_, err = writeSessionLogs(ctx, state, "copilot", sessionID, nil, sessionSource{Type: "copilot-db"})
		return err
	}

	var rows []CopilotRow
	if parseErr := json.Unmarshal([]byte(out), &rows); parseErr != nil {
		return fmt.Errorf("failed to parse Copilot query result: %w", parseErr)
	}

	fingerprint, err := fingerprintJSON(rows)
	if err != nil {
		return err
	}
	_, err = writeSessionLogs(ctx, state, "copilot", sessionID, parseCopilotRows(sessionID, cwd, rows), sessionSource{Type: "copilot-db", Fingerprint: fingerprint})
	if err == nil {
		recordUsageBestEffort(state, "copilot", func() (*UsageRecord, error) {
			return ExtractUsageCopilot(ctx, state, sessionID, cwd)
		})
	}
	return err
}

// syncCopilotSessions scans the Copilot store and logs every untracked session.
func syncCopilotSessions(ctx context.Context, state *GlobalState, dbPath string) (int, error) {
	return syncSQLiteSessions(ctx, state, dbPath, sqliteSweep[CopilotRow]{
		agent:         sessionStoreCopilot,
		sourceType:    "copilot-db",
		label:         "Copilot",
		rowNoun:       "turn",
		rowNounPlural: "turns",
		sessionsQuery: copilotSessionsQuery,
		rowsQuery:     copilotTurnsQuery,
		filterColumn:  "t.session_id",
		sessionOf:     func(row CopilotRow) string { return row.SessionID },
		parse: func(sessionID string, rows []CopilotRow) ([]SessionLogLine, error) {
			return parseCopilotRows(sessionID, "", rows), nil
		},
	})
}

// ExtractUsageCopilot extracts token usage from GitHub Copilot CLI's assistant_usage_events.
func ExtractUsageCopilot(ctx context.Context, state *GlobalState, sessionID, cwd string) (*UsageRecord, error) {
	// The session id is interpolated into the SQL below, and the SessionEnd hook
	// takes it straight from the host's JSON payload. Reject anything outside the
	// id alphabet here, at the boundary every caller shares.
	if !isValidSessionID(sessionID) {
		return nil, fmt.Errorf("invalid copilot session id %q", sessionID)
	}
	dbPath, err := state.Config.Agent.SourceRoot(sessionStoreCopilot)
	if err != nil {
		return nil, err
	}
	if _, statErr := os.Stat(dbPath); os.IsNotExist(statErr) {
		return nil, fmt.Errorf("copilot database not found at %s", dbPath)
	}

	query := fmt.Sprintf("SELECT model, COALESCE(SUM(input_tokens), 0) AS input_tokens, COALESCE(SUM(output_tokens), 0) AS output_tokens, COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens, COALESCE(SUM(cache_write_tokens), 0) AS cache_write_tokens, COALESCE(SUM(reasoning_tokens), 0) AS reasoning_tokens, COUNT(*) AS turns FROM assistant_usage_events WHERE session_id = '%s' GROUP BY model;", sessionID)
	out, err := runSQLiteJSON(ctx, state, dbPath, query)
	if err != nil {
		return nil, err
	}
	var rows []struct {
		Model            string `json:"model"`
		InputTokens      int64  `json:"input_tokens"`
		OutputTokens     int64  `json:"output_tokens"`
		CacheReadTokens  int64  `json:"cache_read_tokens"`
		CacheWriteTokens int64  `json:"cache_write_tokens"`
		ReasoningTokens  int64  `json:"reasoning_tokens"`
		Turns            int    `json:"turns"`
	}
	_ = json.Unmarshal([]byte(strings.TrimSpace(out)), &rows)

	sessionQuery := fmt.Sprintf("SELECT cwd, created_at FROM sessions WHERE id = '%s';", sessionID)
	sessionOut, _ := runSQLiteJSON(ctx, state, dbPath, sessionQuery)
	var sessionRows []struct {
		CWD       string `json:"cwd"`
		CreatedAt string `json:"created_at"`
	}
	_ = json.Unmarshal([]byte(strings.TrimSpace(sessionOut)), &sessionRows)

	sessionCWD := cwd
	ts := time.Now().UTC().Format(time.RFC3339)
	if len(sessionRows) > 0 {
		if sessionCWD == "" {
			sessionCWD = sessionRows[0].CWD
		}
		if sessionRows[0].CreatedAt != "" {
			ts = sessionRows[0].CreatedAt
		}
	}

	rec := &UsageRecord{
		Timestamp: ts,
		Harness:   sessionStoreCopilot,
		Agent:     sessionStoreCopilot,
		SessionID: sessionID,
		CWD:       resolveCWD(sessionCWD),
	}
	for _, row := range rows {
		if rec.Model == "" && row.Model != "" {
			rec.Model = row.Model
		}
		rec.InputTokens += row.InputTokens
		rec.OutputTokens += row.OutputTokens
		rec.CachedTokens += row.CacheReadTokens
		rec.CacheWriteTokens += row.CacheWriteTokens
		rec.ReasoningTokens += row.ReasoningTokens
		rec.TurnCount += row.Turns
	}
	rec.TotalTokens = rec.InputTokens + rec.OutputTokens + rec.CachedTokens + rec.CacheWriteTokens
	return rec, nil
}

func handleCopilotUsageHook(ctx context.Context, state *GlobalState, sessionID, cwd string) error {
	defer func() {
		_, _ = fmt.Fprintln(state.Stdout, "{}")
	}()
	if sessionID == "" && state.Stdin != nil {
		input, err := decodeCopilotSessionEnd(state.Stdin)
		if err == nil {
			sessionID = input.SessionID
			cwd = input.CWD
		}
	}
	if sessionID == "" {
		return errors.New("missing copilot session id")
	}
	rec, err := ExtractUsageCopilot(ctx, state, sessionID, cwd)
	if err != nil {
		return err
	}
	return WriteUsageRecord(*rec)
}
