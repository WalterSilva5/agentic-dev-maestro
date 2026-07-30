"""Aviso de RAM por modelo Whisper nas Configurações (isolado — não toca config.json real)."""
from maestro_local.gui.views.settings_view import SettingsView


def test_hint_reflete_o_modelo_padrao(qapp, temp_db):
    v = SettingsView()
    assert v.whisper_model.currentText() == "small"
    assert "500 MB" in v.whisper_ram_hint.text()


def test_hint_atualiza_ao_trocar_modelo(qapp, temp_db):
    v = SettingsView()
    v.whisper_model.setCurrentIndex(v.whisper_model.findText("large-v3"))
    assert "3.0 GB" in v.whisper_ram_hint.text()
    v.whisper_model.setCurrentIndex(v.whisper_model.findText("tiny"))
    assert "75 MB" in v.whisper_ram_hint.text()


def test_nao_toca_o_config_json_real(qapp, temp_db, monkeypatch):
    from pathlib import Path
    real_config = Path.home() / ".maestro-local" / "config.json"
    before = real_config.read_text() if real_config.exists() else None

    v = SettingsView()
    v.whisper_model.setCurrentIndex(v.whisper_model.findText("tiny"))

    after = real_config.read_text() if real_config.exists() else None
    assert before == after, "teste vazou para o config.json real do usuário"
