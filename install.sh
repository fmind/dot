#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${HOME}/.local/share/mise/bin:${HOME}/.local/share/mise/shims:${PATH}"
SOURCE_DIR="${HOME}/.local/share/chezmoi"
MINIMUM_MISE_VERSION="2026.9.1"

version_at_least() {
  local actual=$1 minimum=$2 actual_part minimum_part
  local IFS=.
  read -r -a actual_parts <<<"${actual}"
  read -r -a minimum_parts <<<"${minimum}"
  for index in 0 1 2; do
    actual_part=${actual_parts[${index}]:-0}
    minimum_part=${minimum_parts[${index}]:-0}
    ((10#${actual_part} > 10#${minimum_part})) && return 0
    ((10#${actual_part} < 10#${minimum_part})) && return 1
  done
  return 0
}

# Error trap handler for clean bootstrapping diagnostics
on_error() {
  local exit_code=$?
  echo "==================================================" >&2
  echo "  ✗ Error: install.sh failed at line $1 with exit code ${exit_code}." >&2
  echo "==================================================" >&2
  echo "  Please check the following bootstrap prerequisites:" >&2
  echo "  1. Ensure you have active internet connectivity." >&2
  echo "  2. Confirm both git and curl are installed on your host." >&2
  echo "  3. On Linux: verify 'build-essential' and 'gnome-keyring' are installed." >&2
  echo "  4. Check that ~/.local/bin is writeable by your current user." >&2
  echo "==================================================" >&2
}
trap 'on_error $LINENO' ERR

# Install mise
command -v mise >/dev/null || {
  echo "=> Installing mise..."
  curl -fsSL https://mise.run | bash
}

mise_version="$(mise --version | awk '{print $1}')"
if [[ ! ${mise_version} =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || ! version_at_least "${mise_version}" "${MINIMUM_MISE_VERSION}"; then
  echo "mise ${MINIMUM_MISE_VERSION} or newer is required; found ${mise_version:-unknown}. Upgrade mise before bootstrapping." >&2
  exit 1
fi

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

# Trust every reviewed config in the checkout before a task can load it. Trust is
# per file, so the nested Go module config needs its own grant: without it the
# first `mise -C dot ...` of the bootstrap stops on an untrusted config.
echo "=> Trusting mise configs..."
mise trust -y "${SOURCE_DIR}/mise.toml"
mise trust -y "${SOURCE_DIR}/dot/mise.toml"

# Complete the ordered bootstrap: apply, trust, tools, hooks, and editor.
echo "=> Completing environment bootstrap..."
mise -C "${SOURCE_DIR}" run install

echo "=> Install complete! You are ready to go."
