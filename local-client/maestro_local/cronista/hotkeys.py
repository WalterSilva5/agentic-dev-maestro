"""Atalhos globais (pynput). Best-effort — pode não funcionar em Wayland."""
from __future__ import annotations

import logging

logger = logging.getLogger("maestro.cronista.hotkeys")


class GlobalHotkeys:
    """Registra atalhos globais do sistema. Falha de forma graciosa."""

    def __init__(self) -> None:
        self._listener = None

    def start(self, bindings: dict[str, callable]) -> bool:
        """bindings: {'<ctrl>+<shift>+r': callback}. Retorna True se ativou."""
        try:
            from pynput import keyboard
            self._listener = keyboard.GlobalHotKeys(bindings)
            self._listener.start()
            logger.info("Atalhos globais ativos: %s", list(bindings))
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning("Atalhos globais indisponíveis: %s", e)
            self._listener = None
            return False

    def stop(self) -> None:
        if self._listener:
            try:
                self._listener.stop()
            except Exception:  # noqa: BLE001
                pass
            self._listener = None
