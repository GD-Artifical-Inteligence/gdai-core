from gdai_core import context
from gdai_core.envelope import ErrorEnvelope
from gdai_core.errors import ServiceResponseError, ServiceTimeout, ServiceUnavailable


def test_carries_service_and_operation():
    e = ErrorEnvelope.from_exception(
        ServiceTimeout(service="lq-api", operation="get_company")
    )
    assert e.error == "ServiceTimeout"
    assert e.service == "lq-api"
    assert e.operation == "get_company"


def test_includes_the_correlation_id_in_scope():
    context.bind("corr-1")
    e = ErrorEnvelope.from_exception(ServiceTimeout(service="s", operation="o"))
    assert e.correlation_id == "corr-1"
    context.reset()


def test_handles_a_plain_exception():
    e = ErrorEnvelope.from_exception(ValueError("bad"))
    assert e.error == "ValueError"
    assert e.service is None


def test_upstream_failures_are_not_500():
    """500 says the fault is ours and sends whoever is debugging to the wrong
    service."""
    assert ErrorEnvelope.status_for(ServiceTimeout(service="s", operation="o")) == 504
    assert (
        ErrorEnvelope.status_for(ServiceUnavailable(service="s", operation="o")) == 502
    )
    assert (
        ErrorEnvelope.status_for(
            ServiceResponseError(service="s", operation="o", status=404)
        )
        == 502
    )
    assert ErrorEnvelope.status_for(ValueError("ours")) == 500


def test_omits_empty_fields():
    assert "service" not in ErrorEnvelope.from_exception(ValueError("x")).to_dict()
