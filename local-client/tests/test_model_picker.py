"""Listagem de modelos ao testar a conexão do provedor de IA."""
import json
import urllib.request

import pytest

from maestro_local.ai import providers


class _Resp:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture()
def picker(qapp):
    from maestro_local.gui.model_picker_dialog import ModelPickerDialog
    return ModelPickerDialog(None, ["gpt-4o", "qwen2.5-coder-7b", "llama-3.1-8b"])


# --- providers.listar_modelos ---------------------------------------------

def test_lista_completa_e_devolvida(monkeypatch):
    """Antes só cinco nomes truncados chegavam à interface."""
    muitos = [{"id": f"modelo-{i}"} for i in range(12)]
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: _Resp({"data": muitos}))
    ok, msg, modelos = providers.listar_modelos({"base_url": "http://x/v1"})
    assert ok and len(modelos) == 12
    assert "12" in msg


def test_nomes_repetidos_aparecem_uma_vez(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: _Resp({"data": [{"id": "a"}, {"id": "a"}, {"id": "b"}]}))
    _, _, modelos = providers.listar_modelos({"base_url": "http://x/v1"})
    assert modelos == ["a", "b"]


def test_falha_nao_devolve_modelos(monkeypatch):
    def explode(*a, **k):
        raise OSError("recusado")
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    ok, _, modelos = providers.listar_modelos({"base_url": "http://x/v1"})
    assert ok is False and modelos == []


def test_base_url_vazia(monkeypatch):
    ok, msg, modelos = providers.listar_modelos({})
    assert ok is False and modelos == [] and "base_url" in msg


def test_test_connection_continua_com_dois_valores(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: _Resp({"data": [{"id": "a"}]}))
    ok, msg = providers.test_connection({"base_url": "http://x/v1"})
    assert ok is True and isinstance(msg, str)


# --- diálogo ---------------------------------------------------------------

def test_filtro_reduz_a_lista(picker):
    picker.filtro.setText("qwen")
    assert picker.lista.count() == 1
    assert picker.selecionado() == "qwen2.5-coder-7b"


def test_filtro_ignora_maiusculas(picker):
    picker.filtro.setText("LLAMA")
    assert picker.lista.count() == 1


def test_filtro_sem_resultado_desabilita_as_acoes(picker):
    picker.filtro.setText("inexistente")
    assert picker.lista.count() == 0
    assert picker.btn_usar.isEnabled() is False
    assert picker.btn_copiar.isEnabled() is False


def test_usar_devolve_o_nome_escolhido(picker):
    picker.filtro.setText("llama")
    picker._usar()
    assert picker.escolhido == "llama-3.1-8b"


def test_copiar_manda_para_a_area_de_transferencia(picker):
    from PySide6.QtWidgets import QApplication
    picker.filtro.setText("gpt")
    picker._copiar()
    assert QApplication.clipboard().text() == "gpt-4o"


def test_modelo_ja_configurado_vem_selecionado(qapp):
    from maestro_local.gui.model_picker_dialog import ModelPickerDialog
    dlg = ModelPickerDialog(None, ["a", "b", "c"], atual="b")
    assert dlg.selecionado() == "b"


# --- verificação do modelo -------------------------------------------------

def _erro_http(codigo, corpo):
    import urllib.error
    import io
    return urllib.error.HTTPError(
        "http://x/v1/chat/completions", codigo, "erro", {},
        io.BytesIO(json.dumps(corpo).encode()))


def test_modelo_que_responde(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Resp({"ok": 1}))
    ok, msg = providers.verificar_modelo({"base_url": "http://x/v1"}, "m1")
    assert ok is True and "m1" in msg


def test_regionerror_mostra_a_mensagem_do_provedor(monkeypatch):
    """O caso real: o modelo está no /models mas exige opt-in de região."""
    def explode(*a, **k):
        raise _erro_http(403, {"error": {
            "type": "RegionError",
            "message": "The latest version of this model is only available "
                       "hosted in China and requires explicit opt in: "
                       "https://opencode.ai/workspace/wrk_x/go"}})
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    ok, msg = providers.verificar_modelo({"base_url": "http://x/v1"}, "minimax-m2.5")
    assert ok is False
    assert "403" in msg
    assert "requires explicit opt in" in msg     # e o link, para resolver
    assert "opencode.ai/workspace" in msg


def test_modelo_nao_suportado(monkeypatch):
    def explode(*a, **k):
        raise _erro_http(401, {"error": {"message": "Model xpto is not supported"}})
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    ok, msg = providers.verificar_modelo({"base_url": "http://x/v1"}, "xpto")
    assert ok is False and "not supported" in msg


def test_corpo_de_erro_ilegivel_nao_quebra(monkeypatch):
    import io
    import urllib.error

    def explode(*a, **k):
        raise urllib.error.HTTPError("http://x", 500, "Server Error", {},
                                     io.BytesIO(b"<html>nao e json</html>"))
    monkeypatch.setattr(urllib.request, "urlopen", explode)
    ok, msg = providers.verificar_modelo({"base_url": "http://x/v1"}, "m1")
    assert ok is False and "500" in msg


def test_sem_modelo_nao_chama_o_provedor(monkeypatch):
    def nao_deveria(*a, **k):
        raise AssertionError("nao deveria chamar o provedor")
    monkeypatch.setattr(urllib.request, "urlopen", nao_deveria)
    ok, msg = providers.verificar_modelo({"base_url": "http://x/v1"}, "  ")
    assert ok is False and "modelo" in msg


def test_verificar_desabilitado_sem_base_url(picker):
    """O diálogo sem provedor (ex.: aberto de um contexto sem URL)."""
    assert picker.btn_verificar.isEnabled() is False


def test_verificar_habilitado_com_provedor(qapp):
    from maestro_local.gui.model_picker_dialog import ModelPickerDialog
    d = ModelPickerDialog(None, ["a"], provider={"base_url": "http://x/v1"})
    assert d.btn_verificar.isEnabled() is True


def test_trocar_de_modelo_limpa_o_resultado_anterior(qapp):
    """Senão o ✓ de um modelo ficaria valendo para outro."""
    from maestro_local.gui.model_picker_dialog import ModelPickerDialog
    d = ModelPickerDialog(None, ["a", "b"], provider={"base_url": "http://x/v1"})
    d._on_verificado(True, "a respondeu.")
    assert d.status.text()
    d.lista.setCurrentRow(1)
    assert d.status.text() == ""
