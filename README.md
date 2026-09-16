# gdai-core

Cross-cutting mechanics shared by GD.AI services: HTTP client, error taxonomy,
correlation id, logging, health and settings.

Design and rationale: [lq-api#115](https://github.com/GD-Artifical-Inteligence/lq-api/issues/115).

## Two rules it exists to enforce

- **`RequestPolicy.timeout` has no default.** A client cannot be constructed
  without choosing how long to wait.
- **`ServiceError` is abstract.** Raising it is a `TypeError`, so every failure
  has to say what it was.

Both close the same hole: a caught failure becoming a neutral value, so the
caller cannot tell "no data" from "the call failed". The two lead to opposite
decisions, so they must not share a return value.

## Usage

```python
from gdai_core import RequestPolicy, ServiceClient

client = ServiceClient(
    base_url="http://lq-api",
    service="lq-api",
    policy=RequestPolicy(timeout=5.0, retries=2),
    token_provider=provider,   # gdai-auth implements this
)

response = await client.get("/companies/internal/abc/billing")
```

Errors propagate. There is no `default=None` and no `or []`: degrading is
written at the call site by whoever accepts it.

Media and attachments do not go through JSON:

```python
media = await client.get_bytes("/attachments/1")   # media.content is bytes
await client.post("/upload", files={"image": ("photo.png", media.content, "image/png")})
```

`get_bytes` skips JSON parsing entirely — a `get` on an image would raise
`ServiceContractError`, correctly, because the body is not JSON. `Response.content`
carries the raw bytes on every response, so a caller that wants both does not
need a second response type.

```python
try:
    settings = await lq.get_billing_settings(company_id)
except ServiceTimeout:
    ...   # an explicit decision, visible in the diff
```

## Structure

| Piece | Kind |
|---|---|
| `Transport`, `TokenProvider`, `HealthProbe` | interface |
| `RequestPolicy`, `Response`, error hierarchy | data |
| `ServiceClient`, `ErrorEnvelope`, `HealthCheck`, `ServiceSettings` | logic |

Interfaces exist only at the seams where services legitimately differ. Everything
else is concrete, because uniformity is the point.

## What this package does not hold

Domain. No `Company`, no `Contact`. A shared domain model forces a redeploy of
every service on every change — the monolith again, distributed and worse,
because the coupling becomes invisible. The contract between services is the API
schema; typed clients live in the repo of the service that produces them.

## Consuming it

Built during the consumer's Docker build. No registry, and no credential ever
enters the image.

```yaml
- uses: actions/checkout@v4
  with:
    repository: GD-Artifical-Inteligence/gdai-core
    ref: v0.2.0        # never main
    path: gdai-core
```

```dockerfile
FROM python:3.12 AS libs
COPY gdai-core/ /src/gdai-core
RUN uv build /src/gdai-core --out-dir /wheels

FROM python:3.12
COPY --from=libs /wheels /wheels
RUN uv sync --frozen --find-links /wheels
```

The tag must be explicit. Checking out `main` would mean every service build
silently picks up the newest library — one change becoming a coordinated deploy
of seven services, with no diff for anyone to review.

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run pyright src
```

`BLE001` and `TRY400` are enabled. This repo starts at zero blind excepts and
stays there; a broad catch needs an explicit `noqa` signed by whoever wrote it.
