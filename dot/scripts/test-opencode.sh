#!/usr/bin/env bash
set -euo pipefail

# A fresh checkout can run tests directly, before the separate check task.
dot/scripts/check-opencode.sh
pnpm --dir dot/testdata/opencode exec vitest run
