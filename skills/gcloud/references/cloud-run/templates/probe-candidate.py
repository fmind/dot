"""Verify a Cloud Run candidate URL on /health and /ready using an invoker ID token."""

from __future__ import annotations

import argparse
import contextlib
import http.client
import re
import shutil
import ssl
import subprocess
import sys
from collections.abc import Callable
from urllib.parse import urlsplit

CANDIDATE_URL_PATTERN = re.compile(r"^https://[a-z0-9.-]+$")
REQUEST_TIMEOUT_SECONDS = 10


def validate_candidate_url(url: str) -> str:
    """Validate that the candidate URL is a bare HTTPS Cloud Run origin without paths or userinfo."""
    if not CANDIDATE_URL_PATTERN.fullmatch(url):
        raise ValueError("Candidate URL must match ^https://[a-z0-9.-]+$")
    return url


def fetch_identity_token(audience: str) -> str:
    """Request an OpenID Connect identity token for the candidate audience via gcloud."""
    gcloud = shutil.which("gcloud")
    if gcloud is None:
        raise RuntimeError("gcloud executable not found on PATH")
    result = subprocess.run(  # noqa: S603 - fixed gcloud binary and regex-validated HTTPS audience URL
        [gcloud, "auth", "print-identity-token", f"--audiences={audience}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    token = result.stdout.strip()
    if result.returncode != 0 or not token or any(ch.isspace() for ch in token):
        raise RuntimeError("Failed to obtain an identity token from gcloud")
    return token


def probe_endpoint(
    host: str,
    path: str,
    token: str,
    *,
    connection_factory: Callable[..., http.client.HTTPSConnection] = http.client.HTTPSConnection,
) -> int:
    """Send one non-redirecting HTTPS GET request with a bearer token and return the status code."""
    conn = connection_factory(host, timeout=REQUEST_TIMEOUT_SECONDS, context=ssl.create_default_context())
    try:
        conn.request("GET", path, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        with contextlib.suppress(OSError):
            conn.close()


def probe_candidate(
    url: str,
    *,
    token_fetcher: Callable[[str], str] = fetch_identity_token,
    connection_factory: Callable[..., http.client.HTTPSConnection] = http.client.HTTPSConnection,
) -> None:
    """Verify both /health and /ready return HTTP 200 without following redirects."""
    origin = validate_candidate_url(url)
    host = urlsplit(origin).netloc
    token = token_fetcher(origin)
    for route in ("/health", "/ready"):
        status = probe_endpoint(host, route, token, connection_factory=connection_factory)
        if status != 200:
            raise RuntimeError(f"Candidate route {route} returned HTTP {status}")


def main() -> int:
    """Run candidate verification from the command line."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("url", help="Candidate Cloud Run tag URL (https://<tag>---<service>-<hash>.a.run.app)")
    args = parser.parse_args()
    try:
        probe_candidate(args.url)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        sys.stderr.write(f"Error: {error}\n")
        return 1
    sys.stdout.write("Candidate /health and /ready probes returned HTTP 200.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
