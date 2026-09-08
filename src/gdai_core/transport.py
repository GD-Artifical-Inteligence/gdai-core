"""The seam between the client's logic and the network.

Exists so `gdai-core` can be tested without a live server: tests swap in a fake
transport and assert on what the client did, not on what a server replied.
"""

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

import httpx


@dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    json: Any = None
    params: Mapping[str, Any] | None = None
    timeout: float = 10.0
    # Corpo multipart. `files` são os arquivos, `data` os campos que os
    # acompanham. Mutuamente exclusivo com `json`: httpx não envia os dois.
    files: Mapping[str, Any] | None = None
    data: Mapping[str, Any] | None = None
    follow_redirects: bool = True

    def __post_init__(self) -> None:
        if self.json is not None and (self.files or self.data):
            raise ValueError("a request carries either json or a multipart body")


@dataclass(frozen=True)
class RawResponse:
    status: int
    headers: Mapping[str, str]
    content: bytes

    @property
    def text(self) -> str:
        """Corpo decodificado. Só faz sentido em resposta textual."""
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        import json

        return json.loads(self.content)


class Transport(Protocol):
    """How a request actually leaves the process."""

    async def send(self, request: Request) -> RawResponse: ...


class HttpxTransport:
    """Default transport. Owns no policy — timeout comes in on the request."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owned = client is None

    async def send(self, request: Request) -> RawResponse:
        client = self._client or httpx.AsyncClient(
            follow_redirects=request.follow_redirects
        )
        try:
            response = await client.request(
                request.method,
                request.url,
                headers=dict(request.headers),
                json=request.json,
                files=dict(request.files) if request.files else None,
                data=dict(request.data) if request.data else None,
                params=dict(request.params) if request.params else None,
                timeout=request.timeout,
            )
        finally:
            if self._owned:
                await client.aclose()

        return RawResponse(
            status=response.status_code,
            headers=dict(response.headers),
            content=response.content,
        )
