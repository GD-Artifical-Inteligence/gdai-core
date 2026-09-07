"""One error shape on the wire, so consumers parse failures the same way."""

from dataclasses import asdict, dataclass

from gdai_core import context
from gdai_core.errors import ServiceError, ServiceResponseError


@dataclass(frozen=True)
class ErrorEnvelope:
    error: str
    message: str
    correlation_id: str | None = None
    service: str | None = None
    operation: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_exception(cls, exc: Exception) -> "ErrorEnvelope":
        if isinstance(exc, ServiceError):
            return cls(
                error=type(exc).__name__,
                message=str(exc),
                correlation_id=context.current(),
                service=exc.service,
                operation=exc.operation,
            )
        return cls(
            error=type(exc).__name__,
            message=str(exc),
            correlation_id=context.current(),
        )

    @staticmethod
    def status_for(exc: Exception) -> int:
        """HTTP status to answer with when `exc` escapes a handler.

        An upstream failure is 502/504, never 500: 500 says the fault is ours
        and sends whoever is debugging to the wrong service.
        """
        from gdai_core.errors import ServiceTimeout, ServiceUnavailable

        if isinstance(exc, ServiceTimeout):
            return 504
        if isinstance(exc, (ServiceUnavailable, ServiceResponseError)):
            return 502
        return 500
