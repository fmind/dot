#!/usr/bin/env bash
set -euo pipefail

# Materialize the list so a failed git command cannot silently skip checks.
file_list="$(mktemp)"
trap 'rm -f "${file_list}"' EXIT
git ls-files -z "dot_config/fish/**/*.fish" "dot_config/fish/*.fish" >"${file_list}"
while IFS= read -r -d "" file; do
  fish --no-config --no-execute "${file}"
done <"${file_list}"
