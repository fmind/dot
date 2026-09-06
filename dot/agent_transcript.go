package dot

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"time"
)

func stringValue(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func mapValue(v any) map[string]any {
	if m, ok := v.(map[string]any); ok {
		return m
	}
	return nil
}

func sourceDirectoryExists(path, source string) (bool, error) {
	info, err := os.Stat(path)
	if errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("failed to inspect %s session directory %s: %w", source, path, err)
	}
	if !info.IsDir() {
		return false, fmt.Errorf("%s session path is not a directory: %s", source, path)
	}
	return true, nil
}

func findSessionFile(root string, matches func(path string, entry fs.DirEntry) bool) (string, error) {
	var found string
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if !entry.IsDir() && matches(path, entry) {
			found = path
			return filepath.SkipAll
		}
		return nil
	})
	if errors.Is(err, os.ErrNotExist) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	return found, nil
}

type jsonlDecodeStats struct {
	Decoded   int
	Malformed int
}

// decodeJSONLWithStats reads line-delimited JSON and retains malformed-record
// evidence so the normalized generation is marked partial instead of silently clean.
func decodeJSONLWithStats(warnOut io.Writer, filePath string, file *os.File, callback func(raw map[string]any) error) (jsonlDecodeStats, error) {
	var stats jsonlDecodeStats
	reader := bufio.NewReader(file)
	for {
		line, err := reader.ReadString('\n')
		if err != nil && !errors.Is(err, io.EOF) {
			return stats, fmt.Errorf("reading file %s: %w", filePath, err)
		}
		if len(line) > 0 {
			var raw map[string]any
			if decodeErr := json.Unmarshal([]byte(line), &raw); decodeErr != nil {
				stats.Malformed++
				if warnOut != nil {
					_, _ = fmt.Fprintf(warnOut, "warning: failed to decode JSON line in %s: %v\n", filePath, decodeErr)
				}
			} else {
				stats.Decoded++
				if cbErr := callback(raw); cbErr != nil {
					return stats, cbErr
				}
			}
		}
		if errors.Is(err, io.EOF) {
			break
		}
	}
	return stats, nil
}

func finalizeTranscriptUsage(rec *UsageRecord) *UsageRecord {
	if rec.Harness == sessionStoreClaude || rec.TotalTokens == 0 && (rec.InputTokens > 0 || rec.OutputTokens > 0) {
		rec.TotalTokens = rec.InputTokens + rec.OutputTokens + rec.CachedTokens + rec.CacheWriteTokens
	}
	if rec.Timestamp == "" {
		rec.Timestamp = time.Now().UTC().Format(time.RFC3339)
	}
	return rec
}

func readTranscriptUsage(path string, rec *UsageRecord, observe func(*UsageRecord, map[string]any)) (*UsageRecord, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer func() { _ = file.Close() }()
	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 1024*1024), 16*1024*1024)
	for scanner.Scan() {
		var raw map[string]any
		if err := json.Unmarshal(scanner.Bytes(), &raw); err != nil {
			continue
		}
		observe(rec, raw)
	}
	return finalizeTranscriptUsage(rec), scanner.Err()
}
