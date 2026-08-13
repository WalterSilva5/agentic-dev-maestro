"""Gravação do provedor de IA: nunca com o campo pela metade.

Gravar a cada tecla salvava prefixos do nome do modelo, e como salvar invalida
o cache de modelos, a IA passava a ser chamada com o nome incompleto — os erros
vistos em produção eram "Model minim is not supported" e "Model minimax-m2. is
not supported", prefixos exatos de "minimax-m2.1".
"""
import pytest

from maestro_local.config import get_active_ai_provider, save_ai_providers


@pytest.fixture()
def settings(qapp, temp_db):
    save_ai_providers([{"id": "p1", "name": "t", "base_url": "http://x/v1",
                        "api_key": "", "model": "antigo"}], active_id="p1")
    from maestro_local.gui.views.settings_view import SettingsView
    return SettingsView()


def _digitar(campo, texto):
    for ch in texto:
        campo.setText(campo.text() + ch)


def test_digitacao_nao_grava_nome_parcial(settings, qapp):
    settings.ai_model.setText("")
    settings.ai_model.clear()
    _digitar(settings.ai_model, "minimax-m2.1")
    qapp.processEvents()
    # nada de "minim", "minimax-m2." etc. chega à configuração
    assert get_active_ai_provider()["model"] == "antigo"


def test_pausa_na_digitacao_grava_o_nome_inteiro(settings, qapp):
    settings.ai_model.clear()
    _digitar(settings.ai_model, "minimax-m2.1")
    settings._ai_save_timer.timeout.emit()      # a pausa terminou
    qapp.processEvents()
    assert get_active_ai_provider()["model"] == "minimax-m2.1"


def test_sair_do_campo_grava_na_hora(settings, qapp):
    settings.ai_model.clear()
    _digitar(settings.ai_model, "gpt-4o")
    settings.ai_model.editingFinished.emit()
    qapp.processEvents()
    assert get_active_ai_provider()["model"] == "gpt-4o"


def test_testar_conexao_usa_o_valor_da_tela(settings, qapp, monkeypatch):
    """Testar logo após digitar não pode usar o provedor antigo."""
    settings.ai_model.clear()
    _digitar(settings.ai_model, "qwen2.5-coder")

    capturado = {}

    class W:
        def __init__(self, provider):
            capturado["provider"] = provider

        class _Sinal:
            def connect(self, *_a):
                pass
        done = _Sinal()

        def start(self):
            pass

    import maestro_local.gui.views.settings_view as sv
    monkeypatch.setattr(sv, "ConnTestWorker", W)
    settings._test_ai_connection()
    assert capturado["provider"]["model"] == "qwen2.5-coder"
    assert get_active_ai_provider()["model"] == "qwen2.5-coder"


def test_escolher_modelo_na_lista_grava_na_hora(settings, qapp, monkeypatch):
    import maestro_local.gui.views.settings_view as sv

    class DlgFalso:
        escolhido = "llama-3.1-8b"

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return sv.QDialog.Accepted

    monkeypatch.setattr(
        "maestro_local.gui.model_picker_dialog.ModelPickerDialog", DlgFalso)
    settings._mostrar_modelos(["llama-3.1-8b"])
    qapp.processEvents()
    assert get_active_ai_provider()["model"] == "llama-3.1-8b"
