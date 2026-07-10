"""Iniciar com o sistema (Linux/XDG autostart).

Cria/remove um arquivo `.desktop` em `~/.config/autostart/`, que os ambientes
de desktop (GNOME, KDE, XFCE, etc.) executam automaticamente no login.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ID = "agentic-dev-maestro"


def is_supported() -> bool:
    """Autostart via XDG só faz sentido no Linux."""
    return sys.platform.startswith("linux")


def _autostart_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "autostart"


def desktop_path() -> Path:
    return _autostart_dir() / f"{APP_ID}.desktop"


def is_enabled() -> bool:
    return is_supported() and desktop_path().exists()


def _exec_command() -> str:
    """Comando que reabre o app usando o mesmo interpretador atual."""
    py = sys.executable or "python3"
    return f'"{py}" -m maestro_local'


def enable() -> None:
    if not is_supported():
        raise RuntimeError("Iniciar com o sistema só é suportado no Linux (XDG autostart).")
    d = _autostart_dir()
    d.mkdir(parents=True, exist_ok=True)
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Agentic Dev Maestro\n"
        "Comment=Gestão de tarefas e ciclo de desenvolvimento (local)\n"
        f"Exec={_exec_command()}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Hidden=false\n"
    )
    desktop_path().write_text(content, encoding="utf-8")


def disable() -> None:
    p = desktop_path()
    if p.exists():
        p.unlink()


def set_enabled(on: bool) -> None:
    enable() if on else disable()
