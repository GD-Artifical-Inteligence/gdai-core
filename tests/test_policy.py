import pytest

from gdai_core.policy import RequestPolicy


def test_timeout_has_no_default():
    """The most important decision in the package: a client cannot be built
    without choosing how long to wait."""
    with pytest.raises(TypeError):
        RequestPolicy()  # type: ignore[call-arg]


def test_rejects_a_nonsense_timeout():
    with pytest.raises(ValueError):
        RequestPolicy(timeout=0)


def test_backoff_is_exponential():
    p = RequestPolicy(timeout=1.0, backoff=0.1)
    assert [p.delay_for(i) for i in range(3)] == [0.1, 0.2, 0.4]
