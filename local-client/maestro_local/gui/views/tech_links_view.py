"""Atalhos para sites de novidades de tecnologia.

Cartões clicáveis que abrem o site no navegador padrão. Centraliza as fontes
para se manter atualizado sem sair do Maestro.
"""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t

LINKS = [
    ("daily.dev", "https://daily.dev",
     _t("Feed personalizado de artigos e discussões por tecnologia "
        "(Python, JS, Rust, IA, WebDev).")),
    ("DEV Community", "https://dev.to",
     _t("Comunidade de desenvolvedores do mundo todo, com tutoriais e "
        "experiências práticas.")),
    ("GitHub Trending", "https://github.com/trending",
     _t("Projetos e linguagens que estão ganhando estrelas agora.")),
    ("Roadmap.sh", "https://roadmap.sh",
     _t("Trilhas de estudo atualizadas por especialidade de desenvolvimento.")),
    ("Blog da Alura", "https://www.alura.com.br/artigos",
     _t("Análises, carreira e atualizações do mercado tech em português.")),
    ("GeekHunter Blog", "https://blog.geekhunter.com.br",
     _t("Carreira e mercado de tecnologia em português.")),
]


class _LinkCard(QFrame):
    def __init__(self, nome: str, url: str, descricao: str):
        super().__init__()
        self.setProperty("class", "card")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self._url = url
        th = current_theme()

        col = QVBoxLayout(self)
        col.setContentsMargins(16, 14, 16, 14)
        col.setSpacing(6)

        titulo = QLabel(nome)
        titulo.setProperty("class", "cardTitle")
        col.addWidget(titulo)

        desc = QLabel(descricao)
        desc.setProperty("class", "hint")
        desc.setWordWrap(True)
        col.addWidget(desc, 1)

        dominio = QLabel(url)
        dominio.setStyleSheet(
            f"color: {th.accent}; font-size: 11px; "
            f"font-family: 'Fira Code', 'JetBrains Mono', monospace; "
            f"border: none; background: transparent;")
        col.addWidget(dominio)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            webbrowser.open(self._url)
            event.accept()
            return
        super().mousePressEvent(event)


class TechLinksView(QWidget):
    """Grade de atalhos para sites de novidades."""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(14)

        titulo = QLabel(_t("Novidades de tecnologia"))
        titulo.setObjectName("sectionTitle")
        root.addWidget(titulo)

        sub = QLabel(
            _t("Atalhos para se manter atualizado — clique num card para abrir "
               "no navegador."))
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        root.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        cont = QWidget()
        grid = QGridLayout(cont)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setContentsMargins(0, 4, 0, 0)
        for indice, (nome, url, descricao) in enumerate(LINKS):
            card = _LinkCard(nome, url, descricao)
            grid.addWidget(card, indice // 2, indice % 2)
        for c in range(2):
            grid.setColumnStretch(c, 1)
        grid.setRowStretch((len(LINKS) + 1) // 2, 1)
        scroll.setWidget(cont)

        root.addWidget(scroll, 1)
