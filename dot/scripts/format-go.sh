#!/usr/bin/env bash
set -euo pipefail

if (($# == 0)); then set -- dot; fi
go tool goimports -local dot -w "$@"
go tool gofumpt -extra -w "$@"
