package dot

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Exercise the deployed session + usage hook pair on a changed transcript. Unique
// session IDs prevent stored-generation reuse from hiding the parsing cost.
func BenchmarkTranscriptHooks(b *testing.B) {
	for _, harness := range []string{sessionStoreClaude, sessionStoreCodex} {
		b.Run(harness, func(b *testing.B) {
			home := b.TempDir()
			b.Setenv("HOME", home)
			transcript := filepath.Join(home, "transcript.jsonl")
			body := strings.Repeat("synthetic benchmark content ", 40)
			var content strings.Builder
			for range 2000 {
				if harness == sessionStoreClaude {
					fmt.Fprintf(&content, `{"timestamp":"2026-09-05T10:00:00Z","type":"assistant","message":{"model":"benchmark","content":[{"type":"text","text":%q}],"usage":{"input_tokens":100,"output_tokens":10}}}`+"\n", body)
				} else {
					fmt.Fprintf(&content, `{"timestamp":"2026-09-05T10:00:00Z","type":"response_item","payload":{"role":"assistant","content":[{"type":"output_text","text":%q}]}}`+"\n", body)
					content.WriteString(`{"timestamp":"2026-09-05T10:00:00Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":100,"output_tokens":10,"total_tokens":110}}}}` + "\n")
				}
			}
			if err := os.WriteFile(transcript, []byte(content.String()), 0o600); err != nil {
				b.Fatal(err)
			}
			state := newTestState(&FakeRunner{})
			state.Stdout, state.Stderr = io.Discard, io.Discard
			b.SetBytes(int64(content.Len()))
			b.ReportAllocs()
			b.ResetTimer()
			for i := range b.N {
				input := fmt.Sprintf(`{"session_id":"benchmark-%d","cwd":%q,"transcript_path":%q}`, i, home, transcript)
				state.Stdin = strings.NewReader(input)
				if err := RunAgentHookSession(context.Background(), state, harness, "", ""); err != nil {
					b.Fatal(err)
				}
				state.Stdin = strings.NewReader(input)
				if err := RunAgentHookUsage(context.Background(), state, harness, "", ""); err != nil {
					b.Fatal(err)
				}
			}
		})
	}
}
