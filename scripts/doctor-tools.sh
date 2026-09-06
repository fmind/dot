#!/usr/bin/env bash
set -euo pipefail

status=0
output="$(mise prune --dry-run 2>&1)" || status=$?
if ((status)); then
  printf "%s\n" "${output}" >&2
  exit "${status}"
fi

orphans="$(grep "no tracked config or tool stub requires" <<<"${output}" || true)"
if [[ -n ${orphans} ]]; then
  printf "%s\n" "${orphans}"
  printf "Untracked tools installed above: declare them in mise, or run 'mise prune'.\n" >&2
  exit 1
fi
