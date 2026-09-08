"""What a caller gets back from a successful call."""

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Response:
    status: int
    body: Any
    headers: Mapping[str, str]
    # Corpo cru. Sempre presente; `body` é o mesmo já parseado como JSON, e fica
    # None quando a chamada pediu bytes. Ter os dois evita que quem baixa mídia
    # precise de um tipo de resposta separado.
    content: bytes = field(default=b"")
