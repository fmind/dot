#!/usr/bin/env bash
# agy updates itself; the installer is downloaded completely before it runs, so a
# truncated transfer cannot execute half a script.
set -euo pipefail
command -v agy >/dev/null && exit 0
installer="$(mktemp)"
trap 'rm -f "${installer}"' EXIT
curl -fsSL --proto '=https' --tlsv1.2 -o "${installer}" https://antigravity.google/cli/install.sh
bash "${installer}"
