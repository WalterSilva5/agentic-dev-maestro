"""Coluna de histórico das reuniões.

Reúne "Nova reunião", busca, filtro de arquivadas, a lista (com reordenação
por arrasto e menu de contexto) e o estado vazio orientativo.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from maestro_local.i18n import t


class HistoryPanel(QWidget):
    """Painel do histórico. Só monta e sinaliza — carregar/abrir/excluir é da view."""

    new_meeting_requested = Signal()
    filters_changed = Signal()              # busca ou "mostrar arquivadas"
    item_opened = Signal(object)            # QListWidgetItem clicado
    context_menu_requested = Signal(object)  # posição do clique direito
    order_changed = Signal()                # itens reordenados por arrasto

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(6)

        title = QLabel(t("Histórico"))
        title.setProperty("class", "cardTitle")
        lay.addWidget(title)

        self.new_meeting_btn = QPushButton(t("➕ Nova reunião"))
        self.new_meeting_btn.setFixedHeight(34)
        self.new_meeting_btn.setCursor(Qt.PointingHandCursor)
        self.new_meeting_btn.setToolTip(
            t("Começa uma reunião do zero, limpando todos os campos."))
        self.new_meeting_btn.clicked.connect(lambda: self.new_meeting_requested.emit())
        lay.addWidget(self.new_meeting_btn)

        self.search = QLineEdit()
        self.search.setPlaceholderText(t("Buscar nas gravações..."))
        self.search.textChanged.connect(lambda _t: self.filters_changed.emit())
        lay.addWidget(self.search)

        self.show_archived_check = QCheckBox(t("Mostrar arquivadas"))
        self.show_archived_check.toggled.connect(lambda _c: self.filters_changed.emit())
        lay.addWidget(self.show_archived_check)

        self.history = QListWidget()
        self.history.setStyleSheet(
            "QListWidget::item { padding: 8px 6px; min-height: 34px; "
            "border-bottom: 1px solid rgba(128,128,128,0.15); }"
        )
        self.history.itemClicked.connect(lambda item: self.item_opened.emit(item))
        # Reordenar arrastando + menu de contexto (abrir/arquivar/excluir)
        self.history.setDragDropMode(QAbstractItemView.InternalMove)
        self.history.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history.customContextMenuRequested.connect(lambda pos: self.context_menu_requested.emit(pos))
        self.history.model().rowsMoved.connect(lambda *_a: self.order_changed.emit())
        lay.addWidget(self.history, 1)

        self.history_empty = QLabel(
            t("Nenhuma reunião ainda.\n\nGrave uma (botão “Gravar e transcrever”) ou "
              "importe uma transcrição do Meet/Teams em “📄 Importar arquivo”."))
        self.history_empty.setWordWrap(True)
        self.history_empty.setAlignment(Qt.AlignCenter)
        self.history_empty.setObjectName("subtitle")
        self.history_empty.setVisible(False)
        lay.addWidget(self.history_empty)

        self.setMinimumWidth(170)
        self.setMaximumWidth(420)

    # ------------------------------------------------------------------
    def query(self) -> str:
        return self.search.text().strip().lower()

    def show_archived(self) -> bool:
        return self.show_archived_check.isChecked()

    def set_empty_state(self, empty: bool, filtering: bool = False) -> None:
        """Estado vazio orientativo (some quando o vazio é resultado de busca)."""
        self.history_empty.setVisible(empty and not filtering)
        self.history.setVisible(not empty or filtering)
