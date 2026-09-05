# Provenance Pilot

Pilot date: 2026-09-05 with mise 2026.9.1 on Linux x86_64.

Current mise can verify SLSA, Cosign, Minisign, and GitHub artifact attestations for supported aqua and GitHub artifacts, and records a verified provenance type in `mise.lock`. Cross-platform records are metadata detection rather than native verification; `github_attestations = "unavailable"` is a negative cache entry, not provenance.

An isolated install of `aqua:BurntSushi/ripgrep@15.2.0` with all four aqua verification mechanisms enabled completed using only the GitHub API digest checksum. It recorded no verified provenance and therefore does not justify a policy change. Native macOS verification and a negative invalid-identity fixture were unavailable in this session.

Keep the existing disabled global policy until a candidate provides a verified signer or workflow identity on both supported native platforms. Do not enable a global switch based on a successful checksum-only download.
