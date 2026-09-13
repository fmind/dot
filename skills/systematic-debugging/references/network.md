# Network Troubleshooting

Apply [systematic-debugging](../SKILL.md) at the failing network boundary. Use the application's actual host, port, resolver, proxy, runtime, and identity; a successful command from another environment is a comparator, not proof of application health.

## Workflow

1. Record the failing operation, sanitized endpoint, exact error, timestamp, runtime/tool versions, and one working comparator. Inspect whether proxy variables and custom CA settings are present without printing credential-bearing values. Keep private hostnames out of public resolver queries.
1. **DNS**: compare the resolver answer with the application's system lookup. For a public example, `doggo example.com. A --timeout=3s --json` and the same query for `AAAA` separate record families. Compare a specific resolver only when that destination is appropriate; record NXDOMAIN, SERVFAIL, timeout, answers, and TTL separately. `--ipv4` selects resolver transport, while `A` selects the requested record type.
1. **Connection**: check the resolved address and intended port from the failing environment. Connection refusal, timeout, and successful connection imply different next probes. A Python `socket.create_connection((host, port), timeout=5)` is a small probe; separately inspect listeners with the platform's existing tools. Do not scan unrelated ports.
1. **TLS**: preserve the original hostname for SNI and verification. With Python, wrap the connected socket using `ssl.create_default_context().wrap_socket(connection, server_hostname=host)` and inspect certificate validation and negotiated protocol. Keep both sockets in context managers. An IP URL can change certificate and virtual-host behavior.
1. **HTTP**: begin with `xh --ignore-stdin --check-status --timeout 5 HEAD https://example.com/`. Follow [xh](../../xh/SKILL.md) for bounded bodies and credentials. A 405 may mean HEAD is unsupported; use a bounded GET when appropriate. Inspect redirects before following them and distinguish HTTP errors from connection failures.
1. **Proxy and authentication**: compare the application's effective proxy, trust store, and identity with the working client. Test direct versus proxied access only where network policy permits it. Separate 401, 403, 407, and 429; use [gcloud](../../gcloud/SKILL.md) or the provider owner for account, scopes, IAM, and quota diagnostics.
1. Record the first boundary that differs, state one falsifiable cause, then change only that variable in a disposable fixture. Repeat the original application operation after the fix; a successful DNS lookup or HTTP 200 alone is insufficient.

## Bounds and failure cases

Use a Python `subprocess.run([...], timeout=15, check=False)` supervisor when a hard process deadline is required. Resolver/connect timeouts do not bound a complete multi-address or HTTP operation. Bound retained output too, and terminate only probes started for this task.

Exercise the method with a loopback fixture that returns a redirect, 401, and 503, plus a closed local port. A local TLS fixture should distinguish a trusted certificate from an untrusted or wrong-host certificate. Verify that diagnostics classify each failure without exposing headers, tokens, proxy passwords, or response bodies.

Keep certificate and hostname verification enabled. Replacing a trust store, disabling verification, broadening IAM, or changing a machine's resolver is a configuration change, not a diagnosis.

## Documentation

- [Doggo examples](https://doggo.mrkaran.dev/docs/guide/examples/) · [Doggo options](https://doggo.mrkaran.dev/docs/guide/reference/)
- [Python sockets](https://docs.python.org/3/library/socket.html) · [Python TLS](https://docs.python.org/3/library/ssl.html)
- Releases: [Doggo](https://github.com/mr-karan/doggo/releases)
