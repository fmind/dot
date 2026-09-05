#!/usr/bin/env bash
set -euo pipefail

if (($# == 0)); then set -- .; fi
ruff check --select=I --fix "$@"
ruff format "$@"
