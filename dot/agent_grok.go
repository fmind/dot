package dot

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// grokSessionDirectory encodes a working directory the way Grok names its
// per-project session folder: every path separator becomes %2F.
func grokSessionDirectory(cwd string) string {
	return url.PathEscape(cwd)
}

// grokCWDFromPath recovers the working directory a transcript belongs to from the
// encoded first path segment. Subagent transcripts nest further down, so the segment
// is taken relative to the store root rather than from the parent directories.
func grokCWDFromPath(root, path string) string {
	relative, err := filepath.Rel(root, path)
	if err != nil {
		return ""
	}
	parts := strings.Split(relative, string(filepath.Separator))
	if len(parts) < 2 {
		return ""
	}
	decoded, err := url.PathUnescape(parts[0])
	if err != nil {
		return ""
	}
	return decoded
}

// grokTimestamp renders the Unix-second stamp on every session update. A missing or
// non-positive stamp stays empty so normalized output never invents a time.
func grokTimestamp(value any) string {
	seconds, ok := value.(float64)
	if !ok || seconds <= 0 {
		return ""
	}
	return time.Unix(int64(seconds), 0).UTC().Format(time.RFC3339)
}

// grokMessage accumulates the chunks of one streamed message. Grok emits text a
// fragment at a time, so a message only exists once its run of chunks ends.
type grokMessage struct {
	Role     string
	PromptID string
	TS       string
	Model    string
	Parts    []string
}

// RunAgentSessionLogGrok reads a Grok Build session update stream and processes the session.
func RunAgentSessionLogGrok(ctx context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, false)
	if err != nil {
		return err
	}
	if halt {
		return nil
	}
	sessionID, cwd = identity.Session, identity.CWD

	sessionsDir, err := state.Config.Agent.SourceRoot(sessionStoreGrok)
	if err != nil {
		return err
	}

	transcriptPath, err := hookTranscriptPath(identity, "grok")
	if err != nil {
		return err
	}
	if transcriptPath == "" {
		transcriptPath, err = findGrokTranscript(sessionsDir, sessionID, cwd)
		if err != nil {
			return err
		}
	}
	if cwd == "" {
		cwd = resolveCWD(grokCWDFromPath(sessionsDir, transcriptPath))
	}

	fingerprint, stored, isStored, err := fingerprintStoredTranscript("grok", sessionID, transcriptPath)
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

	var logs []SessionLogLine
	var current grokMessage
	activeModel := ""
	flush := func() {
		content := strings.Join(current.Parts, "")
		if current.Role == "" || strings.TrimSpace(content) == "" {
			current = grokMessage{}
			return
		}
		logs = append(logs, SessionLogLine{
			TS:      current.TS,
			Agent:   "grok",
			SID:     sessionID,
			Role:    current.Role,
			Content: content,
			CWD:     cwd,
			Model:   current.Model,
		})
		current = grokMessage{}
	}

	decodeStats, decodeErr := decodeJSONLWithStats(state.Stderr, transcriptPath, file, func(raw map[string]any) error {
		params := mapValue(raw["params"])
		update := mapValue(params["update"])
		if update == nil {
			return nil
		}
		// The prompt's model is announced on the user chunk that opens the turn, so it
		// stays active for the assistant chunks that answer it.
		if model := stringValue(mapValue(update["_meta"])["modelId"]); model != "" {
			activeModel = model
		}

		role, carriesText := grokUpdateRoles[stringValue(update["sessionUpdate"])]
		if !carriesText {
			return nil
		}
		text := stringValue(mapValue(update["content"])["text"])
		if text == "" {
			return nil
		}

		// One message is the run of chunks sharing a role and a prompt; either changing
		// means the previous message is complete.
		promptID := stringValue(mapValue(params["_meta"])["promptId"])
		if current.Role != role || current.PromptID != promptID {
			flush()
			current = grokMessage{Role: role, PromptID: promptID, TS: grokTimestamp(raw["timestamp"]), Model: activeModel}
		}
		current.Parts = append(current.Parts, text)
		return nil
	})
	if decodeErr != nil {
		return decodeErr
	}
	flush()

	_, err = writeSessionLogs(ctx, state, "grok", sessionID, logs, sessionSource{Type: "grok-jsonl", Fingerprint: fingerprint, Malformed: decodeStats.Malformed, Skipped: decodeStats.Decoded - len(logs)})
	if err == nil {
		recordUsageBestEffort(state, "grok", func() (*UsageRecord, error) {
			return ExtractUsageGrok(state, sessionID, cwd)
		})
	}
	return err
}

// findGrokTranscript locates one session's update stream. The CWD-derived path is
// exact when the session ran where the hook says it did; the scan below covers a
// session resumed from another directory or started in a worktree.
func findGrokTranscript(sessionsDir, sessionID, cwd string) (string, error) {
	if cwd != "" {
		candidate := filepath.Join(sessionsDir, grokSessionDirectory(cwd), sessionID, grokTranscriptName)
		_, statErr := os.Stat(candidate)
		if statErr == nil {
			return candidate, nil
		}
		if !errors.Is(statErr, os.ErrNotExist) {
			return "", fmt.Errorf("failed to inspect expected Grok transcript %s: %w", candidate, statErr)
		}
	}
	found, findErr := findSessionFile(sessionsDir, func(path string, entry fs.DirEntry) bool {
		return entry.Name() == grokTranscriptName && filepath.Base(filepath.Dir(path)) == sessionID
	})
	if findErr != nil {
		return "", fmt.Errorf("failed to search Grok transcripts in %s: %w", sessionsDir, findErr)
	}
	if found == "" {
		return "", fmt.Errorf("session file not found for grok session %s", sessionID)
	}
	return found, nil
}

// ExtractUsageGrok extracts token usage from Grok Build's signals.json.
func ExtractUsageGrok(state *GlobalState, sessionID, cwd string) (*UsageRecord, error) {
	root, err := state.Config.Agent.SourceRoot(sessionStoreGrok)
	if err != nil {
		return nil, err
	}
	var sessionDir string
	if cwd != "" {
		candidate := filepath.Join(root, grokSessionDirectory(cwd), sessionID)
		if info, statErr := os.Stat(candidate); statErr == nil && info.IsDir() {
			sessionDir = candidate
		}
	}
	if sessionDir == "" {
		entries, readErr := os.ReadDir(root)
		if readErr == nil {
			for _, entry := range entries {
				if entry.IsDir() {
					candidate := filepath.Join(root, entry.Name(), sessionID)
					if info, statErr := os.Stat(candidate); statErr == nil && info.IsDir() {
						sessionDir = candidate
						break
					}
				}
			}
		}
	}
	if sessionDir == "" {
		return nil, fmt.Errorf("grok session directory not found for %s", sessionID)
	}

	rec := &UsageRecord{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Harness:   sessionStoreGrok,
		Agent:     sessionStoreGrok,
		SessionID: sessionID,
		CWD:       cwd,
	}

	signalsPath := filepath.Join(sessionDir, "signals.json")
	if data, readErr := os.ReadFile(signalsPath); readErr == nil {
		var sig struct {
			PrimaryModelID      string `json:"primaryModelId"`
			ContextTokensUsed   int64  `json:"contextTokensUsed"`
			ContextWindowTokens int64  `json:"contextWindowTokens"`
			TurnCount           int    `json:"turnCount"`
		}
		if json.Unmarshal(data, &sig) == nil {
			// Grok records no cumulative token counts anywhere in a session
			// directory -- signals.json only reports how full the context window
			// ended up. That is an input-side measurement, so it goes in
			// InputTokens and TotalTokens keeps the sum-of-parts definition every
			// other harness uses; assigning occupancy straight to TotalTokens made
			// Grok rows self-contradictory and the cross-harness total meaningless.
			// The consequence is a documented undercount: Grok output tokens are
			// not observable.
			rec.InputTokens = sig.ContextTokensUsed
			rec.TotalTokens = rec.InputTokens + rec.OutputTokens + rec.CachedTokens + rec.CacheWriteTokens
			rec.Model = sig.PrimaryModelID
			rec.TurnCount = sig.TurnCount
		}
	}
	return rec, nil
}

func handleGrokUsageHook(_ context.Context, state *GlobalState, sessionID, cwd string) error {
	identity, halt, err := resolveHookIdentity(state, sessionID, cwd, false)
	if err != nil {
		return err
	}
	if halt {
		return nil
	}
	sessionID, cwd = identity.Session, identity.CWD
	rec, err := ExtractUsageGrok(state, sessionID, cwd)
	if err != nil {
		return err
	}
	return WriteUsageRecord(*rec)
}

func syncGrokSessions(ctx context.Context, state *GlobalState, root string) (int, error) {
	return syncTranscriptSessions(ctx, state, root, "Grok", func(path string) string {
		// Grok stores other JSONL streams beside the transcript; do not ingest them.
		if filepath.Base(path) != grokTranscriptName {
			return ""
		}
		return filepath.Base(filepath.Dir(path))
	}, RunAgentSessionLogGrok)
}

func grokUsageCandidates(_ context.Context, _ *GlobalState, root string) ([]usageSyncCandidate, error) {
	// Grok nests sessions one level below a per-cwd directory whose name
	// is an encoded path, so the extractor re-locates the session itself.
	cwdDirs, err := os.ReadDir(root)
	if err != nil {
		return nil, err
	}
	var candidates []usageSyncCandidate
	for _, cwdDir := range cwdDirs {
		if !cwdDir.IsDir() {
			continue
		}
		sessions, readErr := os.ReadDir(filepath.Join(root, cwdDir.Name()))
		if readErr != nil {
			return nil, readErr
		}
		for _, session := range sessions {
			if session.IsDir() {
				candidates = append(candidates, usageSyncCandidate{SessionID: session.Name()})
			}
		}
	}
	return candidates, nil
}
