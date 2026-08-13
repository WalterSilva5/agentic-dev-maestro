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
