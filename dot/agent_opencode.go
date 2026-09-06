package dot

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"
)

// OpencodeData represents the nested structure inside message.data for OpenCode.
type OpencodeData struct {
	Role  string `json:"role"`
	Model struct {
		ProviderID string `json:"providerID"`
		ModelID    string `json:"modelID"`
	} `json:"model"`
}

// OpencodePart represents the content stored in OpenCode's part table.
type OpencodePart struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// OpencodeRow represents the joined message and part rows returned by sqlite3 -json.
type OpencodeRow struct {
	SessionID   string `json:"session_id"`
	MessageID   string `json:"message_id"`
	PartID      string `json:"part_id"`
	Data        string `json:"data"`
	PartData    string `json:"part_data"`
	Directory   string `json:"directory"`
	TimeCreated int64  `json:"time_created"`
}

// parseOpencodeRows converts OpenCode's normalized message/part rows into session logs.
func parseOpencodeRows(sessionID, fallbackCWD string, rows []OpencodeRow) ([]SessionLogLine, error) {
	type message struct {
		data        OpencodeData
		id          string
		directory   string
		textParts   []string
		timeCreated int64
	}

	logs := make([]SessionLogLine, 0, len(rows))
	var current message
	flush := func() {
		content := strings.Join(current.textParts, "\n")
		if (current.data.Role != "user" && current.data.Role != "assistant") || strings.TrimSpace(content) == "" {
			return
		}

		logCWD := current.directory
		if logCWD == "" {
			logCWD = fallbackCWD
		}
		logCWD = resolveCWD(logCWD)

		model := current.data.Model.ModelID
		if current.data.Model.ProviderID != "" && model != "" {
			model = current.data.Model.ProviderID + "/" + model
		}

		logs = append(logs, SessionLogLine{
			TS:      time.UnixMilli(current.timeCreated).UTC().Format(time.RFC3339),
			Agent:   "opencode",
			SID:     sessionID,
			Role:    current.data.Role,
			Content: content,
			CWD:     logCWD,
			Model:   model,
		})
	}

	for _, row := range rows {
		if row.MessageID != current.id {
			if current.id != "" {
				flush()
			}
			current = message{
				id:          row.MessageID,
				directory:   row.Directory,
				timeCreated: row.TimeCreated,
			}
			if err := json.Unmarshal([]byte(row.Data), &current.data); err != nil {
				return nil, fmt.Errorf("failed to parse OpenCode message %s: %w", row.MessageID, err)
			}
		}

		if row.PartData == "" {
			continue
		}
		var part OpencodePart
		if err := json.Unmarshal([]byte(row.PartData), &part); err != nil {
			return nil, fmt.Errorf("failed to parse OpenCode part %s: %w", row.PartID, err)
		}
		if part.Type == "text" && part.Text != "" {
			current.textParts = append(current.textParts, part.Text)
		}
	}
	if current.id != "" {
		flush()
	}

	return logs, nil
}

func syncOpencodeSessions(ctx context.Context, state *GlobalState, dbPath string) (int, error) {
	return syncSQLiteSessions(ctx, state, dbPath, sqliteSweep[OpencodeRow]{
		agent:         sessionStoreOpenCode,
		sourceType:    "opencode-db",
		label:         "OpenCode",
		rowNoun:       "message",
		rowNounPlural: "messages",
		sessionsQuery: opencodeSessionsQuery,
		rowsQuery:     opencodeMessagesQuery,
		filterColumn:  "m.session_id",
		sessionOf:     func(row OpencodeRow) string { return row.SessionID },
		validate: func(row OpencodeRow, rowNumber int) error {
			if row.MessageID == "" {
				return fmt.Errorf("malformed OpenCode message row %d: missing message ID", rowNumber)
			}
			if row.PartData != "" && row.PartID == "" {
				return fmt.Errorf("malformed OpenCode message row %d: missing part ID", rowNumber)
			}
			return nil
		},
		parse: func(sessionID string, rows []OpencodeRow) ([]SessionLogLine, error) {
			return parseOpencodeRows(sessionID, "", rows)
		},
	})
}

// RunAgentSessionLogOpencode reads OpenCode session records and writes them to the sessions directory.
func RunAgentSessionLogOpencode(ctx context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, false)
	if err != nil {
		return err
	}
	if halt {
		return nil
	}
	sessionID, cwd = identity.Session, identity.CWD

	dbPath, err := state.Config.Agent.SourceRoot(sessionStoreOpenCode)
	if err != nil {
		return err
	}
	if _, statErr := os.Stat(dbPath); os.IsNotExist(statErr) {
		return fmt.Errorf("opencode database not found at %s", dbPath)
	}

	sqlQuery := fmt.Sprintf(opencodeMessagesQuery, "m.session_id = '"+sessionID+"'")
	out, err := runSQLiteJSON(ctx, state, dbPath, sqlQuery)
	if err != nil {
		return err
	}

	out = strings.TrimSpace(out)
	if out == "" || out == "[]" {
		_, err = writeSessionLogs(ctx, state, "opencode", sessionID, nil, sessionSource{Type: "opencode-db"})
		return err
	}

	var rows []OpencodeRow
	if parseErr := json.Unmarshal([]byte(out), &rows); parseErr != nil {
		return fmt.Errorf("failed to parse OpenCode query result: %w", parseErr)
	}

	logs, err := parseOpencodeRows(sessionID, cwd, rows)
	if err != nil {
		return err
	}
	fingerprint, err := fingerprintJSON(rows)
	if err != nil {
		return err
	}
	_, err = writeSessionLogs(ctx, state, "opencode", sessionID, logs, sessionSource{Type: "opencode-db", Fingerprint: fingerprint})
	if err == nil {
		recordUsageBestEffort(state, "opencode", func() (*UsageRecord, error) {
			return ExtractUsageOpencode(ctx, state, sessionID, cwd)
		})
	}
	return err
}

// ExtractUsageOpencode extracts token usage from OpenCode's SQLite database.
func ExtractUsageOpencode(ctx context.Context, state *GlobalState, sessionID, cwd string) (*UsageRecord, error) {
	dbPath, err := state.Config.Agent.SourceRoot(sessionStoreOpenCode)
	if err != nil {
		return nil, err
	}
	if _, statErr := os.Stat(dbPath); os.IsNotExist(statErr) {
		return nil, fmt.Errorf("opencode database not found at %s", dbPath)
	}
	query := fmt.Sprintf("SELECT model, tokens_input, tokens_output, tokens_reasoning, tokens_cache_read, tokens_cache_write, cost, directory, time_created FROM session WHERE id = '%s';", sessionID)
	out, err := runSQLiteJSON(ctx, state, dbPath, query)
	if err != nil {
		return nil, err
	}
	out = strings.TrimSpace(out)
	if out == "" || out == "[]" {
		return nil, fmt.Errorf("session %s not found in opencode database", sessionID)
	}
	var rows []struct {
		Model            any     `json:"model"`
		Directory        string  `json:"directory"`
		TokensInput      int64   `json:"tokens_input"`
		TokensOutput     int64   `json:"tokens_output"`
		TokensReasoning  int64   `json:"tokens_reasoning"`
		TokensCacheRead  int64   `json:"tokens_cache_read"`
		TokensCacheWrite int64   `json:"tokens_cache_write"`
		Cost             float64 `json:"cost"`
		TimeCreated      int64   `json:"time_created"`
	}
	if err := json.Unmarshal([]byte(out), &rows); err != nil {
		return nil, fmt.Errorf("failed to parse opencode session row: %w", err)
	}
	if len(rows) == 0 {
		return nil, fmt.Errorf("session %s not found in opencode database", sessionID)
	}
	row := rows[0]
	modelStr := ""
	switch m := row.Model.(type) {
	case string:
		var modelObj struct {
			ID         string `json:"id"`
			ModelID    string `json:"modelID"`
			ProviderID string `json:"providerID"`
		}
		if json.Unmarshal([]byte(m), &modelObj) == nil && (modelObj.ID != "" || modelObj.ModelID != "") {
			if modelObj.ProviderID != "" && modelObj.ModelID != "" {
				modelStr = modelObj.ProviderID + "/" + modelObj.ModelID
			} else if modelObj.ID != "" {
				modelStr = modelObj.ID
			}
		} else {
			modelStr = m
		}
	case map[string]any:
		prov, _ := m["providerID"].(string)
		mod, _ := m["modelID"].(string)
		id, _ := m["id"].(string)
		if prov != "" && mod != "" {
			modelStr = prov + "/" + mod
		} else if id != "" {
			modelStr = id
		}
	}
	sessionCWD := cwd
	if sessionCWD == "" {
		sessionCWD = row.Directory
	}
	ts := time.Now().UTC().Format(time.RFC3339)
	if row.TimeCreated > 0 {
		ts = time.UnixMilli(row.TimeCreated).UTC().Format(time.RFC3339)
	}
	total := row.TokensInput + row.TokensOutput + row.TokensCacheRead + row.TokensCacheWrite
	return &UsageRecord{
		Timestamp:        ts,
		Harness:          sessionStoreOpenCode,
		Agent:            sessionStoreOpenCode,
		SessionID:        sessionID,
		Model:            modelStr,
		InputTokens:      row.TokensInput,
		OutputTokens:     row.TokensOutput,
		CachedTokens:     row.TokensCacheRead,
		CacheWriteTokens: row.TokensCacheWrite,
		ReasoningTokens:  row.TokensReasoning,
		TotalTokens:      total,
		CostUSD:          row.Cost,
		CWD:              resolveCWD(sessionCWD),
	}, nil
}

func handleOpenCodeUsageHook(ctx context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, false)
	if err != nil {
		return err
	}
	if halt {
		return nil
	}
	sessionID, cwd = identity.Session, identity.CWD
	rec, err := ExtractUsageOpencode(ctx, state, sessionID, cwd)
	if err != nil {
		return err
	}
	return WriteUsageRecord(*rec)
}
