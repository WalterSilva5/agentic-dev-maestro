"""QComboBox que ignora a roda do mouse quando fechado.

Evita trocar de projeto/workspace sem querer ao rolar a página — a seleção só
muda clicando e escolhendo na lista. Com a lista aberta, a roda funciona normal.
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):  # noqa: N802
        # Repassa o scroll para o container (a página rola normalmente).
        event.ignore()
