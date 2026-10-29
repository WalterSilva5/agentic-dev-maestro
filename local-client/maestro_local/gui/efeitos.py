"""Efeitos visuais que o QSS não cobre — hoje, sombra real nos cards.

QSS não tem `box-shadow`; o equivalente no Qt é `QGraphicsDropShadowEffect`.
Aplicar por widget é o que dá profundidade aos cards sem trocar de toolkit.
"""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect


def aplicar_sombras(raiz, escuro: bool = False) -> None:
    """Sombra suave em todo `QFrame[class="card"]` da árvore.

    Idempotente: marca o widget com `_sombra` e, se já houver efeito, só
    atualiza a cor (troca de tema). `raiz` pode ser a janela ou uma tela.
    """
    if raiz is None:
        return
    cor = QColor(0, 0, 0, 130 if escuro else 28)
    for widget in raiz.findChildren(QFrame):
        if widget.property("class") != "card":
            continue
        efeito = widget.graphicsEffect()
        if widget.property("_sombra") and isinstance(efeito, QGraphicsDropShadowEffect):
            efeito.setColor(cor)
            continue
        efeito = QGraphicsDropShadowEffect(widget)
        efeito.setBlurRadius(18)
        efeito.setOffset(0, 4)
        efeito.setColor(cor)
        widget.setGraphicsEffect(efeito)
        widget.setProperty("_sombra", True)
