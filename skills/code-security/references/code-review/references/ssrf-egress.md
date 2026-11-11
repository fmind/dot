# SSRF-Safe Outbound HTTP Egress

URL string parsing (`urllib.parse.urlsplit`) never prevents Server-Side Request Forgery (SSRF): attackers bypass string allowlists/denylists via DNS rebinding (TTL `0` flipping from a public IP to `169.254.169.254` or `127.0.0.1`), HTTP `30x` redirects, IPv4-mapped IPv6 (`::ffff:169.254.169.254`), decimal/octal IP literals, or ambient `HTTP_PROXY` variables.

## Controls for Untrusted or User-Influenced URLs

1. **Validate scheme, port, and hostname upfront**: allow only `https` on port `443` (unless an explicit contract requires another port), reject userinfo (`user:pass@host`), and prefer an exact hostname allowlist when destinations are known.
1. **Disable ambient proxies and automatic redirects**: set `trust_env=False` and `follow_redirects=False` on `httpx2` / `httpx` clients ([api-client](../../../../python-stack/references/api-client/GUIDE.md)). If redirects are required, re-validate every `Location` hop against the full policy with a low hop cap (`≤3`).
1. **Reject non-global IPs across all DNS answers**: resolve `socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)` and verify **every** returned address is globally routable (unpacking `ip.ipv4_mapped` on `IPv6Address` first):

   ```python
   import ipaddress
   import socket

   _SHARED_SPACE = ipaddress.ip_network("100.64.0.0/10")  # RFC 6598 CGNAT / cloud internal ranges


   def assert_public_ip(raw_ip: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
       ip = ipaddress.ip_address(raw_ip)
       if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
           ip = ip.ipv4_mapped
       if not ip.is_global or ip in _SHARED_SPACE or ip.is_multicast:
           msg = f"Refused non-public egress address: {ip}"
           raise ValueError(msg)
       return ip


   def resolve_public_ips(host: str, port: int = 443) -> list[str]:
       infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
       if not infos:
           msg = f"No DNS records for {host}"
           raise ValueError(msg)
       return [str(assert_public_ip(info[4][0])) for info in infos]
   ```

1. **Bind validation to the actual socket connection (anti-rebinding)**: never call `resolve_public_ips()` and then let the HTTP client re-resolve DNS independently. Either connect via a custom `httpcore.AsyncNetworkBackend` / socket hook that resolves once and dials the validated IP while preserving TLS `sni_hostname=host`, `Host: <host>`, and explicit `context.minimum_version = ssl.TLSVersion.TLSv1_2`, or route untrusted fetches through a dedicated egress proxy that blocks RFC 1918, loopback, link-local (`169.254.0.0/16`, `fe80::/10`), CGNAT (`100.64.0.0/10`), and cloud metadata (`169.254.169.254`, `fd00:ec2::254`) at L3/L4.
1. **Bound time and bytes**: enforce short connect/read timeouts, stream responses with a hard byte ceiling before decoding, and strip credentials/headers on any cross-origin call.
