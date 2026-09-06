package dot

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"text/tabwriter"
	"time"

	"github.com/urfave/cli/v3"
)

// UsageRecord represents the normalized token usage and cost metrics for one agent session.
type UsageRecord struct {
	Timestamp        string  `json:"timestamp"`
	Harness          string  `json:"harness"`
	Agent            string  `json:"agent"`
	SessionID        string  `json:"session_id"`
	Model            string  `json:"model,omitempty"`
	CWD              string  `json:"cwd,omitempty"`
	InputTokens      int64   `json:"input_tokens"`
	OutputTokens     int64   `json:"output_tokens"`
	CachedTokens     int64   `json:"cached_tokens,omitempty"`
	CacheWriteTokens int64   `json:"cache_write_tokens,omitempty"`
	ReasoningTokens  int64   `json:"reasoning_tokens,omitempty"`
	TotalTokens      int64   `json:"total_tokens"`
	CostUSD          float64 `json:"cost_usd,omitempty"`
	TurnCount        int     `json:"turn_count,omitempty"`
}

// UsageStatsRow represents aggregated usage stats across a harness or model.
type UsageStatsRow struct {
	Harness          string  `json:"harness"`
	Model            string  `json:"model,omitempty"`
	InputTokens      int64   `json:"input_tokens"`
	OutputTokens     int64   `json:"output_tokens"`
	CachedTokens     int64   `json:"cached_tokens"`
	CacheWriteTokens int64   `json:"cache_write_tokens"`
	ReasoningTokens  int64   `json:"reasoning_tokens"`
	TotalTokens      int64   `json:"total_tokens"`
	CostUSD          float64 `json:"cost_usd"`
	Sessions         int     `json:"sessions"`
	Turns            int     `json:"turns"`
}

// UsageStatsOptions controls filtering and presentation of usage stats.
type UsageStatsOptions struct {
	Harness string
	Since   string
	Until   string
	ByModel bool
	JSON    bool
}

// UsageListOptions controls listing of individual session usage records.
type UsageListOptions struct {
	Harness string
	Limit   int
	JSON    bool
}

// UsageRoot returns the base directory for token usage records (~/.agents/usages).
func UsageRoot() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, ".agents", "usages"), nil
}

// HarnessUsageDir returns the directory for a specific harness's usage records.
func HarnessUsageDir(harness string) (string, error) {
	root, err := UsageRoot()
	if err != nil {
		return "", err
	}
	return filepath.Join(root, harness), nil
}

// WriteUsageRecord writes a usage record atomically to ~/.agents/usages/<harness>/<session_id>.json.
func WriteUsageRecord(record UsageRecord) error {
	if record.Harness == "" {
		return errors.New("missing harness in usage record")
	}
	if record.SessionID == "" {
		return errors.New("missing session_id in usage record")
	}
	if record.Agent == "" {
		record.Agent = record.Harness
	}
	if record.Timestamp == "" {
		record.Timestamp = time.Now().UTC().Format(time.RFC3339)
	}
	if record.TotalTokens == 0 && (record.InputTokens > 0 || record.OutputTokens > 0) {
		record.TotalTokens = record.InputTokens + record.OutputTokens + record.CachedTokens + record.CacheWriteTokens
	}

	dir, dirErr := HarnessUsageDir(record.Harness)
	if dirErr != nil {
		return dirErr
	}
	if mkErr := os.MkdirAll(dir, 0o700); mkErr != nil {
		return fmt.Errorf("failed to create usage directory %s: %w", dir, mkErr)
	}

	data, marshalErr := json.MarshalIndent(record, "", "  ")
	if marshalErr != nil {
		return fmt.Errorf("failed to marshal usage record: %w", marshalErr)
	}
	data = append(data, '\n')

	safeSession := sanitizeFilename(record.SessionID)
	target := filepath.Join(dir, safeSession+".json")
	// Stop and SessionEnd hooks can fire close enough together to overlap on one
	// session, so the publish must tolerate a concurrent writer.
	if writeErr := publishOwnerOnly(target, data); writeErr != nil {
		return fmt.Errorf("failed to write usage record %s: %w", target, writeErr)
	}
	return nil
}

// recordUsageBestEffort refreshes the usage record for a session that has just
// been logged.
//
// It is deliberately non-fatal: `dot agent hook usage <agent>` is the owner of
// usage records and every deployed hook config runs it alongside the session
// hook, so a session must still be ingested when a token count cannot be
// derived. The failure is reported rather than discarded -- the six copies of
// this block that preceded it dropped both the extraction and the write error
// with no explanation, which hid the fixed-temp-file collision for months.
func recordUsageBestEffort(state *GlobalState, agent string, extract func() (*UsageRecord, error)) {
	record, err := extract()
	if err == nil && record != nil {
		err = WriteUsageRecord(*record)
	}
	if err != nil {
		_, _ = fmt.Fprintf(state.Stderr, "%s: usage not recorded for this session: %v\n", agent, err)
	}
}

func sanitizeFilename(s string) string {
	var buf strings.Builder
	for _, r := range s {
		if isValidSessionRune(r) {
			buf.WriteRune(r)
		} else {
			buf.WriteByte('_')
		}
	}
	return buf.String()
}

// RunAgentHookUsage routes an agent usage hook call to the appropriate extractor and saves the record.
func RunAgentHookUsage(ctx context.Context, state *GlobalState, agent, sessionID, cwd string) error {
	definition, ok := agentDefinitionNamed(agent)
	var err error
	if !ok {
		err = fmt.Errorf("unknown usage hook agent %q", agent)
	} else {
		err = definition.UsageHook(ctx, state, sessionID, cwd)
	}
	return spoolHookFailure(state.Config.Agent, agent, "usage", sessionID, err)
}

// LoadAllUsageRecords reads all usage records from ~/.agents/usages.
func LoadAllUsageRecords() ([]UsageRecord, error) {
	root, err := UsageRoot()
	if err != nil {
		return nil, err
	}
	var records []UsageRecord
	err = filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			if errors.Is(walkErr, os.ErrNotExist) {
				return nil
			}
			return walkErr
		}
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
			return nil
		}
		//nolint:gosec // G122: the walked root is the owner-only usages directory, not an attacker-writable path
		data, readErr := os.ReadFile(path)
		if errors.Is(readErr, os.ErrNotExist) {
			// Concurrent cleanup may remove a record after directory enumeration.
			return nil
		}
		if readErr != nil {
			return fmt.Errorf("failed to read usage record %s: %w", path, readErr)
		}
		var rec UsageRecord
		if decodeErr := json.Unmarshal(data, &rec); decodeErr != nil {
			return fmt.Errorf("failed to parse usage record %s: %w", path, decodeErr)
		}
		records = append(records, rec)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return records, nil
}

// RunAgentUsageStats computes aggregated usage stats per harness or model.
func RunAgentUsageStats(ctx context.Context, state *GlobalState, opts UsageStatsOptions) error {
	records, err := LoadAllUsageRecords()
	if err != nil {
		return fmt.Errorf("failed to load usage records: %w", err)
	}

	var sinceTime, untilTime time.Time
	if opts.Since != "" {
		if sinceTime, err = parseFlexibleTime(opts.Since); err != nil {
			return fmt.Errorf("--since: %w", err)
		}
	}
	if opts.Until != "" {
		if untilTime, err = parseFlexibleTime(opts.Until); err != nil {
			return fmt.Errorf("--until: %w", err)
		}
	}

	grouped := make(map[string]*UsageStatsRow)
	for _, rec := range records {
		if opts.Harness != "" && rec.Harness != opts.Harness && rec.Agent != opts.Harness {
			continue
		}
		if !sinceTime.IsZero() {
			t, parseErr := time.Parse(time.RFC3339, rec.Timestamp)
			if parseErr == nil && t.Before(sinceTime) {
				continue
			}
		}
		if !untilTime.IsZero() {
			t, parseErr := time.Parse(time.RFC3339, rec.Timestamp)
			if parseErr == nil && t.After(untilTime) {
				continue
			}
		}

		key := rec.Harness
		if opts.ByModel {
			model := rec.Model
			if model == "" {
				model = "unknown"
			}
			key = rec.Harness + "/" + model
		}

		row, ok := grouped[key]
		if !ok {
			row = &UsageStatsRow{
				Harness: rec.Harness,
			}
			if opts.ByModel {
				row.Model = rec.Model
			}
			grouped[key] = row
		}
		row.Sessions++
		row.Turns += rec.TurnCount
		row.InputTokens += rec.InputTokens
		row.OutputTokens += rec.OutputTokens
		row.CachedTokens += rec.CachedTokens
		row.CacheWriteTokens += rec.CacheWriteTokens
		row.ReasoningTokens += rec.ReasoningTokens
		row.TotalTokens += rec.TotalTokens
		row.CostUSD += rec.CostUSD
	}

	var rows []UsageStatsRow
	for _, r := range grouped {
		rows = append(rows, *r)
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].Harness != rows[j].Harness {
			return rows[i].Harness < rows[j].Harness
		}
		return rows[i].Model < rows[j].Model
	})

	if opts.JSON {
		encoder := json.NewEncoder(state.Stdout)
		encoder.SetIndent("", "  ")
		return encoder.Encode(rows)
	}

	if len(rows) == 0 {
		_, _ = fmt.Fprintln(state.Stdout, "No usage records found in ~/.agents/usages. Run 'dot agent usage sync' to backfill existing sessions.")
		return nil
	}

	w := tabwriter.NewWriter(state.Stdout, 0, 0, 3, ' ', 0)
	if opts.ByModel {
		_, _ = fmt.Fprintln(w, "HARNESS\tMODEL\tSESSIONS\tTURNS\tINPUT TOKENS\tOUTPUT TOKENS\tCACHED TOKENS\tREASONING\tTOTAL TOKENS\tCOST (USD)")
	} else {
		_, _ = fmt.Fprintln(w, "HARNESS\tSESSIONS\tTURNS\tINPUT TOKENS\tOUTPUT TOKENS\tCACHED TOKENS\tREASONING\tTOTAL TOKENS\tCOST (USD)")
	}

	var totalRow UsageStatsRow
	for _, r := range rows {
		totalRow.Sessions += r.Sessions
		totalRow.Turns += r.Turns
		totalRow.InputTokens += r.InputTokens
		totalRow.OutputTokens += r.OutputTokens
		totalRow.CachedTokens += r.CachedTokens
		totalRow.CacheWriteTokens += r.CacheWriteTokens
		totalRow.ReasoningTokens += r.ReasoningTokens
		totalRow.TotalTokens += r.TotalTokens
		totalRow.CostUSD += r.CostUSD

		if opts.ByModel {
			_, _ = fmt.Fprintf(w, "%s\t%s\t%d\t%d\t%s\t%s\t%s\t%s\t%s\t$%0.4f\n",
				r.Harness, r.Model, r.Sessions, r.Turns,
				formatTokens(r.InputTokens), formatTokens(r.OutputTokens),
				formatTokens(r.CachedTokens), formatTokens(r.ReasoningTokens),
				formatTokens(r.TotalTokens), r.CostUSD)
		} else {
			_, _ = fmt.Fprintf(w, "%s\t%d\t%d\t%s\t%s\t%s\t%s\t%s\t$%0.4f\n",
				r.Harness, r.Sessions, r.Turns,
				formatTokens(r.InputTokens), formatTokens(r.OutputTokens),
				formatTokens(r.CachedTokens), formatTokens(r.ReasoningTokens),
				formatTokens(r.TotalTokens), r.CostUSD)
		}
	}

	if opts.ByModel {
		_, _ = fmt.Fprintf(w, "TOTAL\t-\t%d\t%d\t%s\t%s\t%s\t%s\t%s\t$%0.4f\n",
			totalRow.Sessions, totalRow.Turns,
			formatTokens(totalRow.InputTokens), formatTokens(totalRow.OutputTokens),
			formatTokens(totalRow.CachedTokens), formatTokens(totalRow.ReasoningTokens),
			formatTokens(totalRow.TotalTokens), totalRow.CostUSD)
	} else {
		_, _ = fmt.Fprintf(w, "TOTAL\t%d\t%d\t%s\t%s\t%s\t%s\t%s\t$%0.4f\n",
			totalRow.Sessions, totalRow.Turns,
			formatTokens(totalRow.InputTokens), formatTokens(totalRow.OutputTokens),
			formatTokens(totalRow.CachedTokens), formatTokens(totalRow.ReasoningTokens),
			formatTokens(totalRow.TotalTokens), totalRow.CostUSD)
	}
	return w.Flush()
}

func formatTokens(n int64) string {
	in := strconv.FormatInt(n, 10)
	if len(in) <= 3 {
		return in
	}
	var out []byte
	lead := len(in) % 3
	if lead > 0 {
		out = append(out, in[:lead]...)
		if len(in) > lead {
			out = append(out, ',')
		}
	}
	for i := lead; i < len(in); i += 3 {
		out = append(out, in[i:i+3]...)
		if i+3 < len(in) {
			out = append(out, ',')
		}
	}
	return string(out)
}

// parseFlexibleTime accepts a Go duration ("24h"), a day count ("7d"), or an
// absolute date. It reports an error rather than a zero time so an unparseable
// window fails the command instead of silently widening it to all time.
func parseFlexibleTime(val string) (time.Time, error) {
	val = strings.TrimSpace(val)
	if d, err := time.ParseDuration(val); err == nil {
		return time.Now().UTC().Add(-d), nil
	}
	if strings.HasSuffix(val, "d") {
		daysStr := strings.TrimSuffix(val, "d")
		var days int
		if _, err := fmt.Sscanf(daysStr, "%d", &days); err == nil && days > 0 {
			return time.Now().UTC().AddDate(0, 0, -days), nil
		}
	}
	for _, layout := range []string{time.RFC3339, "2006-01-02", "2006-01-02T15:04:05"} {
		if t, err := time.Parse(layout, val); err == nil {
			return t.UTC(), nil
		}
	}
	return time.Time{}, fmt.Errorf("invalid time %q; use a duration (24h), a day count (7d), or a date (2006-01-02)", val)
}

// RunAgentUsageList lists individual usage records.
func RunAgentUsageList(ctx context.Context, state *GlobalState, opts UsageListOptions) error {
	records, err := LoadAllUsageRecords()
	if err != nil {
		return fmt.Errorf("failed to load usage records: %w", err)
	}

	var filtered []UsageRecord
	for _, r := range records {
		if opts.Harness != "" && r.Harness != opts.Harness && r.Agent != opts.Harness {
			continue
		}
		filtered = append(filtered, r)
	}

	sort.Slice(filtered, func(i, j int) bool {
		return filtered[i].Timestamp > filtered[j].Timestamp
	})

	if opts.Limit > 0 && len(filtered) > opts.Limit {
		filtered = filtered[:opts.Limit]
	}

	if opts.JSON {
		encoder := json.NewEncoder(state.Stdout)
		encoder.SetIndent("", "  ")
		return encoder.Encode(filtered)
	}

	if len(filtered) == 0 {
		_, _ = fmt.Fprintln(state.Stdout, "No usage records found.")
		return nil
	}

	w := tabwriter.NewWriter(state.Stdout, 0, 0, 3, ' ', 0)
	_, _ = fmt.Fprintln(w, "TIMESTAMP\tHARNESS\tSESSION ID\tMODEL\tTOTAL TOKENS\tCOST (USD)")
	for _, r := range filtered {
		ts := r.Timestamp
		if len(ts) > 19 {
			ts = ts[:19]
		}
		model := r.Model
		if model == "" {
			model = "-"
		}
		_, _ = fmt.Fprintf(w, "%s\t%s\t%s\t%s\t%s\t$%0.4f\n",
			ts, r.Harness, r.SessionID, model, formatTokens(r.TotalTokens), r.CostUSD)
	}
	return w.Flush()
}

// RunAgentUsageShow displays detailed usage for a single session.
func RunAgentUsageShow(ctx context.Context, state *GlobalState, harness, sessionID string) error {
	if harness == "" || sessionID == "" {
		return errors.New("usage: dot agent usage show <harness> <session-id>")
	}
	dir, err := HarnessUsageDir(harness)
	if err != nil {
		return err
	}
	path := filepath.Join(dir, sanitizeFilename(sessionID)+".json")
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("usage record not found for %s session %s: %w", harness, sessionID, err)
	}
	_, _ = state.Stdout.Write(data)
	return nil
}

// NewAgentUsageCmd constructs the `dot agent usage` command group.
func NewAgentUsageCmd(state *GlobalState) *cli.Command {
	statsAction := func(ctx context.Context, cmd *cli.Command) error {
		return RunAgentUsageStats(ctx, state, UsageStatsOptions{
			Harness: cmd.String("harness"),
			Since:   cmd.String("since"),
			Until:   cmd.String("until"),
			ByModel: cmd.Bool("by-model"),
			JSON:    cmd.Bool("json"),
		})
	}

	return &cli.Command{
		Name:    "usage",
		Aliases: []string{"u"},
		Usage:   "Manage and compute stats on agent token usage in ~/.agents/usages",
		Flags: []cli.Flag{
			&cli.StringFlag{Name: "harness", Aliases: []string{"a"}, Usage: "Filter by harness name (claude, codex, grok, etc.)"},
			&cli.StringFlag{Name: "since", Usage: "Filter by duration (24h, 7d) or RFC3339 timestamp"},
			&cli.StringFlag{Name: "until", Usage: "Filter up to duration or timestamp"},
			&cli.BoolFlag{Name: "by-model", Aliases: []string{"m"}, Usage: "Break down token usage by harness and model"},
			&cli.BoolFlag{Name: "json", Aliases: []string{"j"}, Usage: "Output stats as JSON"},
		},
		Action: statsAction,
		Commands: []*cli.Command{
			{
				Name:    "stats",
				Aliases: []string{"s"},
				Usage:   "Compute summary token usage statistics across harnesses",
				Flags: []cli.Flag{
					&cli.StringFlag{Name: "harness", Aliases: []string{"a"}, Usage: "Filter by harness name"},
					&cli.StringFlag{Name: "since", Usage: "Filter by start duration/timestamp"},
					&cli.StringFlag{Name: "until", Usage: "Filter by end duration/timestamp"},
					&cli.BoolFlag{Name: "by-model", Aliases: []string{"m"}, Usage: "Break down by harness and model"},
					&cli.BoolFlag{Name: "json", Aliases: []string{"j"}, Usage: "Output stats as JSON"},
				},
				Action: statsAction,
			},
			{
				Name:    "list",
				Aliases: []string{"l"},
				Usage:   "List session usage records",
				Flags: []cli.Flag{
					&cli.StringFlag{Name: "harness", Aliases: []string{"a"}, Usage: "Filter by harness name"},
					&cli.IntFlag{Name: "limit", Aliases: []string{"n"}, Value: 50, Usage: "Maximum sessions to list"},
					&cli.BoolFlag{Name: "json", Aliases: []string{"j"}, Usage: "Output list as JSON"},
				},
				Action: func(ctx context.Context, cmd *cli.Command) error {
					return RunAgentUsageList(ctx, state, UsageListOptions{
						Harness: cmd.String("harness"),
						Limit:   int(cmd.Int("limit")),
						JSON:    cmd.Bool("json"),
					})
				},
			},
			{
				Name:      "show",
				Aliases:   []string{"w"},
				Usage:     "Show detailed usage record for a session",
				ArgsUsage: "<harness> <session-id>",
				Action: func(ctx context.Context, cmd *cli.Command) error {
					return RunAgentUsageShow(ctx, state, cmd.Args().Get(0), cmd.Args().Get(1))
				},
			},
			{
				Name:    "sync",
				Aliases: []string{"y"},
				Usage:   "Backfill and synchronize usage records from raw harness stores",
				Action: func(ctx context.Context, _ *cli.Command) error {
					return RunAgentUsageSync(ctx, state)
				},
			},
		},
	}
}
