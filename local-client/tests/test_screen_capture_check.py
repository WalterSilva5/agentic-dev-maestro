"""Captura de tela por backend.

`QScreen.grabWindow` é API da era X11 e devolve pixmap vazio no Wayland nativo:
o observador de tela falhava em silêncio em qualquer sessão Wayland. Agora há
detecção de backend e, quando nada serve, uma mensagem que diz o que instalar.
"""
import subprocess
from pathlib import Path

from maestro_local.transcricoes import screen_capture as sc


def test_x11_usa_o_backend_qt(qapp, monkeypatch):
    monkeypatch.setattr(type(qapp), "platformName", lambda self: "xcb")
    assert sc.detectar_backend() == "qt"


def test_wayland_com_spectacle_usa_spectacle(qapp, monkeypatch):
    monkeypatch.setattr(type(qapp), "platformName", lambda self: "wayland")
    monkeypatch.setattr(sc.shutil, "which",
                        lambda b: "/usr/bin/spectacle" if b == "spectacle" else None)
    assert sc.detectar_backend() == "spectacle"
    assert sc.disponivel() == (True, "")


def test_wayland_com_grim_usa_grim(qapp, monkeypatch):
    monkeypatch.setattr(type(qapp), "platformName", lambda self: "wayland")
    monkeypatch.setattr(sc.shutil, "which",
                        lambda b: "/usr/bin/grim" if b == "grim" else None)
    assert sc.detectar_backend() == "grim"


def test_wayland_sem_utilitario_explica_o_que_instalar(qapp, monkeypatch):
    """Antes ficava marcado sem capturar nada e sem dizer por quê."""
    monkeypatch.setattr(type(qapp), "platformName", lambda self: "wayland")
    monkeypatch.setattr(sc.shutil, "which", lambda b: None)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    ok, motivo = sc.disponivel()
    assert ok is False
    assert "spectacle" in motivo and "grim" in motivo


def test_modo_janela_e_o_padrao(qapp):
    """Para um copiloto, a janela ativa tem menos ruído e menos dado privado."""
    args = sc._argumentos("spectacle", sc.MODO_JANELA, Path("/tmp/x.png"))
    assert "-a" in args           # janela ativa
    assert "-n" in args           # sem notificação a cada captura
    assert "-b" in args           # sem abrir a janela do Spectacle


def test_modos_mapeiam_para_argumentos_distintos():
    d = Path("/tmp/x.png")
    janela = sc._argumentos("spectacle", sc.MODO_JANELA, d)
    monitor = sc._argumentos("spectacle", sc.MODO_MONITOR, d)
    tela = sc._argumentos("spectacle", sc.MODO_TELA, d)
    assert "-a" in janela and "-m" in monitor and "-f" in tela


def test_captura_sem_backend_devolve_none(qapp, monkeypatch):
    monkeypatch.setattr(sc, "detectar_backend", lambda: None)
    assert sc.capturar_png() is None


def test_utilitario_que_nao_gera_arquivo_devolve_none(qapp, monkeypatch):
    """Sem arquivo gerado, não inventa resultado."""
    monkeypatch.setattr(sc, "detectar_backend", lambda: "spectacle")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
    assert sc.capturar_png(sc.MODO_JANELA) is None


def test_utilitario_travado_nao_pendura(qapp, monkeypatch):
    def estoura(*a, **k):
        raise subprocess.TimeoutExpired(cmd="spectacle", timeout=1)
    monkeypatch.setattr(sc, "detectar_backend", lambda: "spectacle")
    monkeypatch.setattr(subprocess, "run", estoura)
    assert sc.capturar_png(sc.MODO_JANELA) is None


def test_ligar_observador_sem_captura_desmarca_e_explica(meetings_view, monkeypatch):
    v = meetings_view
    monkeypatch.setattr(v, "_provider_ready", lambda: True)
    monkeypatch.setattr(sc, "detectar_backend", lambda: None)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    v.screen_watch_check.setChecked(True)
    assert v.screen_watch_check.isChecked() is False, "não deve ligar sem captura"
    assert "spectacle" in v.status_label.text()
