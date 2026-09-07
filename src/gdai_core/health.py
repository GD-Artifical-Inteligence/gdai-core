"""Health check: the library runs and formats, the service decides what to check."""

import asyncio
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProbeResult:
    healthy: bool
    detail: str | None = None


class HealthProbe(Protocol):
    """One dependency a service considers part of its health.

    An interface because services legitimately differ here: Mongo, Redis,
    Qdrant. What to check belongs to the service; running and reporting does not.
    """

    name: str

    async def check(self) -> ProbeResult: ...


class HealthCheck:
    """Runs every probe and aggregates. Unhealthy if any probe is."""

    def __init__(self, probes: list[HealthProbe] | None = None) -> None:
        self._probes = probes or []

    async def run(self) -> dict:
        if not self._probes:
            return {"status": "ok", "checks": {}}

        results = await asyncio.gather(
            *(self._run_one(p) for p in self._probes),
        )
        checks = dict(results)
        healthy = all(c["healthy"] for c in checks.values())
        return {"status": "ok" if healthy else "degraded", "checks": checks}

    async def _run_one(self, probe: HealthProbe) -> tuple[str, dict]:
        try:
            result = await probe.check()
        except Exception as exc:  # noqa: BLE001
            # A probe that raises is a failing probe, never a failing healthcheck:
            # the endpoint has to answer even when a dependency is down, or the
            # orchestrator cannot tell "degraded" from "gone".
            return probe.name, {
                "healthy": False,
                "detail": f"{type(exc).__name__}: {exc}",
            }
        return probe.name, {"healthy": result.healthy, "detail": result.detail}
