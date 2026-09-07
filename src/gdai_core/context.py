"""Correlation id that survives across service boundaries.

Only pays off once every service propagates it, which is why it ships in the
first release: retrofitting a correlation id means touching every service a
second time.
"""

import uuid
from contextvars import ContextVar

HEADER = "X-Correlation-Id"

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def current() -> str | None:
    """The correlation id in scope, or None outside a request."""
    return _correlation_id.get()


def ensure() -> str:
    """The correlation id in scope, generating one if this is the chain's start."""
    existing = _correlation_id.get()
    if existing:
        return existing
    generated = uuid.uuid4().hex
    _correlation_id.set(generated)
    return generated


def bind(correlation_id: str | None) -> str:
    """Adopt an incoming correlation id, or start a new chain when absent.

    Called by the inbound edge (middleware); `ServiceClient` reads it on the way
    out. A ContextVar is what makes this work without threading the id through
    every function signature.
    """
    resolved = correlation_id or uuid.uuid4().hex
    _correlation_id.set(resolved)
    return resolved


def reset() -> None:
    _correlation_id.set(None)
