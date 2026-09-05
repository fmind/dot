#!/usr/bin/env bash
set -euo pipefail

if (($# == 0)); then set -- dot_config/nvim; fi
stylua "$@"
