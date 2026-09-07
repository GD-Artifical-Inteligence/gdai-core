from gdai_core import context


def test_absent_outside_a_request():
    assert context.current() is None


def test_bind_adopts_an_incoming_id():
    assert context.bind("from-upstream") == "from-upstream"
    assert context.current() == "from-upstream"


def test_bind_starts_a_chain_when_absent():
    generated = context.bind(None)
    assert generated
    assert context.current() == generated


def test_ensure_is_idempotent():
    first = context.ensure()
    assert context.ensure() == first
