"""What a caller gets back from a successful call."""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Response:
    status: int
    body: Any
    headers: Mapping[str, str]
