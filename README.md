# gdai-core

Cross-cutting mechanics shared by GD.AI services: HTTP client, error taxonomy,
correlation id, logging, health and settings.

Design and rationale: [lq-api#115](https://github.com/GD-Artifical-Inteligence/lq-api/issues/115).

## What it is for

Before this package there were nine hand-rolled service clients, each with its
own idea of how long to wait and what to do when a call failed. One of them had
six `except Exception` blocks in 182 lines. The recurring bug that came out of
that shape: a caught failure becomes a neutral value, and the caller cannot tell
"no data" from "the call failed" — see the `owner_id` case in
[lq-api#111](https://github.com/GD-Artifical-Inteligence/lq-api/issues/111).

Two rules close that hole by construction:

- **`RequestPolicy.timeout` has no default.** A client cannot be built without
  choosing how long to wait.
- **`ServiceError` is abstract.** Raising it is a `TypeError`, so every failure
  has to say what it was.

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
    ref: v0.1.0        # never main
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
