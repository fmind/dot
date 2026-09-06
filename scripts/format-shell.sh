#!/usr/bin/env bash
set -euo pipefail

if (($#)); then
  exec shfmt -w -i 2 -s "$@"
fi

# Materialize the list so a failed git command cannot silently skip checks.
file_list="$(mktemp)"
trap 'rm -f "${file_list}"' EXIT
git ls-files --cached --others --exclude-standard -z "*.sh" >"${file_list}"
files=()
while IFS= read -r -d "" file; do
  if [[ -e ${file} || -L ${file} ]]; then files+=("${file}"); fi
done <"${file_list}"
if ((${#files[@]})); then shfmt -w -i 2 -s "${files[@]}"; fi
