#!/usr/bin/env bash
# agy updates itself; download completely before running, and isolate HOME so
# `agy install` never appends duplicate PATH lines to managed shell profiles.
set -euo pipefail
command -v agy >/dev/null && exit 0
real_home="${HOME}"
installer=""
scratch=""
cleanup() {
  if [ -n "${installer}" ]; then rm -f -- "${installer}"; fi
  if [ -n "${scratch}" ]; then rm -rf -- "${scratch}"; fi
}
trap cleanup EXIT
trap 'cleanup; trap - INT; kill -INT $$' INT
trap 'cleanup; trap - TERM; kill -TERM $$' TERM
installer="$(mktemp)"
scratch="$(mktemp -d)"
curl -fsSL --proto '=https' --tlsv1.2 --connect-timeout 15 --max-time 120 -o "${installer}" https://antigravity.google/cli/install.sh
HOME="${scratch}" bash "${installer}" --dir "${real_home}/.local/bin"
