# HTTPX Test Boundary

Inject a transport or client into the production client rather than monkeypatching, exercising real URL building, pagination, validation, and error paths. `respx` and `pytest-httpx` support `httpx` only — use `httpx2.MockTransport(handler)` for `httpx2`:

```python
import httpx2

def respond(request: httpx2.Request) -> httpx2.Response:
    if request.url.params.get("cursor") == "second":
        return httpx2.Response(200, json={"items": [{"id": "b"}], "next": None})
    return httpx2.Response(200, json={"items": [{"id": "a"}], "next": "second"})

client = httpx2.Client(base_url="https://api.example.test", transport=httpx2.MockTransport(respond))
```

Assert both the returned value and attempted requests (failing after an unauthorized request was already sent is a bug); use a bounded local HTTP server when TLS, proxies, socket timeouts, or pooling matter.

Source: [HTTPX2 mock transports](https://pydantic.dev/docs/httpx2/advanced/transports/#mock-transports) · [HTTPX mock transports](https://www.python-httpx.org/advanced/transports/#mock-transports).
