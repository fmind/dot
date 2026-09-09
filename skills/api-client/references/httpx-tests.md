# HTTPX Test Boundary

Use the installed HTTPX release and the project's pytest conventions. Inject a client or transport into the production client so tests exercise its actual URL construction, traversal, validation, and error handling. Keep the real HTTPX request/response objects; fake the network boundary.

This minimal transport example demonstrates the seam without network access. Adapt the handler and pass the resulting client to the application's API adapter rather than stopping at a test of HTTPX itself.

```python
import httpx

seen: list[httpx.Request] = []

def respond(request: httpx.Request) -> httpx.Response:
    seen.append(request)
    if request.url.params.get("cursor") == "second":
        return httpx.Response(200, json={"items": [{"id": "b"}], "next": None})
    return httpx.Response(200, json={"items": [{"id": "a"}], "next": "second"})

with httpx.Client(
    base_url="https://api.example.test",
    transport=httpx.MockTransport(respond),
    timeout=httpx.Timeout(10.0, connect=3.0),
    follow_redirects=False,
) as client:
    first = client.get("/items")
    first.raise_for_status()
    second = client.get("/items", params={"cursor": first.json()["next"]})
    second.raise_for_status()
    assert [item["id"] for page in (first, second) for item in page.json()["items"]] == ["a", "b"]
assert len(seen) == 2
```

Test the application adapter against success, empty results, repeated cursors, a foreign-origin next link, oversized content, invalid JSON/schema, 401/403, transient failures, and exhausted budgets. Check both the returned result and requests attempted; an error after an unauthorized request is too late.

For retry tests, inject the clock, sleep, and jitter source only where needed. Simulate `httpx.ReadTimeout` after a write was accepted; verify reconciliation or an unknown result rather than an automatic duplicate. Cover cancellation and ensure partial results cannot be mistaken for a complete export.

Mock transports do not prove real TLS, proxy behavior, socket timeouts, or connection pooling. Use a bounded local HTTP server for those concerns when they matter, and distinguish that proof from provider acceptance.

Source: [HTTPX mock transports](https://www.python-httpx.org/advanced/transports/#mock-transports).
