"""Binary bodies and multipart uploads.

A client that cannot carry either is incomplete rather than minimal: media
transfer is transport mechanics, not domain. Without these, a service moving
images between two upstreams had to keep its own httpx sessions and lost the
timeout, retry and typed errors everything else gets.
"""

import pytest
from fakes import FakeTransport, ok

from gdai_core import RequestPolicy, ServiceClient, ServiceContractError
from gdai_core.transport import RawResponse, Request

PNG = b"\x89PNG\r\n\x1a\n" + b"\xde\xad\xbe\xef" * 4


def client(transport, **kw):
    return ServiceClient(
        base_url="http://upstream",
        service="upstream",
        policy=kw.pop("policy", RequestPolicy(timeout=1.0)),
        transport=transport,
        **kw,
    )


def raw(content: bytes, status: int = 200, headers=None) -> RawResponse:
    return RawResponse(status=status, headers=headers or {}, content=content)


class TestCorpoBinario:
    async def test_get_bytes_devolve_o_conteudo_cru(self):
        r = await client(FakeTransport([raw(PNG)])).get_bytes("/media/1")
        assert r.content == PNG

    async def test_get_bytes_nao_tenta_parsear_json(self):
        """Sem isto, baixar uma imagem levantaria ServiceContractError."""
        r = await client(FakeTransport([raw(PNG)])).get_bytes("/media/1")
        assert r.body is None

    async def test_get_normal_ainda_recusa_corpo_invalido(self):
        with pytest.raises(ServiceContractError):
            await client(FakeTransport([raw(PNG)])).get("/media/1")

    async def test_status_de_erro_continua_levantando_no_modo_bytes(self):
        from gdai_core import ServiceResponseError

        with pytest.raises(ServiceResponseError):
            await client(FakeTransport([raw(b"nope", status=404)])).get_bytes("/x")

    async def test_content_tambem_vem_na_resposta_json(self):
        """Ter os dois evita um tipo de resposta separado para quem baixa mídia."""
        r = await client(FakeTransport([ok('{"a": 1}')])).get("/x")
        assert r.body == {"a": 1}
        assert r.content == b'{"a": 1}'


class TestMultipart:
    async def test_envia_arquivos_e_campos(self):
        t = FakeTransport([ok("{}")])
        await client(t).post(
            "/upload",
            files={"image": ("foto.png", PNG, "image/png")},
            data={"caption": "oi"},
        )
        assert t.requests[0].files["image"][0] == "foto.png"
        assert t.requests[0].data == {"caption": "oi"}

    async def test_multipart_nao_manda_json(self):
        t = FakeTransport([ok("{}")])
        await client(t).post("/upload", files={"f": ("a.txt", b"x", "text/plain")})
        assert t.requests[0].json is None

    def test_json_e_multipart_juntos_e_erro(self):
        """httpx não envia os dois; falhar na construção diz isso antes da rede."""
        with pytest.raises(ValueError, match="either json or a multipart"):
            Request(
                method="POST",
                url="http://x",
                json={"a": 1},
                files={"f": ("a.txt", b"x", "text/plain")},
            )


class TestTexto:
    def test_text_decodifica_o_conteudo(self):
        assert raw("olá".encode("utf-8")).text == "olá"

    def test_text_nao_estoura_com_bytes_invalidos(self):
        """Um corpo binário logado como texto não pode derrubar o log."""
        assert raw(b"\xff\xfe").text is not None


class TestRedirect:
    def test_segue_redirect_por_padrao(self):
        """Mídia do Chatwoot vem do Active Storage, que responde 302."""
        assert Request(method="GET", url="http://x").follow_redirects is True


class TestUrlAbsoluta:
    async def test_usa_url_absoluta_como_esta(self):
        """Upstreams devolvem links prontos — anexos em storage, URLs assinadas."""
        t = FakeTransport([raw(PNG)])
        await client(t).get_bytes("https://storage.example/att/1?sig=abc")
        assert t.requests[0].url == "https://storage.example/att/1?sig=abc"

    async def test_path_relativo_continua_colando_na_base(self):
        t = FakeTransport([ok("{}")])
        await client(t).get("/x")
        assert t.requests[0].url == "http://upstream/x"
