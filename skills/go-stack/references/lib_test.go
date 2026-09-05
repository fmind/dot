package <package>

import (
	"context"
	"log/slog"
	"testing"
)

func TestClientDoSomething(t *testing.T) {
	logger := slog.New(slog.DiscardHandler)
	client := NewClient(logger)

	err := client.DoSomething(context.Background())
	if err != nil {
		t.Fatalf("Expected no error, got %v", err)
	}
}
