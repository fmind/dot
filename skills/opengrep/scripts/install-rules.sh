#!/usr/bin/env bash
set -euo pipefail

rules_revision=${1:?Usage: install-rules.sh <commit> [directory] [repository]}
rules_directory=${2:-.opengrep/rules}
rules_repository=${3:-https://github.com/opengrep/opengrep-rules}

if [[ ! ${rules_revision} =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Expected a full lowercase commit SHA for the rules pin\n' >&2
  exit 1
fi

# An empty or interrupted initialization must be repairable on the next run.
if [[ ! -e "${rules_directory}/.git" ]]; then
  git init -q "${rules_directory}"
fi
rules_status=$(git -C "${rules_directory}" status --porcelain)
if [[ -n ${rules_status} ]]; then
  printf 'Rules checkout has local changes; preserve them before changing the pin\n' >&2
  exit 1
fi

if ! git -C "${rules_directory}" cat-file -e "${rules_revision}^{commit}" 2>/dev/null; then
  git -C "${rules_directory}" fetch -q --depth 1 "${rules_repository}" "${rules_revision}"
fi
git -C "${rules_directory}" checkout -q --no-overwrite-ignore --detach "${rules_revision}"
rules_head=$(git -C "${rules_directory}" rev-parse HEAD)
test "${rules_head}" = "${rules_revision}"
