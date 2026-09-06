package dot

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/urfave/cli/v3"
)

// HookInput represents the normalized JSON context passed by agent hooks on stdin.
type HookInput struct {
	SessionID      string `json:"session_id"`
	CWD            string `json:"cwd"`
	TranscriptPath string `json:"transcript_path"`
	StopHookActive bool   `json:"stop_hook_active"`
	FullyIdle      bool   `json:"fullyIdle"`
}

// UnmarshalJSON normalizes the snake_case Claude/Codex hook payload and the
// camelCase Antigravity and Grok payloads into one canonical HookInput.
func (h *HookInput) UnmarshalJSON(data []byte) error {
	var raw struct {
		SessionID                 string   `json:"session_id"`
		ConversationID            string   `json:"conversationId"`
		GrokSessionID             string   `json:"sessionId"`
		CWD                       string   `json:"cwd"`
		TranscriptPath            string   `json:"transcript_path"`
		AntigravityTranscriptPath string   `json:"transcriptPath"`
		WorkspacePaths            []string `json:"workspacePaths"`
		StopHookActive            bool     `json:"stop_hook_active"`
		// Grok emits the whole envelope in camelCase, so the Claude-compatible
		// stop guard only fires if its spelling is accepted too; without it a
		// hook-continued turn notifies twice.
		GrokStopHookActive bool `json:"stopHookActive"`
		FullyIdle          bool `json:"fullyIdle"`
	}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}

	h.SessionID = raw.SessionID
	if h.SessionID == "" {
		h.SessionID = raw.ConversationID
	}
	if h.SessionID == "" {
		h.SessionID = raw.GrokSessionID
	}
	h.CWD = raw.CWD
	if h.CWD == "" {
		for _, path := range raw.WorkspacePaths {
			if path != "" {
				h.CWD = path
				break
			}
		}
	}
	h.TranscriptPath = raw.TranscriptPath
	if h.TranscriptPath == "" {
		h.TranscriptPath = raw.AntigravityTranscriptPath
	}
	h.StopHookActive = raw.StopHookActive || raw.GrokStopHookActive
	h.FullyIdle = raw.FullyIdle
	return nil
}

// SessionLogLine is the unified format for logging prompt turns.
type SessionLogLine struct {
	TS      string `json:"ts"`
	Agent   string `json:"agent"`
	SID     string `json:"sid"`
	Role    string `json:"role"`
	Content string `json:"content"`
	CWD     string `json:"cwd,omitempty"`
	Model   string `json:"model,omitempty"`
}

// NewAgentCmd constructs the agent command group.
func NewAgentCmd(state *GlobalState) *cli.Command {
	return &cli.Command{
		Name:    "agent",
		Aliases: []string{"a"},
		Usage:   "Manage AI agent integrations and sessions",
		Commands: []*cli.Command{
			NewAgentCleanCmd(state),
			NewAgentDoctorCmd(state),
			NewAgentHookCmd(state),
			NewAgentSessionCmd(state),
			NewAgentUsageCmd(state),
		},
	}
}

// agentSessionLogger is the per-agent entrypoint for session ingestion or usage
// hooks, with the session ID and working directory supplied by the caller.
type agentSessionLogger func(ctx context.Context, state *GlobalState, sessionID, cwd string) error

// agentSessionEntry is one agent's ingestion entrypoint and the one-line usage its
// subcommand advertises.
type agentSessionEntry struct {
	Log   agentSessionLogger
	Usage string
}

// NewAgentSessionCmd constructs the agent session command group.
func NewAgentSessionCmd(state *GlobalState) *cli.Command {
	commands := []*cli.Command{
		NewAgentSessionListCmd(state),
		NewAgentSessionShowCmd(state),
		NewAgentSessionExportCmd(state),
	}
	// Table order follows the canonical agent table so `--help` lists the agents in
	// the same order everywhere dot reports them.
	for _, definition := range agentDefinitions() {
		entry := definition.Session
		var aliases []string
		if definition.Alias != "" {
			aliases = []string{definition.Alias}
		}
		commands = append(commands, &cli.Command{
			Name:      definition.Agent,
			Aliases:   aliases,
			Usage:     entry.Usage,
			ArgsUsage: "[SESSION-ID] [CWD]",
			Action: func(ctx context.Context, cmd *cli.Command) error {
				return entry.Log(ctx, state, cmd.Args().Get(0), cmd.Args().Get(1))
			},
		})
	}
	return &cli.Command{
		Name:    "session",
		Aliases: []string{"s"},
		Usage:   "Manage agent session logs",
		Commands: append(commands,
			NewAgentSessionSyncCmd(state),
			&cli.Command{
				Name:    "migrate",
				Aliases: []string{"m"},
				Usage:   "Select the most complete legacy transcript per lineage without deleting evidence",
				Flags: []cli.Flag{
					&cli.BoolFlag{Name: "apply", Usage: "Write selected transcripts to the versioned store (default is dry-run)"},
				},
				Action: func(ctx context.Context, cmd *cli.Command) error {
					return RunAgentSessionMigrate(ctx, state, cmd.Bool("apply"))
				},
			},
		),
	}
}

// NewAgentSessionSyncCmd handles checking and syncing all untracked sessions.
func NewAgentSessionSyncCmd(state *GlobalState) *cli.Command {
	return &cli.Command{
		Name:    "sync",
		Aliases: []string{"s"},
		Usage:   "Scan for new sessions across all agents and log them",
		Action: func(ctx context.Context, _ *cli.Command) error {
			return RunAgentSessionSync(ctx, state)
		},
	}
}

func sessionStateWithTranscript(state *GlobalState, sessionID, transcriptPath string) (*GlobalState, error) {
	payload, err := json.Marshal(HookInput{SessionID: sessionID, TranscriptPath: transcriptPath, FullyIdle: true})
	if err != nil {
		return nil, err
	}
	sourced := *state
	sourced.Stdin = strings.NewReader(string(payload))
	return &sourced, nil
}

// hookIdentity is the session identity one ingestion call resolved, merged from the
// command-line operands and an optional hook payload on stdin.
type hookIdentity struct {
	Input   *HookInput
	Session string
	CWD     string
}

// FromHook reports whether this invocation was driven by a hook payload rather than
// by `agent session sync` or a manual command line.
func (h hookIdentity) FromHook() bool { return h.Input != nil }

// resolveHookIdentity merges the operands with any hook payload on stdin and
// validates the result. It returns halt=true when the payload says this invocation
// must do nothing: a re-entrant Stop hook, or — when requireIdle is set for an agent
// whose Stop event also fires mid-turn — a turn that is not finished yet.
func resolveHookIdentity(state *GlobalState, sessionID, cwd string, requireIdle bool) (identity hookIdentity, halt bool, err error) {
	input, err := parseStdin(state.Stdin)
	if err != nil {
		return hookIdentity{}, false, err
	}
	if input != nil {
		if input.StopHookActive || (requireIdle && !input.FullyIdle) {
			return hookIdentity{Input: input}, true, nil
		}
		if sessionID == "" {
			sessionID = input.SessionID
		}
		if cwd == "" {
			cwd = input.CWD
		}
	}
	if sessionID == "" {
		return hookIdentity{}, false, errors.New("missing session_id")
	}
	if !isValidSessionID(sessionID) {
		return hookIdentity{}, false, fmt.Errorf("invalid session_id format: %q", sessionID)
	}
	return hookIdentity{Input: input, Session: sessionID, CWD: resolveCWD(cwd)}, false, nil
}

// hookTranscriptPath returns the transcript the hook payload pointed at, after
// verifying it is a readable regular file. An empty result means the payload named
// no transcript and the caller must discover it from the agent's own store layout.
func hookTranscriptPath(identity hookIdentity, agent string) (string, error) {
	if identity.Input == nil || identity.Input.TranscriptPath == "" {
		return "", nil
	}
	path := ExpandPath(identity.Input.TranscriptPath)
	info, err := os.Stat(path)
	if err != nil {
		return "", fmt.Errorf("%s transcript from hook payload is unavailable at %s: %w", agent, path, err)
	}
	if info.IsDir() {
		return "", fmt.Errorf("%s transcript from hook payload is not a file: %s", agent, path)
	}
	return path, nil
}

// parseStdin reads stdin to extract HookInput when data is piped by an agent hook.
func parseStdin(stdin io.Reader) (*HookInput, error) {
	if stdin == nil {
		return nil, nil
	}
	if file, ok := stdin.(*os.File); ok {
		stat, err := file.Stat()
		if err != nil {
			return nil, err
		}
		if (stat.Mode() & os.ModeCharDevice) != 0 {
			return nil, nil
		}
	}

	// Hook producers close stdin after writing one JSON payload, so ReadAll cannot
	// block in normal hook execution and also handles payloads without a trailing newline.
	data, err := io.ReadAll(stdin)
	if err != nil {
		return nil, err
	}
	if len(data) == 0 {
		return nil, nil
	}
	var input HookInput
	if err := json.Unmarshal(data, &input); err != nil {
		return nil, fmt.Errorf("failed to parse agent hook input: %w", err)
	}
	return &input, nil
}

// resolveCWD converts a relative or empty CWD to an absolute path.
func resolveCWD(cwd string) string {
	if cwd == "" {
		return ""
	}
	if cwd == "." {
		if pwd, err := os.Getwd(); err == nil {
			return pwd
		}
		return "."
	}
	if abs, err := filepath.Abs(cwd); err == nil {
		return abs
	}
	return cwd
}

// isValidSessionRune checks if a rune is allowed in a session ID.
func isValidSessionRune(r rune) bool {
	return (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '-' || r == '_'
}

func isValidSessionID(sessionID string) bool {
	if sessionID == "" {
		return false
	}
	for _, r := range sessionID {
		if !isValidSessionRune(r) {
			return false
		}
	}
	return true
}

// agyTranscriptNames are the transcript files an agy session may carry, most
// complete first.
var agyTranscriptNames = []string{"transcript_full.jsonl", "transcript.jsonl"}

// grokTranscriptName is the ACP session-update stream Grok treats as the
// authoritative conversation log; the sibling grokChatHistoryName file is the raw
// model wire format and carries the system prompt, which the archive must not keep.
const grokTranscriptName = "updates.jsonl"

// grokChatHistoryName is Grok's raw model wire-format sibling to grokTranscriptName.
// pruneRawSessions disposes of it alongside its sibling once that one is verified,
// since it carries no identity of its own.
const grokChatHistoryName = "chat_history.jsonl"

// grokUpdateRoles maps the session-update kinds that carry conversation text to
// canonical roles. Everything else in the stream — reasoning, tool calls, hook runs,
// plan revisions — is machinery rather than the conversation.
var grokUpdateRoles = map[string]string{
	"user_message_chunk":  "user",
	"agent_message_chunk": "assistant",
}

const opencodeMessagesQuery = `SELECT
    m.session_id AS session_id,
    m.id AS message_id,
    m.time_created,
    m.data,
    s.directory,
    p.id AS part_id,
    p.data AS part_data
FROM message m
JOIN session s ON m.session_id = s.id
LEFT JOIN part p ON p.message_id = m.id
WHERE %s
ORDER BY m.session_id, m.time_created, m.id, p.time_created, p.id`

const opencodeSessionsQuery = "SELECT id, directory FROM session"

const copilotTurnsQuery = `SELECT
    t.session_id AS session_id,
    t.turn_index AS turn_index,
    t.user_message AS user_message,
    t.assistant_response AS assistant_response,
    t.timestamp AS timestamp,
    s.cwd AS cwd
FROM turns t
JOIN sessions s ON t.session_id = s.id
WHERE %s
ORDER BY t.session_id, t.turn_index, t.id`

const copilotSessionsQuery = "SELECT id, cwd FROM sessions"
