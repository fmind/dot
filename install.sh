#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${HOME}/.local/share/mise/bin:${HOME}/.local/share/mise/shims:${PATH}"
SOURCE_DIR="${HOME}/.local/share/chezmoi"
# The mise release that CI tests, installed when mise is absent. mise.toml's
# min_version rejects an older existing installation. Keep equal to the workflow pins.
MINIMUM_MISE_VERSION="2026.11.12"

# Install mise
command -v mise >/dev/null || {
  echo "=> Installing mise..."
  # Execute only a complete transfer. The installer honors MISE_VERSION and
  # verifies the release checksum, but cannot detect its own truncated download.
  mise_installer=""
  cleanup_mise() {
    if [ -n "${mise_installer}" ]; then rm -f -- "${mise_installer}"; fi
  }
  trap cleanup_mise EXIT
  trap 'cleanup_mise; trap - INT; kill -INT $$' INT
  trap 'cleanup_mise; trap - TERM; kill -TERM $$' TERM
  mise_installer="$(mktemp)"
  curl -fsSL --proto '=https' --tlsv1.2 -o "${mise_installer}" https://mise.run
  MISE_VERSION="v${MINIMUM_MISE_VERSION}" bash "${mise_installer}"
}

# Clone or update dot repository
if [ ! -d "${SOURCE_DIR}" ]; then
  echo "=> Cloning dot repository..."
  git clone https://github.com/fmind/dot.git "${SOURCE_DIR}"
else
  echo "=> Updating dot repository..."
  if [ "${SKIP_GIT_PULL:-}" = "true" ]; then
    echo "=> Skipping git pull as requested by environment variable."
  else
    git -C "${SOURCE_DIR}" pull --ff-only
  fi
fi

# All repository tasks are owned by this config, including calls from dot/.
echo "=> Trusting mise config..."
mise trust -y "${SOURCE_DIR}/mise.toml"

# Initialize chezmoi using the repository-locked release when chezmoi is absent.
echo "=> Initializing dot..."
if command -v chezmoi >/dev/null; then
  chezmoi init --force --source "${SOURCE_DIR}" "$@"
else
  echo "=> Installing locked chezmoi..."
  MISE_IGNORED_CONFIG_PATHS="${MISE_CONFIG_DIR:-${XDG_CONFIG_HOME:-${HOME}/.config}/mise}" \
    mise -C "${SOURCE_DIR}" --locked install -y chezmoi
  chezmoi_bin="$(
    MISE_IGNORED_CONFIG_PATHS="${MISE_CONFIG_DIR:-${XDG_CONFIG_HOME:-${HOME}/.config}/mise}" \
      mise -C "${SOURCE_DIR}" which chezmoi
  )"
  "${chezmoi_bin}" init --force --source "${SOURCE_DIR}" "$@"
fi

# Complete the ordered bootstrap: full (install, apply, deploy), hooks, and editor.
echo "=> Completing environment bootstrap..."
mise -C "${SOURCE_DIR}" run install

echo "=> Install complete! You are ready to go."
