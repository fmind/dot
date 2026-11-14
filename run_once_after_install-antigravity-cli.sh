#!/usr/bin/env bash
# agy updates itself; download completely before running, and isolate HOME so
# `agy install` never appends duplicate PATH lines to managed shell profiles.
set -euo pipefail
command -v agy >/dev/null && exit 0
real_home="${HOME}"
installer="$(mktemp)"
scratch="$(mktemp -d)"
trap 'rm -rf "${installer}" "${scratch}"' EXIT
curl -fsSL --proto '=https' --tlsv1.2 -o "${installer}" https://antigravity.google/cli/install.sh
HOME="${scratch}" bash "${installer}" --dir "${real_home}/.local/bin"
