"""The seam through which a token reaches an outbound call.

`gdai-core` must never import `gdai-auth` — the dependency points one way, and
inverting it would make the two packages one in practice. So core declares the
protocol and `gdai-auth` implements it.
"""

from typing import Protocol


class TokenProvider(Protocol):
    """Supplies the bearer token for a call to `service`.

    Returning None means "call it unauthenticated", which is a decision the
    provider makes, not a failure.
    """

    async def token_for(self, service: str) -> str | None: ...
