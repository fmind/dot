package dot

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

// claudeProjectDirectory encodes a working directory the way Claude Code names its
// per-project transcript folder: path separators and dots become dashes.
func claudeProjectDirectory(cwd string) string {
	encoded := strings.ReplaceAll(cwd, "/", "-")
	encoded = strings.ReplaceAll(encoded, ".", "-")
	return "-" + strings.TrimPrefix(encoded, "-")
}

// claudeTranscriptPath is shared by ingestion and usage extraction so both read
// the exact same source and report lookup failures consistently.
func claudeTranscriptPath(cfg AgentConfig, sessionID, cwd, transcriptPath string) (string, error) {
	if transcriptPath != "" {
		return transcriptPath, nil
	}
	projectsDir, rootErr := cfg.SourceRoot(sessionStoreClaude)
	if rootErr != nil {
		return "", rootErr
	}
	// The CWD-derived path is exact when it exists, so the directory scan below is
	// only a fallback for a session logged from a different working directory.
	transcriptPath = filepath.Join(projectsDir, claudeProjectDirectory(cwd), sessionID+".jsonl")
	_, statErr := os.Stat(transcriptPath)
	if statErr != nil && !errors.Is(statErr, os.ErrNotExist) {
		return "", fmt.Errorf("failed to inspect expected Claude transcript %s: %w", transcriptPath, statErr)
	}
	if statErr != nil {
		found, findErr := findSessionFile(projectsDir, func(_ string, entry fs.DirEntry) bool {
			return entry.Name() == sessionID+".jsonl"
		})
		if findErr != nil {
			return "", fmt.Errorf("failed to search Claude transcripts in %s: %w", projectsDir, findErr)
		}
		if found == "" {
			return "", fmt.Errorf("session file not found for claude session %s", sessionID)
		}
		transcriptPath = found
	}
	return transcriptPath, nil
}

// RunAgentSessionLogClaude reads the Claude JSONL files and processes the session.
func RunAgentSessionLogClaude(ctx context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, false)
	if err != nil {
		return err
	}
	if halt {
		return nil
	}
	sessionID, cwd = identity.Session, identity.CWD

	sessionFile, err := hookTranscriptPath(identity, "claude")
	if err != nil {
		return err
	}
	sessionFile, err = claudeTranscriptPath(state.Config.Agent, sessionID, cwd, sessionFile)
	if err != nil {
		return err
	}

	fingerprint, stored, isStored, err := fingerprintStoredTranscript("claude", sessionID, sessionFile)
	if err != nil {
		return err
	}
	if isStored {
		reportStoredGeneration(state.Stderr, stored)
		return nil
	}

	file, err := os.Open(sessionFile)
	if err != nil {
		return err
	}
	defer func() { _ = file.Close() }()

	usage := &UsageRecord{Harness: sessionStoreClaude, Agent: sessionStoreClaude, SessionID: sessionID, CWD: cwd}
	var logs []SessionLogLine
	decodeStats, decodeErr := decodeJSONLWithStats(state.Stderr, sessionFile, file, func(raw map[string]any) error {
		updateClaudeUsage(usage, raw)
		typ, _ := raw["type"].(string)
		if typ != "user" && typ != "assistant" {
			return nil
		}

		ts, _ := raw["timestamp"].(string)
		msgVal, ok := raw["message"].(map[string]any)
		if !ok {
			return nil
		}

		var content string
		switch typ {
		case "user":
			content, _ = msgVal["content"].(string)
		case "assistant":
			if contentsList, ok := msgVal["content"].([]any); ok {
				var textParts []string
				for _, part := range contentsList {
					if partMap, ok := part.(map[string]any); ok {
						if ptype, _ := partMap["type"].(string); ptype == "text" {
							if text, _ := partMap["text"].(string); text != "" {
								textParts = append(textParts, text)
							}
						}
					}
				}
				content = strings.Join(textParts, "\n")
			}
		}

		logCWD, _ := raw["cwd"].(string)
		if logCWD == "" {
			logCWD = cwd
		}
		logCWD = resolveCWD(logCWD)

		var model string
		if m, ok := msgVal["model"].(string); ok {
			model = m
		}

		if strings.TrimSpace(content) == "" {
			return nil
		}

		logs = append(logs, SessionLogLine{
			TS:      ts,
			Agent:   "claude",
			SID:     sessionID,
			Role:    typ,
			Content: content,
			CWD:     logCWD,
			Model:   model,
		})
		return nil
	})
	if decodeErr != nil {
		return decodeErr
	}

	_, err = writeSessionLogs(ctx, state, "claude", sessionID, logs, sessionSource{Type: "claude-jsonl", Fingerprint: fingerprint, Malformed: decodeStats.Malformed, Skipped: decodeStats.Decoded - len(logs)})
	if err == nil {
		recordUsageBestEffort(state, "claude", func() (*UsageRecord, error) {
			return finalizeTranscriptUsage(usage), nil
		})
	}
	return err
}

// ExtractUsageClaude extracts precise token usage from Claude Code's project transcript.
func ExtractUsageClaude(cfg AgentConfig, sessionID, cwd, transcriptPath string) (*UsageRecord, error) {
	transcriptPath, err := claudeTranscriptPath(cfg, sessionID, cwd, transcriptPath)
	if err != nil {
		return nil, err
	}

	return readTranscriptUsage(transcriptPath, &UsageRecord{
		Harness:   sessionStoreClaude,
		Agent:     sessionStoreClaude,
		SessionID: sessionID,
		CWD:       cwd,
	}, updateClaudeUsage)
}

// Session ingestion feeds these same observers while decoding conversation
// records, avoiding a second full parse solely to refresh token usage.
func updateClaudeUsage(rec *UsageRecord, raw map[string]any) {
	if ts, ok := raw["timestamp"].(string); ok && ts != "" {
		rec.Timestamp = ts
	}
	if lineCWD, ok := raw["cwd"].(string); ok && lineCWD != "" && rec.CWD == "" {
		rec.CWD = resolveCWD(lineCWD)
	}
	typ, _ := raw["type"].(string)
	if typ == "cost-state" {
		if cost, ok := raw["totalCostUSD"].(float64); ok && cost > 0 {
			rec.CostUSD = cost
		}
	}
	if typ == "assistant" {
		rec.TurnCount++
		if msg, ok := raw["message"].(map[string]any); ok {
			if model, ok := msg["model"].(string); ok && model != "" {
				rec.Model = model
			}
			if usage, ok := msg["usage"].(map[string]any); ok {
				if in, ok := usage["input_tokens"].(float64); ok {
					rec.InputTokens += int64(in)
				}
				if out, ok := usage["output_tokens"].(float64); ok {
					rec.OutputTokens += int64(out)
				}
				if cr, ok := usage["cache_read_input_tokens"].(float64); ok {
					rec.CachedTokens += int64(cr)
				}
				if cw, ok := usage["cache_creation_input_tokens"].(float64); ok {
					rec.CacheWriteTokens += int64(cw)
				}
			}
		}
	}
}

func handleClaudeUsageHook(_ context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, false)
	if err != nil {
		return err
	}
	if halt {
		return nil
	}
	sessionID, cwd = identity.Session, identity.CWD
	transcriptPath, err := hookTranscriptPath(identity, "claude")
	if err != nil {
		return err
	}
	rec, err := ExtractUsageClaude(state.Config.Agent, sessionID, cwd, transcriptPath)
	if err != nil {
		return err
	}
	return WriteUsageRecord(*rec)
}

func syncClaudeSessions(ctx context.Context, state *GlobalState, root string) (int, error) {
	return syncTranscriptSessions(ctx, state, root, "Claude", claudeSessionID, RunAgentSessionLogClaude)
}

func claudeSessionID(path string) string {
	name := filepath.Base(path)
	// memory.jsonl is hand-curated long-term memory, not a session transcript.
	if name == "memory.jsonl" {
		return ""
	}
	return strings.TrimSuffix(name, ".jsonl")
}
