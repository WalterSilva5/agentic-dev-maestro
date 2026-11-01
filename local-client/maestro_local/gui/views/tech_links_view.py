"""Atalhos para sites de novidades de tecnologia.

Cartões clicáveis (abrem no navegador), agrupados por categoria e editáveis:
o usuário adiciona/remove atalhos e a lista fica salva na config.
"""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t

DEFAULT_LINKS = [
    {"nome": "daily.dev", "url": "https://daily.dev", "categoria": "Notícias",
     "descricao": "Feed personalizado de artigos e discussões por tecnologia."},
    {"nome": "Hacker News", "url": "https://news.ycombinator.com", "categoria": "Notícias",
     "descricao": "Notícias e discussões técnicas da comunidade Y Combinator."},
    {"nome": "r/programming", "url": "https://www.reddit.com/r/programming/", "categoria": "Notícias",
     "descricao": "Comunidade do Reddit sobre programação em geral."},
    {"nome": "DEV Community", "url": "https://dev.to", "categoria": "Comunidade",
     "descricao": "Comunidade de desenvolvedores com tutoriais e experiências."},
    {"nome": "GitHub Trending", "url": "https://github.com/trending", "categoria": "Comunidade",
     "descricao": "Projetos e linguagens que estão ganhando estrelas agora."},
    {"nome": "Roadmap.sh", "url": "https://roadmap.sh", "categoria": "Carreira & Estudos",
     "descricao": "Trilhas de estudo atualizadas por especialidade."},
    {"nome": "The Pragmatic Engineer", "url": "https://newsletter.pragmaticengineer.com", "categoria": "Carreira & Estudos",
     "descricao": "Newsletter sobre engenharia de software em grandes empresas."},
    {"nome": "Blog da Alura", "url": "https://www.alura.com.br/artigos", "categoria": "Carreira & Estudos",
     "descricao": "Análises, carreira e mercado tech em português."},
    {"nome": "GeekHunter Blog", "url": "https://blog.geekhunter.com.br", "categoria": "Carreira & Estudos",
     "descricao": "Carreira e mercado de tecnologia em português."},
]


def carregar_links() -> list[dict]:
    """Atalhos do usuário ou os padrões (cópia, para não mutar o default)."""
    from maestro_local.config import load_config
    links = load_config().get("settings", {}).get("tech_links")
    if not links:
        return [dict(x) for x in DEFAULT_LINKS]
    return list(links)


def salvar_links(links: list[dict]) -> None:
    from maestro_local.config import load_config, save_config
    cfg = load_config()
    cfg.setdefault("settings", {})["tech_links"] = links
    save_config(cfg)


class _LinkCard(QFrame):
    def __init__(self, link: dict, on_remove):
        super().__init__()
        self.setProperty("class", "card")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self._url = link["url"]
        th = current_theme()

        col = QVBoxLayout(self)
        col.setContentsMargins(16, 12, 12, 14)
        col.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(8)
        titulo = QLabel(link["nome"])
        titulo.setProperty("class", "cardTitle")
        head.addWidget(titulo, 1)
        remover = QToolButton()
        remover.setText("✕")
        remover.setToolTip(_t("Remover atalho"))
        remover.setCursor(Qt.PointingHandCursor)
        remover.setStyleSheet(
            f"QToolButton {{ background: transparent; border: none; color: {th.text_muted}; "
            f"font-size: 13px; border-radius: 6px; padding: 2px 6px; }}"
            f"QToolButton:hover {{ background: {th.bg_hover}; color: {th.danger}; }}")
        remover.clicked.connect(lambda: on_remove(link))
        head.addWidget(remover)
        col.addLayout(head)

        desc = QLabel(link.get("descricao", ""))
        desc.setProperty("class", "hint")
        desc.setWordWrap(True)
        col.addWidget(desc, 1)

        dominio = QLabel(link["url"])
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


class _AddLinkDialog(QDialog):
    def __init__(self, categorias, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_t("Novo atalho"))
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        lay.addWidget(QLabel(_t("Nome:")))
        self.nome = QLineEdit()
        lay.addWidget(self.nome)

        lay.addWidget(QLabel(_t("URL:")))
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://…")
        lay.addWidget(self.url)

        lay.addWidget(QLabel(_t("Categoria:")))
        self.categoria = QComboBox()
        self.categoria.setEditable(True)
        for c in categorias:
            self.categoria.addItem(c)
        lay.addWidget(self.categoria)

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        lay.addWidget(botoes)

    def valores(self):
        nome = self.nome.text().strip()
        url = self.url.text().strip()
        categoria = self.categoria.currentText().strip() or "Notícias"
        if url and "://" not in url:
            url = "https://" + url
        return nome, url, categoria


class TechLinksView(QWidget):
    """Grade de atalhos, agrupada por categoria e editável."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._links = carregar_links()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(14)

        topo = QHBoxLayout()
        titulo = QLabel(_t("Novidades de tecnologia"))
        titulo.setObjectName("sectionTitle")
        topo.addWidget(titulo)
        topo.addStretch()
        self.add_btn = QPushButton(_t("+ Adicionar atalho"))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._adicionar)
        topo.addWidget(self.add_btn)
        root.addLayout(topo)

        sub = QLabel(
            _t("Clique num card para abrir no navegador. Use ✕ para remover um "
               "atalho."))
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        root.addWidget(sub)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self._container = QWidget()
        self._col = QVBoxLayout(self._container)
        self._col.setContentsMargins(0, 4, 0, 0)
        self._col.setSpacing(14)
        self.scroll.setWidget(self._container)
        root.addWidget(self.scroll, 1)

        self._rebuild()

    # ------------------------------------------------------------------
    def _categorias(self) -> list[str]:
        vistas = []
        for link in self._links:
            c = link.get("categoria", "Geral")
            if c not in vistas:
                vistas.append(c)
        return vistas

    def _rebuild(self):
        while self._col.count():
            item = self._col.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        por_categoria: dict[str, list[dict]] = {}
        for link in self._links:
            por_categoria.setdefault(link.get("categoria", "Geral"), []).append(link)

        for categoria in self._categorias():
            rotulo = QLabel(categoria.upper())
            rotulo.setProperty("class", "sectionLabel")
            self._col.addWidget(rotulo)

            grade = QGridLayout()
            grade.setHorizontalSpacing(14)
            grade.setVerticalSpacing(14)
            for indice, link in enumerate(por_categoria[categoria]):
                card = _LinkCard(link, self._remover)
                grade.addWidget(card, indice // 2, indice % 2)
            for c in range(2):
                grade.setColumnStretch(c, 1)
            self._col.addLayout(grade)

        self._col.addStretch(1)

    def _adicionar(self):
        dlg = _AddLinkDialog(self._categorias(), self)
        if dlg.exec() != QDialog.Accepted:
            return
        nome, url, categoria = dlg.valores()
        if not nome or not url:
            return
        self._links.append({"nome": nome, "url": url, "categoria": categoria,
                            "descricao": ""})
        salvar_links(self._links)
        self._rebuild()

    def _remover(self, link):
        if link in self._links:
            self._links.remove(link)
        salvar_links(self._links)
        self._rebuild()
