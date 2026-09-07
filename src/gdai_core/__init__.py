"""Cross-cutting mechanics shared by GD.AI services.

Interfaces at the seams where services legitimately differ; concrete logic where
they must not. What this package deliberately does not hold is domain: no
`Company`, no `Contact`. A shared domain model would force a redeploy of every
service on every change — the monolith again, distributed and worse, because the
coupling becomes invisible. The contract between services is the API schema.
"""

from gdai_core.auth import TokenProvider
from gdai_core.client import ServiceClient
from gdai_core.envelope import ErrorEnvelope
from gdai_core.errors import (
    ServiceContractError,
    ServiceError,
    ServiceResponseError,
    ServiceTimeout,
    ServiceUnavailable,
    UnexpectedTransportError,
)
from gdai_core.health import HealthCheck, HealthProbe, ProbeResult
from gdai_core.policy import RequestPolicy
from gdai_core.response import Response
from gdai_core.settings import ServiceSettings
from gdai_core.transport import HttpxTransport, RawResponse, Request, Transport

__all__ = [
    "ErrorEnvelope",
    "HealthCheck",
    "HealthProbe",
    "HttpxTransport",
    "ProbeResult",
    "RawResponse",
    "Request",
    "RequestPolicy",
    "Response",
    "ServiceClient",
    "ServiceContractError",
    "ServiceError",
    "ServiceResponseError",
    "ServiceSettings",
    "ServiceTimeout",
    "ServiceUnavailable",
    "TokenProvider",
    "Transport",
    "UnexpectedTransportError",
]
