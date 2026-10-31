"""Estado vazio padronizado: ícone + título + dica (e ação opcional)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from maestro_local.gui.theme import current_theme


class EmptyState(QWidget):
    """Bloco centralizado para listas/sessões sem conteúdo.

    Uso:
        empty = EmptyState(icon="🎉", title="Tudo em dia",
                           hint="Nenhuma tarefa vencida.",
                           action_text="Adicionar")
        empty.action.connect(callback)
    """

    action = Signal()

    def __init__(self, icon: str = "", title: str = "", hint: str = "",
                 action_text: str = "", parent=None):
        super().__init__(parent)
        th = current_theme()

        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignCenter)
        v.setContentsMargins(8, 18, 8, 18)
        v.setSpacing(5)

        if icon:
            ic = QLabel(icon)
            ic.setAlignment(Qt.AlignCenter)
            ic.setStyleSheet(
                "font-size: 26px; border: none; background: transparent;")
            v.addWidget(ic)

        if title:
            titulo = QLabel(title)
            titulo.setAlignment(Qt.AlignCenter)
            titulo.setStyleSheet(
                f"font-size: 14px; font-weight: 700; color: {th.text_primary}; "
                f"border: none; background: transparent;")
            v.addWidget(titulo)

        if hint:
            dica = QLabel(hint)
            dica.setAlignment(Qt.AlignCenter)
            dica.setWordWrap(True)
            dica.setStyleSheet(
                f"font-size: 12px; color: {th.text_muted}; "
                f"border: none; background: transparent;")
            v.addWidget(dica)

        self._btn = None
        if action_text:
            self._btn = QPushButton(action_text)
            self._btn.setProperty("class", "secondary")
            self._btn.setCursor(Qt.PointingHandCursor)
            self._btn.clicked.connect(self.action.emit)
            v.addWidget(self._btn, 0, Qt.AlignCenter)
