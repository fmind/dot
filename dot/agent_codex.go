package dot

import (
	"context"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

// extractCodexSessionID extracts the session ID from rollout filename (without .jsonl).
func extractCodexSessionID(name string) string {
	if !strings.HasPrefix(name, "rollout-") {
		return ""
	}
	parts := strings.Split(name, "-")
	if len(parts) >= 7 {
		return strings.Join(parts[6:], "-")
	}
	return ""
}

func textFromCodexContent(value any) string {
	switch content := value.(type) {
	case string:
		return content
	case []any:
		textParts := make([]string, 0, len(content))
		for _, part := range content {
			switch partValue := part.(type) {
			case string:
				textParts = append(textParts, partValue)
			case map[string]any:
				if text := stringValue(partValue["text"]); text != "" {
					textParts = append(textParts, text)
				} else if text := stringValue(partValue["content"]); text != "" {
					textParts = append(textParts, text)
				}
			}
		}
		return strings.Join(textParts, "\n")
	default:
		return ""
	}
}

func codexRole(raw map[string]any) string {
	if role := stringValue(raw["role"]); role != "" {
		return role
	}

	payload := mapValue(raw["payload"])
	if payload != nil {
		if role := stringValue(payload["role"]); role != "" {
			return role
		}
	}

	switch stringValue(raw["type"]) {
	case "user", "user_message":
		return "user"
	case "assistant", "assistant_message", "agent_message":
		return "assistant"
	default:
		return ""
	}
}

func codexContent(raw map[string]any) string {
	if content := textFromCodexContent(raw["content"]); content != "" {
		return content
	}

	payload := mapValue(raw["payload"])
	if payload != nil {
		if content := textFromCodexContent(payload["content"]); content != "" {
			return content
		}
		if content := stringValue(payload["message"]); content != "" {
			return content
		}
		if content := stringValue(payload["text"]); content != "" {
			return content
		}
	}

	if content := stringValue(raw["message"]); content != "" {
		return content
	}
	return stringValue(raw["text"])
}

func codexModel(raw map[string]any) string {
	if model := stringValue(raw["model"]); model != "" {
		return model
	}
	if payload := mapValue(raw["payload"]); payload != nil {
		return stringValue(payload["model"])
	}
	return ""
}

func codexCWD(raw map[string]any) string {
	if cwd := stringValue(raw["cwd"]); cwd != "" {
		return cwd
	}
	if payload := mapValue(raw["payload"]); payload != nil {
		return stringValue(payload["cwd"])
	}
	return ""
}

func codexTranscriptPath(cfg AgentConfig, sessionID, transcriptPath string) (string, error) {
	if transcriptPath != "" {
		return transcriptPath, nil
	}
	sessionsDir, rootErr := cfg.SourceRoot(sessionStoreCodex)
	if rootErr != nil {
		return "", rootErr
	}
	found, findErr := findSessionFile(sessionsDir, func(_ string, entry fs.DirEntry) bool {
		if !strings.HasSuffix(entry.Name(), ".jsonl") {
			return false
		}
		return extractCodexSessionID(strings.TrimSuffix(entry.Name(), ".jsonl")) == sessionID
	})
	if findErr != nil {
		return "", fmt.Errorf("failed to search Codex transcripts in %s: %w", sessionsDir, findErr)
	}
	if found == "" {
		return "", fmt.Errorf("session file not found for codex session %s", sessionID)
	}
	transcriptPath = found
	return transcriptPath, nil
}

// RunAgentSessionLogCodex reads Codex rollout session files and processes the session.
func RunAgentSessionLogCodex(ctx context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, false)
	if err != nil {
		return err
	}
	if halt {
		return nil
	}
	sessionID, cwd = identity.Session, identity.CWD

	transcriptPath, err := hookTranscriptPath(identity, "codex")
	if err != nil {
		return err
	}
	transcriptPath, err = codexTranscriptPath(state.Config.Agent, sessionID, transcriptPath)
	if err != nil {
		return err
	}

	fingerprint, stored, isStored, err := fingerprintStoredTranscript("codex", sessionID, transcriptPath)
	if err != nil {
		return err
	}
	if isStored {
		reportStoredGeneration(state.Stderr, stored)
		return nil
	}

	file, err := os.Open(transcriptPath)
	if err != nil {
		return err
	}
	defer func() { _ = file.Close() }()

	usage := &UsageRecord{Harness: sessionStoreCodex, Agent: sessionStoreCodex, SessionID: sessionID, CWD: cwd}
	var logs []SessionLogLine
	activeModel := ""
	activeCWD := cwd
	decodeStats, decodeErr := decodeJSONLWithStats(state.Stderr, transcriptPath, file, func(raw map[string]any) error {
		updateCodexUsage(usage, raw)
		if model := codexModel(raw); model != "" {
			activeModel = model
		}
		if logCWD := codexCWD(raw); logCWD != "" {
			activeCWD = resolveCWD(logCWD)
		}

		role := codexRole(raw)
		if role != "user" && role != "assistant" {
			return nil
		}

		content := codexContent(raw)
		if strings.TrimSpace(content) == "" {
			return nil
		}

		ts, _ := raw["timestamp"].(string)
		if ts == "" {
			ts, _ = raw["created_at"].(string)
		}
		if ts == "" {
			ts, _ = raw["ts"].(string)
		}
		// A missing source time remains empty so normalized output does not change
		// merely because a hook and sync run at different times.

		model := codexModel(raw)
		if model == "" {
			model = activeModel
		}

		logCWD := codexCWD(raw)
		if logCWD != "" {
			logCWD = resolveCWD(logCWD)
		} else {
			logCWD = activeCWD
		}

		logs = append(logs, SessionLogLine{
			TS:      ts,
			Agent:   "codex",
			SID:     sessionID,
			Role:    role,
			Content: content,
			CWD:     logCWD,
			Model:   model,
		})
		return nil
	})
	if decodeErr != nil {
		return decodeErr
	}

	_, err = writeSessionLogs(ctx, state, "codex", sessionID, logs, sessionSource{Type: "codex-jsonl", Fingerprint: fingerprint, Malformed: decodeStats.Malformed, Skipped: decodeStats.Decoded - len(logs)})
	if err == nil {
		recordUsageBestEffort(state, "codex", func() (*UsageRecord, error) {
			return finalizeTranscriptUsage(usage), nil
		})
	}
	return err
}

// ExtractUsageCodex extracts token usage from OpenAI Codex's rollout file.
func ExtractUsageCodex(cfg AgentConfig, sessionID, cwd, transcriptPath string) (*UsageRecord, error) {
	transcriptPath, err := codexTranscriptPath(cfg, sessionID, transcriptPath)
	if err != nil {
		return nil, err
	}

	return readTranscriptUsage(transcriptPath, &UsageRecord{
		Harness:   sessionStoreCodex,
		Agent:     sessionStoreCodex,
		SessionID: sessionID,
		CWD:       cwd,
	}, updateCodexUsage)
}

func updateCodexUsage(rec *UsageRecord, raw map[string]any) {
	if ts, ok := raw["timestamp"].(string); ok && ts != "" {
		rec.Timestamp = ts
	}
	payload := mapValue(raw["payload"])
	switch typ := stringValue(raw["type"]); typ {
	case "turn_context", "session_meta":
		if model := stringValue(payload["model"]); typ == "turn_context" && model != "" {
			rec.Model = model
		}
		if cwd := stringValue(payload["cwd"]); cwd != "" && rec.CWD == "" {
			rec.CWD = resolveCWD(cwd)
		}
	case "response_item":
		if stringValue(payload["role"]) == "assistant" {
			rec.TurnCount++
		}
	case "event_msg":
		if stringValue(payload["type"]) != "token_count" {
			return
		}
		total := mapValue(mapValue(payload["info"])["total_token_usage"])
		if in, ok := total["input_tokens"].(float64); ok {
			rec.InputTokens = int64(in)
		}
		if out, ok := total["output_tokens"].(float64); ok {
			rec.OutputTokens = int64(out)
		}
		if cached, ok := total["cached_input_tokens"].(float64); ok {
			rec.CachedTokens = int64(cached)
		}
		if written, ok := total["cache_write_input_tokens"].(float64); ok {
			rec.CacheWriteTokens = int64(written)
		}
		if reasoning, ok := total["reasoning_output_tokens"].(float64); ok {
			rec.ReasoningTokens = int64(reasoning)
		}
		if tokens, ok := total["total_tokens"].(float64); ok {
			rec.TotalTokens = int64(tokens)
		}
	}
}

func handleCodexUsageHook(_ context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, false)
	if err != nil {
		return err
	}
	if halt {
		return nil
	}
	sessionID, cwd = identity.Session, identity.CWD
	transcriptPath, err := hookTranscriptPath(identity, "codex")
	if err != nil {
		return err
	}
	rec, err := ExtractUsageCodex(state.Config.Agent, sessionID, cwd, transcriptPath)
	if err != nil {
		return err
	}
	return WriteUsageRecord(*rec)
}

func syncCodexSessions(ctx context.Context, state *GlobalState, root string) (int, error) {
	return syncTranscriptSessions(ctx, state, root, "Codex", codexSessionID, RunAgentSessionLogCodex)
}

func codexSessionID(path string) string {
	return extractCodexSessionID(strings.TrimSuffix(filepath.Base(path), ".jsonl"))
}
