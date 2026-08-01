"""Captura de tela para o copiloto — com backend por ambiente.

Por que existe: `QScreen.grabWindow()` é API da era X11 e devolve um pixmap
VAZIO no Wayland nativo. O observador de tela usava só isso, então falhava em
silêncio em qualquer sessão Wayland (ver docs/planos/copiloto-ambiente).

Ordem de escolha:

1. **Qt** — sessões X11, sem processo externo e com seleção por monitor;
2. **spectacle** — KDE/Plasma (inclusive Wayland);
3. **grim** — compositores wlroots (Sway, Hyprland);
4. **gnome-screenshot** — GNOME.

O caminho universal no Wayland é o XDG Desktop Portal (ScreenCast) + PipeWire,
que exigiria novas dependências (bindings D-Bus e GStreamer) — fica para depois;
os backends acima já cobrem os ambientes mais comuns sem instalar nada.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Modos de captura. "janela" é o padrão do copiloto: mostra o que se está
# editando, com menos ruído e menos informação privada que a tela inteira.
MODO_JANELA = "janela"
MODO_MONITOR = "monitor"
MODO_TELA = "tela"
MODOS = (MODO_JANELA, MODO_MONITOR, MODO_TELA)

_TIMEOUT = 15


def _e_wayland() -> bool:
    if os.environ.get("WAYLAND_DISPLAY"):
        return True
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def _qt_serve() -> bool:
    """Qt só captura de fato fora do Wayland."""
    try:
        from PySide6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001
        return False
    app = QApplication.instance()
    if app is None:
        return not _e_wayland()
    return not app.platformName().startswith("wayland")


def detectar_backend() -> str | None:
    """Nome do backend utilizável neste ambiente, ou None."""
    if _qt_serve():
        return "qt"
    for nome, binario in (("spectacle", "spectacle"),
                          ("grim", "grim"),
                          ("gnome-screenshot", "gnome-screenshot")):
        if shutil.which(binario):
            return nome
    return None


def disponivel() -> tuple[bool, str]:
    """(pode capturar, motivo quando não pode) — texto pronto para a interface."""
    backend = detectar_backend()
    if backend:
        return True, ""
    if _e_wayland():
        return False, (
            "Ver a tela precisa de um utilitário de captura nesta sessão Wayland "
            "(o método do Qt é do X11 e não funciona aqui). Instale o spectacle "
            "(KDE), o grim (Sway/Hyprland) ou o gnome-screenshot."
        )
    return False, "Nenhum mecanismo de captura de tela disponível."


def capturar_png(modo: str = MODO_JANELA, monitor: int | None = None) -> bytes | None:
    """Captura e devolve PNG em bytes. None se não for possível.

    `monitor` só é respeitado pelo backend Qt; os utilitários externos capturam
    a janela ativa, o monitor atual ou a tela toda conforme `modo`.
    """
    backend = detectar_backend()
    if backend is None:
        return None
    if backend == "qt":
        return _capturar_qt(monitor)
    return _capturar_por_utilitario(backend, modo)


def _capturar_qt(monitor: int | None) -> bytes | None:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtWidgets import QApplication

    telas = QApplication.screens()
    if not telas:
        return None
    tela = telas[monitor] if (monitor is not None and 0 <= monitor < len(telas)) \
        else QApplication.primaryScreen()
    pix = tela.grabWindow(0)
    if pix is None or pix.isNull():
        return None
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    pix.save(buf, "PNG")
    buf.close()
    return bytes(ba.data())


def _argumentos(backend: str, modo: str, destino: Path) -> list[str] | None:
    if backend == "spectacle":
        alvo = {MODO_JANELA: "-a", MODO_MONITOR: "-m", MODO_TELA: "-f"}.get(modo, "-a")
        # -b: sem abrir a janela do Spectacle; -n: sem notificação a cada captura.
        return ["spectacle", "-b", "-n", alvo, "-o", str(destino)]
    if backend == "grim":
        return ["grim", str(destino)]        # grim captura a saída inteira
    if backend == "gnome-screenshot":
        args = ["gnome-screenshot", "-f", str(destino)]
        if modo == MODO_JANELA:
            args.insert(1, "-w")
        return args
    return None


def _capturar_por_utilitario(backend: str, modo: str) -> bytes | None:
    tmp = Path(tempfile.mkdtemp(prefix="maestro-cap-"))
    destino = tmp / "captura.png"
    try:
        args = _argumentos(backend, modo, destino)
        if not args:
            return None
        subprocess.run(args, timeout=_TIMEOUT, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not destino.exists() or destino.stat().st_size == 0:
            return None
        return destino.read_bytes()
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        # A imagem tem a tela do usuário: não fica em disco além do necessário.
        shutil.rmtree(tmp, ignore_errors=True)
