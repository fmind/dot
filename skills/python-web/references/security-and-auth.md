---
name: security-and-auth
description: "Implement OIDC/OAuth2 login, JWT validation, Argon2id hashing, webhook HMAC checks, CSRF cookies, and security headers."
---

# Web Security, Auth, & Boundaries

Fail-closed defaults for Python HTTP services and browser apps ([code-review](../../code-security/references/code-review/GUIDE.md) owns threat modeling and audit checks).

## OIDC, OAuth2 Login, & Password Hashing

- **Verify explicit claims with `PyJWT[crypto]`**: validate signature, `exp` (with bounded `leeway`), `iss`, and expected `aud` against a pinned explicit list `algorithms=["RS256", "ES256"]` — never pass untrusted token headers as `algorithms` and never accept `alg="none"`.
- **OAuth2 / OIDC Relying Party & JWE**: use `authlib>=1.9.8` paired with `joserfc>=1.8.0` for authorization-code + PKCE browser logins, provider discovery, and encrypted JWE tokens, keeping PKCE verifiers and state nonces in server-validated session state.
- **Local password & secret hashing**: hash user passwords with Argon2id via `pwdlib[argon2]>=0.4.2` (`PasswordHash.recommended()`, calling `verify_and_update` to upgrade stale parameters transparently; never use unmaintained `passlib` or raw SHA digests).
- **Cloud Run & Cloud Tasks OIDC**: prefer IAM service-to-service invoker auth (`roles/run.invoker`) or validate Google OIDC tokens via `google-auth` (`google.oauth2.id_token.verify_oauth2_token`) checking `issuer == "https://accounts.google.com"`, `email_verified`, expected service account email, and exact service audience URL.
- **Bound JWKS fetches**: cache provider JWKS with TLS verification and short TTL (`PyJWKClient(..., cache_keys=True, lifespan=300)`), failing `401` on network/key errors.

## Webhook Signature & Replay Defense

1. **Read raw bytes before parsing JSON**: verify the MAC over exact request `await request.body()`, never re-serialized dicts.
1. **Constant-time check + replay window**: compute expected HMAC-SHA256 digest, compare via `hmac.compare_digest(expected, provided)`, and reject timestamps outside a bounded window (`abs(now - ts) <= 300`). Store delivery IDs when idempotency matters.

## Sessions, CSRF, & Security Headers

- **Litestar CSRF + cookies**: enable `CSRFConfig(secret=config.session_secret.get_secret_value(), cookie_secure=config.environment == "production", cookie_httponly=True, cookie_samesite="lax")` and render `{{ csrf_input | safe }}` inside HTMX/HTML forms (`HX-XSRFToken` or `x-csrftoken` header for AJAX/HTMX mutations). Store only opaque session IDs or HMAC-signed minimal claims, never PII or secrets in client cookies.
- **Default response headers**: set an after-request/middleware header baseline:
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `X-Frame-Options: DENY`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
  - `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'` (add explicit hashes/nonces instead of `'unsafe-inline'`)
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` when `environment == "production"` over HTTPS.

## SSRF & Upload Boundaries

- **Outbound user-influenced URLs**: enforce [ssrf-egress](../../code-security/references/code-review/references/ssrf-egress.md) (`https` only, reject userinfo `user:pass@host`, set `trust_env=False` and `follow_redirects=False` or re-validate every redirect hop, verify all resolved DNS answers unpacking `ip.ipv4_mapped` while blocking CGNAT `100.64.0.0/10` and NAT64 `64:ff9b::/96`, and pin the validated IP at socket connect time or route through an L3/L4-enforced egress proxy).
- **File uploads**: enforce `max_upload_bytes` before buffering to disk, strip directory paths (`Path(filename).name`), generate server-owned storage keys, validate magic bytes + extension allowlist, and serve downloads with `Content-Disposition: attachment` from a distinct origin/bucket when possible.

## Documentation

- [Litestar Security & CSRF](https://docs.litestar.dev/latest/usage/security/) · [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/) · [PyJWT docs](https://pyjwt.readthedocs.io/en/stable/) · [Authlib](https://docs.authlib.org/en/latest/) · [joserfc](https://jose.authlib.org/en/) · [pwdlib](https://frankie567.github.io/pwdlib/)
