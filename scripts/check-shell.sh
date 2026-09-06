#!/usr/bin/env bash
set -euo pipefail

# Materialize the list so a failed git command cannot silently skip checks.
file_list="$(mktemp)"
trap 'rm -f "${file_list}"' EXIT
git ls-files --cached --others --exclude-standard -z "*.sh" >"${file_list}"
files=()
while IFS= read -r -d "" file; do
  # Review the working tree, including additions and deletions before staging.
  if [[ -e ${file} || -L ${file} ]]; then files+=("${file}"); fi
done <"${file_list}"
if ((${#files[@]})); then
  shellcheck --rcfile dot_config/shellcheckrc "${files[@]}"
  shfmt -d -i 2 -s "${files[@]}"
fi

git ls-files --cached --others --exclude-standard -z "*.sh.tmpl" >"${file_list}"
while IFS= read -r -d "" template; do
  if [[ ! -e ${template} && ! -L ${template} ]]; then continue; fi
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
