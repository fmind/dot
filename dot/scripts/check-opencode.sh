#!/usr/bin/env bash
set -euo pipefail

package=dot/testdata/opencode
pnpm --dir "${package}" install --frozen-lockfile --ignore-scripts
pnpm --dir "${package}" exec tsc --project tsconfig.json
biome check
