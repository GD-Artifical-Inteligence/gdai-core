"""Error taxonomy for calls to other services.

Ownership is split in two layers. This module owns the *transport* layer: what
happened on the wire. Domain errors — "company not found", "insufficient
credits" — belong to the typed client of the service that produces them and
subclass `ServiceResponseError`.

`gdai-core` cannot know what a company is, so it must not name that error.
"""

from abc import ABC
from typing import Any, Self


class ServiceError(Exception, ABC):
    """Base for any failure of a call to another service.

    Abstract on purpose. Raising it directly is a `TypeError`, not a review
    comment someone might forget to leave: a failure that does not say what it
    was is the failure we are trying to stop shipping.

    Carries structured context rather than a formatted string, so logs can be
    filtered by service and operation instead of grepped.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if cls is ServiceError:
            raise TypeError(
                "ServiceError is abstract - raise a specific subclass so the "
                "failure explains itself"
            )
        return super().__new__(cls, *args)

    def __init__(
        self,
        *,
        service: str,
        operation: str,
        message: str | None = None,
    ) -> None:
        self.service = service
        self.operation = operation
        super().__init__(message or self._default_message())

    def _default_message(self) -> str:
        return f"{type(self).__name__} on {self.service}.{self.operation}"


class ServiceTimeout(ServiceError):
    """The service did not answer within the policy's timeout.

    Kept separate from `ServiceUnavailable` because a timeout is retryable
    almost always, while "never arrived" can be DNS or a service that is down —
    callers treat the two differently.
    """


class ServiceUnavailable(ServiceError):
    """The request never reached the service: DNS, refused connection, no route."""


class ServiceResponseError(ServiceError):
    """The service answered with an error status.

    Also the base for domain errors defined by each typed client.
    """

    def __init__(
        self,
        *,
        service: str,
        operation: str,
        status: int,
        body: Any = None,
        message: str | None = None,
    ) -> None:
        self.status = status
        self.body = body
        super().__init__(service=service, operation=operation, message=message)

    def _default_message(self) -> str:
        return f"{self.service}.{self.operation} answered {self.status}"


class ServiceContractError(ServiceError):
    """The service answered successfully but off-contract.

    Unparseable body, or a payload that does not validate against the DTO. The
    call worked; what came back is not what was promised.
    """


class UnexpectedTransportError(ServiceError):
    """A transport failure we never mapped.

    Deliberately ugly, and it should read as a gap to close rather than a
    comfortable default. It exists because forcing an unknown failure into a
    specific type that is wrong is worse than admitting we do not know: without
    this class, people pick the nearest type to satisfy the rule and the error
    starts lying.
    """
