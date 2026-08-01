"""Aviso quando ver a tela não funciona no ambiente.

`QScreen.grabWindow` devolve pixmap vazio no Wayland nativo: o observador de
tela falhava em silêncio — ligava e nada acontecia, sem explicação.
"""
from maestro_local.gui.views.transcricoes_view import TranscricoesView


def test_wayland_reporta_indisponivel(qapp, monkeypatch):
    monkeypatch.setattr(type(qapp), "platformName", lambda self: "wayland")
    ok, motivo = TranscricoesView._captura_de_tela_disponivel()
    assert ok is False
    assert "Wayland" in motivo and "portal" in motivo.lower()


def test_x11_reporta_disponivel(qapp, monkeypatch):
    monkeypatch.setattr(type(qapp), "platformName", lambda self: "xcb")
    ok, motivo = TranscricoesView._captura_de_tela_disponivel()
    assert ok is True
    assert motivo == ""


def test_ligar_observador_no_wayland_desmarca_e_explica(meetings_view, qapp, monkeypatch):
    v = meetings_view
    monkeypatch.setattr(v, "_provider_ready", lambda: True)
    monkeypatch.setattr(type(qapp), "platformName", lambda self: "wayland")
    v.screen_watch_check.setChecked(True)      # dispara o toggle
    assert v.screen_watch_check.isChecked() is False, "não deve ficar ligado sem captura"
    assert "Wayland" in v.status_label.text()
