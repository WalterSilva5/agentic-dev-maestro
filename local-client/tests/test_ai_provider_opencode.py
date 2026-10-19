"""Header de sessão exigido pelo gateway do OpenCode (Console/Go).

O gateway responde 400 MissingSessionID quando o `x-opencode-session` não vai;
estes testes travam o contrato para o provedor opencode não regredir.
"""
import json
import urllib.request

from maestro_local.ai import providers

OPENCODE = {
    "id": "opencode",
    "name": "opencode (Zen Go)",
    "base_url": "https://opencode.ai/zen/go/v1",
    "api_key": "k",
    "model": "deepseek-v4.1-flash",
}
LOCAL = {"id": "lmstudio", "base_url": "http://localhost:1234/v1", "model": "m"}


class _Resp:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _captura_headers(monkeypatch, payload):
    capturado = {}

    def fake_urlopen(req, *a, **k):
        capturado["headers"] = {n.lower(): v for n, v in req.header_items()}
        return _Resp(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return capturado


def test_reconhece_o_provedor_opencode():
    assert providers.eh_opencode(OPENCODE) is True
    assert providers.eh_opencode(LOCAL) is False


def test_opencode_ganha_header_de_sessao(temp_db):
    h = providers.headers_extras(OPENCODE)
    assert h.get("x-opencode-session")
    assert h.get("User-Agent") == "maestro-local/1.0"


def test_sessao_e_estavel(temp_db):
    primeira = providers.headers_extras(OPENCODE)["x-opencode-session"]
    segunda = providers.headers_extras(OPENCODE)["x-opencode-session"]
    assert primeira == segunda


def test_outros_provedores_nao_ganham_header(temp_db):
    assert providers.headers_extras(LOCAL) == {}


def test_listar_modelos_manda_o_header(temp_db, monkeypatch):
    capturado = _captura_headers(monkeypatch, {"data": [{"id": "deepseek-v4.1-flash"}]})
    ok, _, modelos = providers.listar_modelos(OPENCODE)
    assert ok and modelos == ["deepseek-v4.1-flash"]
    assert capturado["headers"].get("x-opencode-session")


def test_verificar_modelo_manda_o_header(temp_db, monkeypatch):
    capturado = _captura_headers(monkeypatch, {})
    ok, _ = providers.verificar_modelo(OPENCODE, "deepseek-v4.1-flash")
    assert ok
    assert capturado["headers"].get("x-opencode-session")


def test_chat_model_recebe_default_headers(temp_db, monkeypatch):
    import langchain_openai

    capturado = {}

    class FakeChat:
        def __init__(self, **kwargs):
            capturado.update(kwargs)

    monkeypatch.setattr(langchain_openai, "ChatOpenAI", FakeChat)
    providers.clear_model_cache()
    providers.build_chat_model(OPENCODE)
    assert capturado["default_headers"]["x-opencode-session"]


def test_chat_model_de_outro_provedor_nao_recebe_header(temp_db, monkeypatch):
    import langchain_openai

    capturado = {}

    class FakeChat:
        def __init__(self, **kwargs):
            capturado.update(kwargs)

    monkeypatch.setattr(langchain_openai, "ChatOpenAI", FakeChat)
    providers.clear_model_cache()
    providers.build_chat_model(LOCAL)
    assert "default_headers" not in capturado
