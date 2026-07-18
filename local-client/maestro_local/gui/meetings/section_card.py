"""Card de etapa numerada.

Deixa o fluxo da tela explícito (1 Preparar → 2 Gravar → 3 Resultado): número
em destaque, título e um texto curto explicando o passo.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from maestro_local.gui.theme import current_theme


class SectionCard(QFrame):
    """Card com cabeçalho numerado. O conteúdo vai em `self.body`."""

    def __init__(self, number: str, title_text: str, help_text: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        th = current_theme()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        badge = QLabel(number)
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background: {th.accent}; color: {th.text_on_accent}; border-radius: 11px; "
            f"font-weight: 800; font-size: 11px; border: none;")
        head.addWidget(badge)
        title = QLabel(title_text)
        title.setProperty("class", "cardTitle")
        head.addWidget(title)
        head.addStretch()
        outer.addLayout(head)

        if help_text:
            hint = QLabel(help_text)
            hint.setWordWrap(True)
            hint.setObjectName("subtitle")
            outer.addWidget(hint)

        # Onde os widgets da etapa são adicionados.
        self.body = outer
