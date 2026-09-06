#!/usr/bin/env bash
set -euo pipefail

output="${1:-}"
if [[ -z ${output} ]]; then
  echo "usage: mise run report:vuln -- OUTPUT.json" >&2
  exit 2
fi
output_dir="$(dirname "${output}")"
umask 077
mkdir -p "${output_dir}"
trivy --config trivy.yaml fs \
  --scanners vuln \
  --ignore-unfixed=false \
  --exit-code 0 \
  --format json \
  --output "${output}" \
  --tf-vars skills/terraform-stack/references/terraform.example.tfvars \
  .
