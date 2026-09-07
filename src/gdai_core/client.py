"""The generic client every service-to-service call goes through.

Concrete, not an interface. A `ServiceClient` defined as a protocol would be
re-implemented differently in every service, which is the situation this package
exists to end.

It concentrates five things: enforcing the timeout, retrying only what is
retryable, mapping status to a typed error, attaching the service token, and
propagating the correlation id.

The default is that **errors propagate**. There is no `default=None` and no
`or []`. Degrading is written at the call site by whoever accepts it — the
inverse of the clients we have today, where a caught failure quietly became a
neutral value and the caller could not tell "no data" from "the call failed".
"""

import asyncio
import json
import logging
from typing import Any, Mapping

from gdai_core import context
from gdai_core.auth import TokenProvider
from gdai_core.errors import (
    ServiceContractError,
    ServiceResponseError,
    ServiceTimeout,
    ServiceUnavailable,
    UnexpectedTransportError,
)
from gdai_core.policy import RequestPolicy
from gdai_core.response import Response
from gdai_core.transport import HttpxTransport, RawResponse, Request, Transport

logger = logging.getLogger(__name__)


class ServiceClient:
    """Talks to one service. Typed clients wrap this; callers rarely use it raw."""

    def __init__(
        self,
        *,
        base_url: str,
        service: str,
        policy: RequestPolicy,
        transport: Transport | None = None,
        token_provider: TokenProvider | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service = service
        self._policy = policy
        self._transport = transport or HttpxTransport()
        self._token_provider = token_provider

    async def get(self, path: str, **kwargs: Any) -> Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> Response:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Response:
        return await self.request("DELETE", path, **kwargs)

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        operation: str | None = None,
    ) -> Response:
        op = operation or f"{method} {path}"
        request = Request(
            method=method,
            url=f"{self._base_url}/{path.lstrip('/')}",
            headers=await self._headers(headers),
            json=json_body,
            params=params,
            timeout=self._policy.timeout,
        )

        last: Exception | None = None
        for attempt in range(self._policy.retries + 1):
            try:
                raw = await self._send(request, op)
            except (ServiceTimeout, ServiceUnavailable) as exc:
                last = exc
                if not self._retryable_failure(attempt):
                    raise
            else:
                if self._retryable_status(raw.status, attempt):
                    last = self._response_error(raw, op)
                else:
                    return self._to_response(raw, op)

            await asyncio.sleep(self._policy.delay_for(attempt))

        # The loop only falls through after exhausting retries, so `last` is set.
        raise last  # type: ignore[misc]

    async def _headers(self, extra: Mapping[str, str] | None) -> dict[str, str]:
        headers = {context.HEADER: context.ensure()}
        if self._token_provider is not None:
            token = await self._token_provider.token_for(self._service)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        if extra:
            headers.update(extra)
        return headers

    async def _send(self, request: Request, operation: str) -> RawResponse:
        try:
            return await self._transport.send(request)
        except ServiceTimeout:
            raise
        except TimeoutError as exc:
            raise ServiceTimeout(service=self._service, operation=operation) from exc
        except OSError as exc:
            raise ServiceUnavailable(
                service=self._service, operation=operation, message=str(exc)
            ) from exc
        except Exception as exc:  # noqa: BLE001
            # The single escape hatch. Anything reaching here is a transport
            # failure we have not mapped, and saying so is more honest than
            # forcing it into a neighbouring type.
            raise UnexpectedTransportError(
                service=self._service,
                operation=operation,
                message=f"{type(exc).__name__}: {exc}",
            ) from exc

    def _retryable_failure(self, attempt: int) -> bool:
        return self._policy.retry_on_timeout and attempt < self._policy.retries

    def _retryable_status(self, status: int, attempt: int) -> bool:
        return status in self._policy.retry_on and attempt < self._policy.retries

    def _response_error(self, raw: RawResponse, operation: str) -> ServiceResponseError:
        return ServiceResponseError(
            service=self._service,
            operation=operation,
            status=raw.status,
            body=raw.text,
        )

    def _to_response(self, raw: RawResponse, operation: str) -> Response:
        if raw.status >= 400:
            raise self._response_error(raw, operation)

        body: Any = None
        if raw.text:
            try:
                body = raw.json()
            except (json.JSONDecodeError, ValueError) as exc:
                raise ServiceContractError(
                    service=self._service,
                    operation=operation,
                    message=f"response body is not valid JSON: {exc}",
                ) from exc

        return Response(status=raw.status, body=body, headers=raw.headers)
