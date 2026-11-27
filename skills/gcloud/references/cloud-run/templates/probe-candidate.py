"""Verify a Cloud Run candidate URL on /health and /ready using an invoker ID token."""

from __future__ import annotations

import argparse
import contextlib
import http.client
import ipaddress
import re
import shutil
import socket
import ssl
import subprocess
import sys
from collections.abc import Callable
from urllib.parse import urlsplit

_DNS_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
CANDIDATE_URL_PATTERN = re.compile(rf"^https://(?:{_DNS_LABEL}\.)+run\.app$")
CUSTOM_DOMAIN_URL_PATTERN = re.compile(rf"^https://(?:{_DNS_LABEL}\.)+[a-z]{{2,63}}$")
_FORBIDDEN_SUFFIXES = (".internal", ".local", ".localhost", ".arpa", ".home", ".lan")
_CGNAT_NET = ipaddress.ip_network("100.64.0.0/10")
MAX_HOSTNAME_LENGTH = 253
MAX_RESPONSE_BYTES = 65_536
REQUEST_TIMEOUT_SECONDS = 10


def validate_candidate_url(url: str, *, allow_custom_domain: bool = False) -> str:
    """Validate that the candidate URL is a bare HTTPS Cloud Run (or allowed custom domain) origin."""
    pattern = CUSTOM_DOMAIN_URL_PATTERN if allow_custom_domain else CANDIDATE_URL_PATTERN
    host = urlsplit(url).netloc
    if (
        not pattern.fullmatch(url)
        or len(host) > MAX_HOSTNAME_LENGTH
        or any(host.endswith(suffix) for suffix in _FORBIDDEN_SUFFIXES)
    ):
        expected = "a valid public HTTPS hostname origin" if allow_custom_domain else "a bare HTTPS *.run.app origin"
        msg = f"Candidate URL must be {expected}"
        raise ValueError(msg)
    return url


def _assert_public_ip(raw_ip: str) -> str:
    addr = ipaddress.ip_address(raw_ip.split("%", 1)[0])
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    if (
        not addr.is_global
        or addr.is_multicast
        or addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_unspecified
        or (isinstance(addr, ipaddress.IPv4Address) and addr in _CGNAT_NET)
    ):
        msg = f"Candidate host resolved to non-public IP address: {addr}"
        raise ValueError(msg)
    return str(addr)


def resolve_public_ip(host: str) -> str:
    """Resolve host once and reject any non-public IP address (anti-SSRF / anti-rebinding)."""
    infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not infos:
        msg = f"Candidate host did not resolve: {host}"
        raise ValueError(msg)
    public_ips = [_assert_public_ip(str(info[4][0])) for info in infos]
    return public_ips[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection pinned to a pre-validated IP address while verifying TLS against hostname."""

    def __init__(self, hostname: str, pinned_ip: str, *, timeout: float, context: ssl.SSLContext) -> None:
        super().__init__(hostname, 443, timeout=timeout, context=context)
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def fetch_identity_token(audience: str) -> str:
    """Request an OpenID Connect identity token for the candidate audience via gcloud."""
    gcloud = shutil.which("gcloud")
    if gcloud is None:
        raise RuntimeError("gcloud executable not found on PATH")
    result = subprocess.run(  # noqa: S603 - fixed gcloud binary and regex-validated HTTPS audience URL
        [gcloud, "auth", "print-identity-token", f"--audiences={audience}"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    token = result.stdout.strip()
    if result.returncode != 0 or not token or any(ch.isspace() for ch in token):
        raise RuntimeError("Failed to obtain an identity token from gcloud")
    return token


def _drain_response(response: http.client.HTTPResponse) -> None:
    try:
        response.read(MAX_RESPONSE_BYTES)
    except TypeError:
        response.read()


def probe_endpoint(
    host: str,
    path: str,
    token: str | None,
    *,
    pinned_ip: str | None = None,
    connection_factory: Callable[..., http.client.HTTPSConnection] = http.client.HTTPSConnection,
) -> int:
    """Send one non-redirecting HTTPS GET request (optional bearer token) and return the status code."""
    headers = {"Accept": "application/json", "Host": host}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    ctx = ssl.create_default_context()
    if connection_factory is http.client.HTTPSConnection and pinned_ip is not None:
        conn: http.client.HTTPSConnection = _PinnedHTTPSConnection(
            host, pinned_ip, timeout=REQUEST_TIMEOUT_SECONDS, context=ctx
        )
    else:
        conn = connection_factory(host, timeout=REQUEST_TIMEOUT_SECONDS, context=ctx)
    try:
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        _drain_response(response)
        return response.status
    finally:
        with contextlib.suppress(OSError):
            conn.close()


def probe_candidate(
    url: str,
    *,
    check_unauth: bool = False,
    allow_custom_domain: bool = False,
    token_fetcher: Callable[[str], str] = fetch_identity_token,
    connection_factory: Callable[..., http.client.HTTPSConnection] = http.client.HTTPSConnection,
) -> None:
    """Verify optional unauthenticated 401/403 rejection plus authenticated /health and /ready HTTP 200."""
    origin = validate_candidate_url(url, allow_custom_domain=allow_custom_domain)
    host = urlsplit(origin).netloc
    pinned_ip = resolve_public_ip(host) if connection_factory is http.client.HTTPSConnection else None
    if check_unauth:
        for route in ("/health", "/ready"):
            unauth_status = probe_endpoint(
                host, route, None, pinned_ip=pinned_ip, connection_factory=connection_factory
            )
            if unauth_status not in (401, 403):
                msg = f"Unauthenticated {route} returned HTTP {unauth_status}; expected 401 or 403"
                raise RuntimeError(msg)
    token = token_fetcher(origin)
    for route in ("/health", "/ready"):
        status = probe_endpoint(host, route, token, pinned_ip=pinned_ip, connection_factory=connection_factory)
        if status != 200:
            msg = f"Candidate route {route} returned HTTP {status}"
            raise RuntimeError(msg)


def main() -> int:
    """Run candidate verification from the command line."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True
    parser.add_argument("url", help="Candidate Cloud Run tag URL (https://<tag>---<service>-<hash>.a.run.app)")
    parser.add_argument(
        "--check-unauth",
        action="store_true",
        help="Assert unauthenticated GET /health and /ready return HTTP 401 or 403 before authenticated probes",
    )
    parser.add_argument(
        "--allow-custom-domain",
        action="store_true",
        help="Allow a verified public non-.run.app HTTPS hostname",
    )
    args = parser.parse_args()
    try:
        probe_candidate(args.url, check_unauth=args.check_unauth, allow_custom_domain=args.allow_custom_domain)
    except (OSError, ValueError, RuntimeError, http.client.HTTPException, subprocess.SubprocessError) as error:
        sys.stderr.write(f"Error: {error}\n")
        return 1
    if args.check_unauth:
        sys.stdout.write(
            "Unauthenticated /health and /ready rejected (401/403); candidate /health and /ready returned HTTP 200.\n"
        )
    else:
        sys.stdout.write("Candidate /health and /ready probes returned HTTP 200.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
