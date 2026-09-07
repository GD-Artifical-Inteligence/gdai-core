from gdai_core.health import HealthCheck, ProbeResult


class Probe:
    def __init__(
        self, name: str, healthy: bool = True, raises: Exception | None = None
    ):
        self.name = name
        self._healthy = healthy
        self._raises = raises

    async def check(self) -> ProbeResult:
        if self._raises:
            raise self._raises
        return ProbeResult(healthy=self._healthy)


async def test_no_probes_is_ok():
    assert (await HealthCheck().run())["status"] == "ok"


async def test_all_healthy():
    r = await HealthCheck([Probe("mongo"), Probe("redis")]).run()
    assert r["status"] == "ok"
    assert set(r["checks"]) == {"mongo", "redis"}


async def test_one_unhealthy_degrades_the_whole():
    r = await HealthCheck([Probe("mongo"), Probe("redis", healthy=False)]).run()
    assert r["status"] == "degraded"
    assert r["checks"]["mongo"]["healthy"] is True
    assert r["checks"]["redis"]["healthy"] is False


async def test_a_raising_probe_is_a_failing_probe_not_a_failing_endpoint():
    """The endpoint has to answer even when a dependency is down, or the
    orchestrator cannot tell "degraded" from "gone"."""
    r = await HealthCheck([Probe("mongo", raises=RuntimeError("boom"))]).run()
    assert r["status"] == "degraded"
    assert "RuntimeError" in r["checks"]["mongo"]["detail"]
