#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_SHA:?GITHUB_SHA is required}"
: "${GITHUB_REF_NAME:?GITHUB_REF_NAME is required}"

tag_sha="$(git rev-parse "${GITHUB_REF_NAME}^{commit}")"
if [[ ${tag_sha} != "${GITHUB_SHA}" ]]; then
  echo "tag ${GITHUB_REF_NAME} resolves to ${tag_sha}, not checked-out SHA ${GITHUB_SHA}" >&2
  exit 1
fi

attempts="${RELEASE_GATE_ATTEMPTS:-80}"
interval="${RELEASE_GATE_INTERVAL_SECONDS:-15}"
for ((attempt = 1; attempt <= attempts; attempt++)); do
  runs="$(gh run list --workflow ci.yml --commit "${GITHUB_SHA}" --limit 20 --json databaseId,headSha,status,conclusion,workflowName,createdAt)"
  record="$(jq -c --arg sha "${GITHUB_SHA}" '[.[] | select(.headSha == $sha and .workflowName == "CI")] | sort_by(.createdAt) | reverse | .[0] // empty' <<<"${runs}")"
  if [[ -n ${record} ]]; then
    status="$(jq -r '.status' <<<"${record}")"
    conclusion="$(jq -r '.conclusion // ""' <<<"${record}")"
    if [[ ${status} == "completed" ]]; then
      if [[ ${conclusion} == "success" ]]; then
        exit 0
      fi
      echo "CI for ${GITHUB_SHA} completed with conclusion ${conclusion:-unknown}" >&2
      exit 1
    fi
  fi
  if ((attempt < attempts)); then
    sleep "${interval}"
  fi
done

echo "no successful completed ci.yml run appeared for ${GITHUB_SHA} within the release gate" >&2
exit 1
