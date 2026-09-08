from gdai_core.transport import RawResponse, Request


class FakeTransport:
    """Records requests and replays scripted responses.

    The reason `Transport` is a protocol: without this, every test in this
    package would need a live server.
    """

    def __init__(self, responses: list[RawResponse | Exception]) -> None:
        self._responses = list(responses)
        self.requests: list[Request] = []

    async def send(self, request: Request) -> RawResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("FakeTransport ran out of scripted responses")
        nxt = self._responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


def ok(body: str = '{"ok": true}', status: int = 200) -> RawResponse:
    return RawResponse(status=status, headers={}, content=body.encode("utf-8"))
