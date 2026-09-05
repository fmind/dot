package <slug>

import (
	"context"
	"log/slog"
)

// Client is the entry point for the library business logic.
type Client struct {
	logger *slog.Logger
}

// NewClient initializes a new Client.
func NewClient(logger *slog.Logger) *Client {
	return &Client{logger: logger}
}

// DoSomething executes the library business logic.
func (c *Client) DoSomething(ctx context.Context) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	c.logger.InfoContext(ctx, "doing something in library")
	return nil
}
