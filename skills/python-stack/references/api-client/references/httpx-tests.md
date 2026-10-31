# HTTPX Test Boundary

Use the project's installed `httpx2` or `httpx` release and pytest conventions; the example below runs on `httpx` as well once every `httpx2` name becomes `httpx`. respx and pytest-httpx support only `httpx`, so do not patch: inject a client or transport into the production client so tests exercise its actual URL construction, traversal, validation, and error handling. Keep the real HTTPX request/response objects; fake the network boundary.

This minimal transport example demonstrates the seam without network access. Adapt the handler and pass the resulting client to the application's API adapter rather than stopping at a test of HTTPX itself.

```python
import httpx2

seen: list[httpx2.Request] = []

def respond(request: httpx2.Request) -> httpx2.Response:
    seen.append(request)
    if request.url.params.get("cursor") == "second":
        return httpx2.Response(200, json={"items": [{"id": "b"}], "next": None})
    return httpx2.Response(200, json={"items": [{"id": "a"}], "next": "second"})

with httpx2.Client(
    base_url="https://api.example.test",
    transport=httpx2.MockTransport(respond),
    timeout=httpx2.Timeout(10.0, connect=3.0),
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

For retry tests, inject the clock, sleep, and jitter source only where needed. Simulate `httpx2.ReadTimeout` after a write was accepted; verify reconciliation or an unknown result rather than an automatic duplicate. Cover cancellation and ensure partial results cannot be mistaken for a complete export.

Mock transports do not prove real TLS, proxy behavior, socket timeouts, or connection pooling. Use a bounded local HTTP server for those concerns when they matter, and distinguish that proof from provider acceptance.

Source: [HTTPX2 mock transports](https://pydantic.dev/docs/httpx2/advanced/transports/#mock-transports) · [HTTPX mock transports](https://www.python-httpx.org/advanced/transports/#mock-transports).
