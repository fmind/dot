# HTTPX Test Boundary

Inject a client or transport into the production client instead of patching, so tests exercise its actual URL construction, traversal, validation, and error handling with real HTTPX request and response objects. respx and pytest-httpx support only `httpx`, not `httpx2`: for an `httpx2` client, inject `httpx2.MockTransport(handler)`.

```python
import httpx2

def respond(request: httpx2.Request) -> httpx2.Response:
    if request.url.params.get("cursor") == "second":
        return httpx2.Response(200, json={"items": [{"id": "b"}], "next": None})
    return httpx2.Response(200, json={"items": [{"id": "a"}], "next": "second"})

client = httpx2.Client(base_url="https://api.example.test", transport=httpx2.MockTransport(respond))
```

Check both the returned result and the requests attempted: an error raised after an unauthorized request is too late. Mock transports do not prove real TLS, proxy behavior, socket timeouts, or connection pooling; use a bounded local HTTP server when those matter.

Source: [HTTPX2 mock transports](https://pydantic.dev/docs/httpx2/advanced/transports/#mock-transports) · [HTTPX mock transports](https://www.python-httpx.org/advanced/transports/#mock-transports).
