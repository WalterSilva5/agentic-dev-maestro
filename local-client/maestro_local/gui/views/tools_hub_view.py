"""Central de Ferramentas: uma tela-hub com cards (ícone + rótulo) que abrem
as funcionalidades extras, mantendo o menu lateral enxuto."""
from PySide6.QtCore import Qt, Signal
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

# (chave, ícone, rótulo, descrição)
HUB_ITEMS = [
    ("study", "📚", "Estudos", "Planos, tópicos e assistente de estudo"),
    ("transcricoes", "🎙", "Reuniões", "Gravar, transcrever e resumir"),
    ("vault", "🔒", "Senhas", "Cofre de senhas KeePass"),
    ("library", "📇", "Biblioteca", "Snippets, runbooks, triagem, code review, git, tempo"),
    ("apitester", "🛰", "Testador de API", "Monte, execute e salve requisições HTTP"),
    ("kb", "🧠", "Base de conhecimento", "Notas com backlinks e Q&A por IA"),
    ("english", "🗣️", "Praticar Inglês", "Conversação por voz com feedback da IA"),
]


class _HubCard(QFrame):
    clicked = Signal(str)

    def __init__(self, key, icon, label, desc):
        super().__init__()
        self._key = key
        self.setCursor(Qt.PointingHandCursor)
        t = current_theme()
        self.setStyleSheet(
            f"_HubCard {{ background: {t.bg_card}; border: 1px solid {t.border}; "
            f"border-radius: 12px; }} "
            f"_HubCard:hover {{ border: 1px solid {t.accent}; background: {t.bg_hover}; }}")
        self.setMinimumHeight(120)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(6)

        ico = QLabel(icon)
        ico.setStyleSheet("font-size: 30px; border: none; background: transparent;")
        lay.addWidget(ico)

        name = QLabel(_t(label))
        name.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {t.text_primary}; "
            f"border: none; background: transparent;")
        lay.addWidget(name)

        sub = QLabel(_t(desc))
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"font-size: 12px; color: {t.text_muted}; border: none; background: transparent;")
        lay.addWidget(sub)
        lay.addStretch()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._key)
        super().mousePressEvent(event)


class ToolsHubView(QWidget):
    def __init__(self, on_open):
        """`on_open(key)`: callback que troca para a tela da funcionalidade."""
        super().__init__()
        self._on_open = on_open
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(_t("Ferramentas"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel(_t("Funcionalidades extras — clique para abrir."))
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        self._grid = QGridLayout(container)
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(0, 0, 0, 0)
        cols = 3
        for i, (key, icon, label, desc) in enumerate(HUB_ITEMS):
            card = _HubCard(key, icon, label, desc)
            card.clicked.connect(self._on_open)
            self._grid.addWidget(card, i // cols, i % cols)
        for c in range(cols):
            self._grid.setColumnStretch(c, 1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

    def refresh(self):
        pass
