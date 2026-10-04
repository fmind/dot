#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${HOME}/.local/share/mise/bin:${HOME}/.local/share/mise/shims:${PATH}"
SOURCE_DIR="${HOME}/.local/share/chezmoi"
# The mise release that CI tests, installed when mise is absent. mise.toml's
# min_version rejects an older existing installation. Keep equal to the workflow pins.
MINIMUM_MISE_VERSION="2026.10.2"

# Install mise
command -v mise >/dev/null || {
  echo "=> Installing mise..."
  # Execute only a complete transfer. The installer honors MISE_VERSION and
  # verifies the release checksum, but cannot detect its own truncated download.
  mise_installer="$(mktemp)"
  trap 'rm -f "${mise_installer}"' EXIT
  curl -fsSL --proto '=https' --tlsv1.2 -o "${mise_installer}" https://mise.run
  MISE_VERSION="v${MINIMUM_MISE_VERSION}" bash "${mise_installer}"
}

# Install chezmoi
command -v chezmoi >/dev/null || {
  echo "=> Installing chezmoi..."
  mise use --global --yes chezmoi@latest
}

# Install dot
echo "=> Installing dot..."
if [ ! -d "${SOURCE_DIR}" ]; then
  chezmoi init --force https://github.com/fmind/dot.git --source "${SOURCE_DIR}" "$@"
else
  echo "=> Updating dot repository..."
  if [ "${SKIP_GIT_PULL:-}" = "true" ] || [ "${CI:-}" = "true" ]; then
    echo "=> Skipping git pull as requested by environment variable."
  else
    git -C "${SOURCE_DIR}" pull --ff-only
  fi
  chezmoi init --force --source "${SOURCE_DIR}" "$@"
fi

# All repository tasks are owned by this config, including calls from dot/.
echo "=> Trusting mise config..."
mise trust -y "${SOURCE_DIR}/mise.toml"

# Complete the ordered bootstrap: trust, tools (install, apply, deploy), hooks, and editor.
echo "=> Completing environment bootstrap..."
mise -C "${SOURCE_DIR}" run install

echo "=> Install complete! You are ready to go."
