"""The abstract base is the mechanism, not a convention."""

import pytest

from gdai_core.errors import (
    ServiceError,
    ServiceResponseError,
    ServiceTimeout,
    UnexpectedTransportError,
)


def test_base_cannot_be_raised():
    with pytest.raises(TypeError, match="abstract"):
        ServiceError(service="lq-api", operation="get_company")


def test_subclasses_can_be_raised():
    exc = ServiceTimeout(service="lq-api", operation="get_company")
    assert exc.service == "lq-api"
    assert exc.operation == "get_company"


def test_context_is_structured_not_only_a_string():
    exc = ServiceTimeout(service="lq-api", operation="get_company")
    assert (exc.service, exc.operation) == ("lq-api", "get_company")
    assert "lq-api" in str(exc)


def test_response_error_carries_status_and_body():
    exc = ServiceResponseError(
        service="lq-api", operation="get_company", status=404, body="not found"
    )
    assert exc.status == 404
    assert exc.body == "not found"
    assert "404" in str(exc)


def test_domain_errors_subclass_response_error():
    """Typed clients define these; core must never name them."""

    class CompanyNotFound(ServiceResponseError):
        pass

    exc = CompanyNotFound(service="lq-api", operation="get_company", status=404)
    assert isinstance(exc, ServiceResponseError)
    assert isinstance(exc, ServiceError)


def test_every_error_is_catchable_as_the_base():
    for exc in (
        ServiceTimeout(service="s", operation="o"),
        UnexpectedTransportError(service="s", operation="o"),
        ServiceResponseError(service="s", operation="o", status=500),
    ):
        assert isinstance(exc, ServiceError)
