package dot

import (
	"context"
	"io"
	"os"
	"path/filepath"
	"testing"
)

func TestSQLiteSourceQueryDoesNotCreateDatabase(t *testing.T) {
	path := filepath.Join(t.TempDir(), "missing.db")
	state := newTestState(NewStandardRunner(nil, io.Discard, io.Discard))
	if _, err := runSQLiteJSON(context.Background(), state, path, "SELECT 1;"); err == nil {
		t.Fatal("query of a missing source database must fail")
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("source query created a database: %v", err)
	}
}
