package dot

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// agyTranscriptCandidates returns the transcript paths for one agy session, in
// preference order, beneath the configured source root.
func agyTranscriptCandidates(cfg AgentConfig, sessionID string) ([]string, error) {
	root, err := cfg.SourceRoot(sessionStoreAgy)
	if err != nil {
		return nil, err
	}
	candidates := make([]string, 0, len(agyTranscriptNames))
	for _, name := range agyTranscriptNames {
		candidates = append(candidates, filepath.Join(root, sessionID, ".system_generated", "logs", name))
	}
	return candidates, nil
}

// RunAgentSessionLogAgy reads the agy transcript files and processes the session.
func RunAgentSessionLogAgy(ctx context.Context, state *GlobalState, sessionID, cwd string) error {
	// agy fires Stop on every turn boundary, so a busy turn must be acknowledged
	// without ingesting a half-written transcript.
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, true)
	if err != nil {
		return err
	}
	if halt {
		return writeAntigravityStopDecision(state.Stdout)
	}
	sessionID, cwd = identity.Session, identity.CWD

	transcriptPath, err := hookTranscriptPath(identity, "antigravity")
	if err != nil {
		return err
	}
	if transcriptPath == "" {
		candidates, candidateErr := agyTranscriptCandidates(state.Config.Agent, sessionID)
		if candidateErr != nil {
			return candidateErr
		}
		for _, candidate := range candidates {
			if _, statErr := os.Stat(candidate); statErr == nil {
				transcriptPath = candidate
				break
			}
		}
		if transcriptPath == "" {
			return fmt.Errorf("transcript file not found for agy session %s", sessionID)
		}
	}

	fingerprint, stored, isStored, err := fingerprintStoredTranscript("agy", sessionID, transcriptPath)
	if err != nil {
		return err
	}
	if isStored {
		reportStoredGeneration(state.Stderr, stored)
		if identity.FromHook() {
			return writeAntigravityStopDecision(state.Stdout)
		}
		return nil
	}

	file, err := os.Open(transcriptPath)
	if err != nil {
		return err
	}
	defer func() { _ = file.Close() }()

	var logs []SessionLogLine
	decodeStats, decodeErr := decodeJSONLWithStats(state.Stderr, transcriptPath, file, func(raw map[string]any) error {
		if trunc, ok := raw["is_truncated"].(bool); ok && trunc {
			return nil
		}

		source, _ := raw["source"].(string)
		typ, _ := raw["type"].(string)
		createdAt, _ := raw["created_at"].(string)
		content, _ := raw["content"].(string)

		var role string
		if source == "USER_EXPLICIT" && typ == "USER_INPUT" {
			role = "user"
		} else if source == "MODEL" && typ == "PLANNER_RESPONSE" {
			role = "assistant"
		} else {
			return nil
		}

		if strings.TrimSpace(content) == "" {
			return nil
		}

		logs = append(logs, SessionLogLine{
			TS:      createdAt,
			Agent:   "agy",
			SID:     sessionID,
			Role:    role,
			Content: content,
			CWD:     cwd,
		})
		return nil
	})
	if decodeErr != nil {
		return decodeErr
	}

	if _, err := writeSessionLogs(ctx, state, "agy", sessionID, logs, sessionSource{Type: "antigravity-jsonl", Fingerprint: fingerprint, Malformed: decodeStats.Malformed, Skipped: decodeStats.Decoded - len(logs)}); err != nil {
		return err
	}
	recordUsageBestEffort(state, "agy", func() (*UsageRecord, error) {
		return ExtractUsageAgy(state, sessionID, cwd, transcriptPath)
	})
	if identity.FromHook() {
		return writeAntigravityStopDecision(state.Stdout)
	}
	return nil
}

func writeAntigravityStopDecision(stdout io.Writer) error {
	response := struct {
		Decision string `json:"decision"`
	}{}
	if err := json.NewEncoder(stdout).Encode(response); err != nil {
		return fmt.Errorf("failed to write Antigravity Stop response: %w", err)
	}
	return nil
}

// ExtractUsageAgy extracts token usage from Antigravity's transcript steps.
func ExtractUsageAgy(state *GlobalState, sessionID, cwd, transcriptPath string) (*UsageRecord, error) {
	if transcriptPath == "" {
		candidates, err := agyTranscriptCandidates(state.Config.Agent, sessionID)
		if err != nil {
			return nil, err
		}
		for _, c := range candidates {
			if _, statErr := os.Stat(c); statErr == nil {
				transcriptPath = c
				break
			}
		}
		if transcriptPath == "" {
			return nil, fmt.Errorf("transcript file not found for agy session %s", sessionID)
		}
	}
	file, err := os.Open(transcriptPath)
	if err != nil {
		return nil, err
	}
	defer func() { _ = file.Close() }()

	rec := &UsageRecord{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Harness:   sessionStoreAgy,
		Agent:     sessionStoreAgy,
		SessionID: sessionID,
		Model:     "gemini",
		CWD:       cwd,
	}

	var inputBytes int64
	var outputBytes int64

	scanner := bufio.NewScanner(file)
	buf := make([]byte, 1024*1024)
	scanner.Buffer(buf, 16*1024*1024)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(bytes.TrimSpace(line)) == 0 {
			continue
		}
		var raw map[string]any
		if err := json.Unmarshal(line, &raw); err != nil {
			continue
		}
		if ts, ok := raw["created_at"].(string); ok && ts != "" {
			rec.Timestamp = ts
		}
		source, _ := raw["source"].(string)
		typ, _ := raw["type"].(string)
		content, _ := raw["content"].(string)

		if source == "USER_EXPLICIT" && typ == "USER_INPUT" {
			rec.TurnCount++
			inputBytes += int64(len(content))
		} else if source == "MODEL" && typ == "PLANNER_RESPONSE" {
			outputBytes += int64(len(content))
			if thinking, ok := raw["thinking"].(string); ok {
				outputBytes += int64(len(thinking))
			}
		} else if typ == "RUN_COMMAND" || typ == "SYSTEM_MESSAGE" {
			inputBytes += int64(len(content))
		}
	}

	rec.InputTokens = (inputBytes + 3) / 4
	rec.OutputTokens = (outputBytes + 3) / 4
	rec.TotalTokens = rec.InputTokens + rec.OutputTokens
	return rec, scanner.Err()
}

func handleAgyUsageHook(_ context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, true)
	if err != nil {
		return err
	}
	if halt {
		return writeAntigravityStopDecision(state.Stdout)
	}
	sessionID, cwd = identity.Session, identity.CWD
	transcriptPath, err := hookTranscriptPath(identity, "antigravity")
	if err != nil {
		return err
	}
	rec, err := ExtractUsageAgy(state, sessionID, cwd, transcriptPath)
	if err != nil {
		if identity.FromHook() {
			_ = writeAntigravityStopDecision(state.Stdout)
		}
		return err
	}
	if err := WriteUsageRecord(*rec); err != nil {
		if identity.FromHook() {
			_ = writeAntigravityStopDecision(state.Stdout)
		}
		return err
	}
	if identity.FromHook() {
		return writeAntigravityStopDecision(state.Stdout)
	}
	return nil
}

// syncAgySessions walks the agy brain directory, ingesting every session that has a
// readable transcript. Sessions without one are skipped, not failed: agy creates the
// directory before the transcript exists.
func syncAgySessions(ctx context.Context, state *GlobalState, root string) (int, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return 0, fmt.Errorf("failed to read agy sessions: %w", err)
	}
	count := 0
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		sessionID := entry.Name()
		candidates, candidateErr := agyTranscriptCandidates(state.Config.Agent, sessionID)
		if candidateErr != nil {
			return 0, candidateErr
		}
		present := false
		for _, candidate := range candidates {
			if _, statErr := os.Stat(candidate); statErr == nil {
				present = true
				break
			} else if !errors.Is(statErr, os.ErrNotExist) {
				return 0, fmt.Errorf("failed to inspect agy transcript %s: %w", candidate, statErr)
			}
		}
		if !present {
			continue
		}
		if logErr := RunAgentSessionLogAgy(ctx, state, sessionID, ""); logErr != nil {
			return 0, fmt.Errorf("failed to sync agy session %s: %w", sessionID, logErr)
		}
		count++
	}
	return count, nil
}

func agyUsageCandidates(_ context.Context, state *GlobalState, root string) ([]usageSyncCandidate, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, err
	}
	var candidates []usageSyncCandidate
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		// Resolve through the shared candidate list so the backfill reads
		// the same transcript the hook does. Hard-coding transcript.jsonl
		// skipped sessions carrying only transcript_full.jsonl, and read
		// the shorter file when both existed -- which then overwrote the
		// accurate hook-written record with a byte-count undercount.
		paths, pathErr := agyTranscriptCandidates(state.Config.Agent, entry.Name())
		if pathErr != nil {
			return nil, pathErr
		}
		for _, path := range paths {
			if _, statErr := os.Stat(path); statErr == nil {
				candidates = append(candidates, usageSyncCandidate{SessionID: entry.Name(), Path: path})
				break
			}
		}
	}
	return candidates, nil
}
