"""What the client guarantees, stated as tests.

The recurring bug this package exists to stop: a caught failure becomes a
neutral value, and the caller cannot tell "no data" from "the call failed".
Several tests below exist only to pin that errors propagate.
"""

import pytest
from fakes import FakeTransport, ok

from gdai_core import context
from gdai_core.client import ServiceClient
from gdai_core.errors import (
    ServiceContractError,
    ServiceResponseError,
    ServiceTimeout,
    ServiceUnavailable,
    UnexpectedTransportError,
)
from gdai_core.policy import RequestPolicy
from gdai_core.transport import RawResponse


def client(transport, **kw):
    return ServiceClient(
        base_url="http://lq-api",
        service="lq-api",
        policy=kw.pop("policy", RequestPolicy(timeout=1.0)),
        transport=transport,
        **kw,
    )


async def test_success_returns_parsed_body():
    c = client(FakeTransport([ok('{"owner_id": "abc"}')]))
    r = await c.get("/companies/x")
    assert r.status == 200
    assert r.body == {"owner_id": "abc"}


async def test_error_status_raises_instead_of_returning_none():
    """The whole point. No `default=None`, no silent neutral value."""
    c = client(FakeTransport([ok("nope", status=404)]))
    with pytest.raises(ServiceResponseError) as exc:
        await c.get("/companies/x")
    assert exc.value.status == 404


async def test_timeout_becomes_typed_error():
    c = client(FakeTransport([TimeoutError("too slow")]))
    with pytest.raises(ServiceTimeout):
        await c.get("/companies/x")


async def test_connection_failure_becomes_typed_error():
    c = client(FakeTransport([OSError("connection refused")]))
    with pytest.raises(ServiceUnavailable):
        await c.get("/companies/x")


async def test_unmapped_failure_uses_the_escape_hatch():
    c = client(FakeTransport([RuntimeError("something new")]))
    with pytest.raises(UnexpectedTransportError) as exc:
        await c.get("/companies/x")
    assert "RuntimeError" in str(exc.value)


async def test_malformed_json_is_a_contract_error_not_a_transport_one():
    """The call worked; what came back is not what was promised."""
    c = client(FakeTransport([ok("this is not json")]))
    with pytest.raises(ServiceContractError):
        await c.get("/companies/x")


async def test_timeout_is_enforced_from_the_policy():
    t = FakeTransport([ok()])
    await client(t, policy=RequestPolicy(timeout=2.5)).get("/x")
    assert t.requests[0].timeout == 2.5


async def test_retries_retryable_status_then_succeeds():
    t = FakeTransport([ok(status=503), ok('{"ok": 1}')])
    c = client(t, policy=RequestPolicy(timeout=1.0, retries=1, backoff=0))
    r = await c.get("/x")
    assert r.body == {"ok": 1}
    assert len(t.requests) == 2


async def test_does_not_retry_a_non_retryable_status():
    t = FakeTransport([ok(status=404), ok()])
    c = client(t, policy=RequestPolicy(timeout=1.0, retries=3, backoff=0))
    with pytest.raises(ServiceResponseError):
        await c.get("/x")
    assert len(t.requests) == 1


async def test_raises_after_exhausting_retries():
    t = FakeTransport([ok(status=503), ok(status=503)])
    c = client(t, policy=RequestPolicy(timeout=1.0, retries=1, backoff=0))
    with pytest.raises(ServiceResponseError) as exc:
        await c.get("/x")
    assert exc.value.status == 503


async def test_retries_timeout_then_raises():
    t = FakeTransport([TimeoutError(), TimeoutError()])
    c = client(t, policy=RequestPolicy(timeout=1.0, retries=1, backoff=0))
    with pytest.raises(ServiceTimeout):
        await c.get("/x")
    assert len(t.requests) == 2


async def test_attaches_token_from_provider():
    class Provider:
        async def token_for(self, service: str) -> str:
            assert service == "lq-api"
            return "tok-123"

    t = FakeTransport([ok()])
    await client(t, token_provider=Provider()).get("/x")
    assert t.requests[0].headers["Authorization"] == "Bearer tok-123"


async def test_no_authorization_header_without_a_provider():
    t = FakeTransport([ok()])
    await client(t).get("/x")
    assert "Authorization" not in t.requests[0].headers


async def test_propagates_the_correlation_id_in_scope():
    context.bind("corr-abc")
    t = FakeTransport([ok()])
    await client(t).get("/x")
    assert t.requests[0].headers[context.HEADER] == "corr-abc"


async def test_starts_a_correlation_id_when_none_is_in_scope():
    t = FakeTransport([ok()])
    await client(t).get("/x")
    assert t.requests[0].headers[context.HEADER]


async def test_operation_name_reaches_the_error():
    c = client(FakeTransport([ok(status=500)]))
    with pytest.raises(ServiceResponseError) as exc:
        await c.get("/companies/x", operation="get_company")
    assert exc.value.operation == "get_company"
    assert exc.value.service == "lq-api"


async def test_empty_body_is_not_a_contract_error():
    c = client(FakeTransport([RawResponse(status=204, headers={}, content=b"")]))
    r = await c.delete("/x")
    assert r.status == 204
    assert r.body is None
