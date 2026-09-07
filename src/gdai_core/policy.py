"""Request policy: the knobs a caller must decide before making a call."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestPolicy:
    """Timeout, retry and backoff for one client.

    `timeout` has no default on purpose, and it is the most important decision
    in this package. A client cannot be constructed without choosing one, which
    is what prevents the omission that produced nine hand-rolled clients with
    nine different ideas about how long to wait.
    """

    timeout: float
    retries: int = 0
    backoff: float = 0.2
    retry_on: frozenset[int] = field(default_factory=lambda: frozenset({502, 503, 504}))
    retry_on_timeout: bool = True

    def __post_init__(self) -> None:
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.retries < 0:
            raise ValueError("retries cannot be negative")

    def delay_for(self, attempt: int) -> float:
        """Exponential backoff for the given zero-based attempt."""
        return self.backoff * (2**attempt)
