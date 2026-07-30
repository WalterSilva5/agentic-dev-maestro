"""Agrupamento visual de botões relacionados numa barra de ações.

Botões soltos lado a lado (ex.: "Preview", "Template", "Salvar" numa fileira só)
não comunicam quais pertencem juntos nem qual é a ação principal — lê como uma
lista de botões, não como uma barra de ferramentas. Este helper separa um
cluster do resto com um traço vertical fino e, opcionalmente, um rótulo — o
mesmo padrão já usado na barra de ações de Reuniões.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from maestro_local.gui.theme import current_theme


def vsep() -> QFrame:
    """Separador vertical fino entre grupos de uma barra de ações."""
    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setFixedSize(1, 24)
    sep.setStyleSheet(f"color: {current_theme().border};")
    return sep


def action_group(buttons: list, label: str | None = None) -> QWidget:
    """Grupo de botões relacionados, com um traço vertical antes (e rótulo
    opcional). Fica num container próprio para quebrar como unidade em telas
    estreitas — o rótulo nunca se separa dos seus botões."""
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    row.addWidget(vsep())
    if label:
        lbl = QLabel(label)
        lbl.setObjectName("subtitle")
        row.addWidget(lbl)
    for b in buttons:
        row.addWidget(b)
    return w
