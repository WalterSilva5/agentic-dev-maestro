"""Etapa 3 — Assistente ao vivo.

As abas do copiloto — plano, dicas, ações, decisões e o painel de perguntas
& respostas — e, embaixo, o campo de perguntar à reunião. A transcrição em si
não aparece aqui: ela vai direto para o campo da etapa 4 (Resultado), que é o
único lugar onde o texto da reunião existe.

Antes esse painel aparecia solto entre as etapas "Gravar" e "Resultado", sem
número — quebrava a sequência numerada do fluxo. Agora é a própria etapa 3,
com o mesmo cabeçalho numerado das demais (SectionCard).

Só monta e sinaliza: preencher as abas e responder perguntas é da view.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.meetings.section_card import SectionCard
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


class LiveAssistantPanel(SectionCard):
    ask_requested = Signal()
    note_added = Signal(str)   # informação nova digitada durante a reunião

    def __init__(self, parent=None):
        super().__init__(
            "3", t("Assistente ao vivo"),
            t("Ligue \"Assistente ao vivo\" na etapa 2 para ver plano, dicas, ações, "
              "decisões e perguntas conforme a reunião acontece."),
            parent)
        lay = self.body

        status_row = QHBoxLayout()
        status_row.addStretch()
        self.live_status = QLabel("")
        self.live_status.setObjectName("subtitle")
        status_row.addWidget(self.live_status)
        lay.addLayout(status_row)

        # A transcrição ao vivo aparece direto no campo da etapa 4 — aqui ficam
        # só os itens que o assistente extrai dela.
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
        lay.addWidget(self.live_tabs, 1)

        # Informar algo ao assistente durante a reunião (vai para o contexto,
        # não para a transcrição). Fica ANTES de "perguntar" porque alimenta o
        # assistente, enquanto o de baixo consulta.
        note = QHBoxLayout()
        note.setSpacing(8)
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText(
            t("📝 Informar ao assistente (ex.: o prazo mudou para sexta)"))
        self.note_input.setToolTip(
            t("Acrescenta uma informação ao contexto da reunião AGORA — o assistente "
              "passa a considerá-la nas próximas atualizações de plano, ações e dicas. "
              "Não entra na transcrição."))
        self.note_input.returnPressed.connect(self._emit_note)
        note.addWidget(self.note_input, 1)
        self.note_btn = QPushButton(t("Adicionar"))
        self.note_btn.setProperty("flat", "true")
        self.note_btn.setCursor(Qt.PointingHandCursor)
        self.note_btn.clicked.connect(self._emit_note)
        note.addWidget(self.note_btn)
        lay.addLayout(note)

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

        self.setMinimumHeight(420)

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

    def _emit_note(self) -> None:
        """Emite a nota digitada e limpa o campo (ignora texto vazio)."""
        text = self.note_input.text().strip()
        if not text:
            return
        self.note_input.clear()
        self.note_added.emit(text)

    def set_ai_enabled(self, enabled: bool) -> None:
        """Sem provedor de IA, perguntar à reunião fica indisponível.

        O campo de informar continua ativo: anexar contexto não depende de IA
        (é só texto guardado) e vale a pena registrar mesmo sem provedor.
        """
        self.ask_input.setEnabled(enabled)
        self.ask_btn.setEnabled(enabled)
