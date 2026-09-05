#!/usr/bin/env bash
set -euo pipefail

# Materialize the list so a failed git command cannot silently skip checks.
file_list="$(mktemp)"
trap 'rm -f "${file_list}"' EXIT
git ls-files -z "*.sh" >"${file_list}"
files=()
while IFS= read -r -d "" file; do files+=("${file}"); done <"${file_list}"
if ((${#files[@]})); then
  shellcheck --rcfile dot_config/shellcheckrc "${files[@]}"
  shfmt -d -i 2 -s "${files[@]}"
fi

git ls-files -z "*.sh.tmpl" >"${file_list}"
while IFS= read -r -d "" template; do
  printf "In %s:\n" "${template}"
  rendered="$(chezmoi execute-template --file "${template}")"
  shellcheck --rcfile dot_config/shellcheckrc --external-sources --shell=bash - <<<"${rendered}"
  shfmt -d -i 2 -s - <<<"${rendered}"
done <"${file_list}"

for modifier in modify_dot_bashrc modify_dot_profile; do
  printf "In %s:\n" "${modifier}"
  rendered="$(printf "%s\n" "# existing shell configuration" | chezmoi execute-template --with-stdin --file "${modifier}")"
  shellcheck --rcfile dot_config/shellcheckrc --external-sources --shell=bash - <<<"${rendered}"
  shfmt -d -i 2 -s - <<<"${rendered}"
done
