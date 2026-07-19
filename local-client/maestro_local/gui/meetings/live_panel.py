"""Painel do assistente ao vivo.

Transcrição em tempo real (topo) e as abas do copiloto — plano, dicas, ações,
decisões e o painel de perguntas & respostas — num splitter que prioriza as
abas. Embaixo, o campo de perguntar à reunião.

Só monta e sinaliza: preencher as abas e responder perguntas é da view.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.i18n import t


def make_live_list() -> QListWidget:
    """Lista das abas ao vivo: itens com quebra de linha, espaçados e legíveis."""
    lst = QListWidget()
    lst.setWordWrap(True)
    lst.setSpacing(4)
    lst.setUniformItemSizes(False)
    lst.setStyleSheet(
        "QListWidget { border: none; font-size: 13px; } "
        "QListWidget::item { padding: 10px 10px; min-height: 30px; "
        "border-bottom: 1px solid rgba(128,128,128,0.18); }"
    )
    return lst


class LiveAssistantPanel(QFrame):
    ask_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel(t("● Ao vivo"))
        title.setProperty("class", "cardTitle")
        head.addWidget(title)
        head.addStretch()
        self.live_status = QLabel("")
        self.live_status.setObjectName("subtitle")
        head.addWidget(self.live_status)
        lay.addLayout(head)

        # Splitter: transcrição ao vivo em cima, abas embaixo (arrastável).
        split = QSplitter(Qt.Vertical)
        split.setChildrenCollapsible(False)

        trans_pane = QWidget()
        tp = QVBoxLayout(trans_pane)
        tp.setContentsMargins(0, 0, 0, 0)
        tp.setSpacing(4)
        tp.addWidget(QLabel(t("Transcrição ao vivo")))
        self.live_transcript_edit = QTextEdit()
        self.live_transcript_edit.setReadOnly(True)
        self.live_transcript_edit.setPlaceholderText(
            t("A transcrição aparecerá aqui em tempo real..."))
        tp.addWidget(self.live_transcript_edit)
        trans_pane.setMinimumHeight(80)
        split.addWidget(trans_pane)

        self.live_tabs = QTabWidget()
        self.live_tabs.setMinimumHeight(320)
        self.live_plan_list = make_live_list()
        self.live_tips_list = make_live_list()
        self.live_actions_list = make_live_list()
        self.live_decisions_list = make_live_list()
        self.live_tabs.addTab(self.live_plan_list, "🗺 " + t("Plano"))
        self.live_tabs.addTab(self.live_tips_list, "💡 " + t("Dicas"))
        self.live_tabs.addTab(self.live_actions_list, "✅ " + t("Ações"))
        self.live_tabs.addTab(self.live_decisions_list, "📌 " + t("Decisões"))
        self.live_tabs.addTab(self._build_questions_panel(), "❓ " + t("Perguntas"))
        split.addWidget(self.live_tabs)

        # Prioriza as abas: transcrição menor, abas bem maiores.
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 4)
        split.setSizes([120, 480])
        lay.addWidget(split, 1)

        # Perguntar à reunião
        ask = QHBoxLayout()
        ask.setSpacing(8)
        self.ask_input = QLineEdit()
        self.ask_input.setPlaceholderText(
            t("Perguntar à reunião (ex.: o que ficou decidido sobre X?)"))
        self.ask_input.returnPressed.connect(lambda: self.ask_requested.emit())
        ask.addWidget(self.ask_input, 1)
        self.ask_btn = QPushButton(t("Perguntar"))
        self.ask_btn.setCursor(Qt.PointingHandCursor)
        self.ask_btn.clicked.connect(lambda: self.ask_requested.emit())
        ask.addWidget(self.ask_btn)
        lay.addLayout(ask)

        self.ask_answer = QLabel("")
        self.ask_answer.setWordWrap(True)
        self.ask_answer.setObjectName("subtitle")
        self.ask_answer.setVisible(False)
        lay.addWidget(self.ask_answer)

        self.setMinimumHeight(460)

    # ------------------------------------------------------------------
    def _build_questions_panel(self) -> QWidget:
        """Painel de perguntas & respostas (cards), em vez de lista simples."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.questions_container = QWidget()
        self.questions_layout = QVBoxLayout(self.questions_container)
        self.questions_layout.setContentsMargins(6, 6, 6, 6)
        self.questions_layout.setSpacing(8)
        self.questions_empty = QLabel(
            t("As perguntas levantadas na reunião aparecerão aqui — com a resposta "
              "assim que forem respondidas."))
        self.questions_empty.setWordWrap(True)
        self.questions_empty.setObjectName("subtitle")
        self.questions_layout.addWidget(self.questions_empty)
        self.questions_layout.addStretch()
        scroll.setWidget(self.questions_container)
        return scroll

    def set_ai_enabled(self, enabled: bool) -> None:
        """Sem provedor de IA, perguntar à reunião fica indisponível."""
        self.ask_input.setEnabled(enabled)
        self.ask_btn.setEnabled(enabled)
