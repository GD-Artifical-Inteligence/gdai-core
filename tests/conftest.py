import pytest

from gdai_core import context


@pytest.fixture(autouse=True)
def _clean_context():
    context.reset()
    yield
    context.reset()
