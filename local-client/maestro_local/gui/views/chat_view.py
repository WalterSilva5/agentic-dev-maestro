from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import get_active_ai_provider
from maestro_local.gui.theme import current_theme

SUGGESTIONS = [
    "Resuma o estado do board e o que priorizar hoje",
    "Solicite revisão das tarefas que estão em Fazendo",
    "Crie um TODO com os próximos passos",
    "O que foi feito nas últimas 24h?",
]


class AgentWorker(QThread):
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, history):
        super().__init__()
        self._history = history

    def run(self):
        try:
            from maestro_local.ai.agent import run_agent
            reply = run_agent(self._history)
            self.finished_ok.emit(reply or "(sem resposta)")
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class MessageBubble(QFrame):
    def __init__(self, role, text):
        super().__init__()
        t = current_theme()
        is_user = role == "user"
        bg = t.accent if is_user else t.bg_card
        fg = t.text_on_accent if is_user else t.text_primary
        self.setStyleSheet(
            f"MessageBubble {{ background: {bg}; border: 1px solid {t.border_light}; "
            f"border-radius: 10px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        who = QLabel("Você" if is_user else "Assistente")
        who.setStyleSheet(
            f"color: {fg}; font-size: 10px; font-weight: 700; opacity: 0.8; "
            f"background: transparent; border: none; text-transform: uppercase;"
        )
        lay.addWidget(who)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet(f"color: {fg}; font-size: 13px; background: transparent; border: none;")
        lay.addWidget(body)


class ChatView(QWidget):
    def __init__(self):
        super().__init__()
        self._history = []
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Chat estratégico")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.subtitle = QLabel(
            "Converse com o assistente interno: ele lê o board, sugere prioridades, "
            "solicita revisões, cria TODOs e comenta tarefas."
        )
        self.subtitle.setWordWrap(True)
        self.subtitle.setObjectName("subtitle")
        layout.addWidget(self.subtitle)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setVisible(False)
        layout.addWidget(self.banner)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.msgs_widget = QWidget()
        self.msgs_layout = QVBoxLayout(self.msgs_widget)
        self.msgs_layout.setSpacing(8)
        self.msgs_layout.setContentsMargins(0, 0, 0, 0)
        self.msgs_layout.addStretch()
        scroll.setWidget(self.msgs_widget)
        self._scroll = scroll
        layout.addWidget(scroll, 1)

        # Sugestões
        self.sug_row = QHBoxLayout()
        self.sug_row.setSpacing(6)
        for sug in SUGGESTIONS[:2]:
            self.sug_row.addWidget(self._make_suggestion(sug))
        layout.addLayout(self.sug_row)

        # Input
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Pergunte algo ou peça uma ação...")
        self.input.returnPressed.connect(self._send)
        input_row.addWidget(self.input, 1)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.setFixedHeight(34)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._send)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        self.refresh()

    def _make_suggestion(self, text):
        t = current_theme()
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"background: {t.bg_badge}; color: {t.text_secondary}; border: 1px solid {t.border}; "
            f"border-radius: 14px; padding: 4px 10px; font-size: 11px; text-align: left;"
        )
        btn.clicked.connect(lambda: self._fill_and_send(text))
        return btn

    def _fill_and_send(self, text):
        self.input.setText(text)
        self._send()

    def refresh(self):
        provider = get_active_ai_provider()
        t = current_theme()
        if not provider or not provider.get("model"):
            self.banner.setText(
                "⚠ Nenhum provedor de IA configurado. Vá em Configurações → Provedores de IA "
                "para definir o LM Studio ou outro provedor."
            )
            self.banner.setStyleSheet(
                f"background: {t.bg_badge}; color: {t.text_secondary}; border: 1px solid {t.border}; "
                f"border-radius: 8px; padding: 8px 12px; font-size: 12px;"
            )
            self.banner.setVisible(True)
            self.input.setEnabled(False)
            self.send_btn.setEnabled(False)
        else:
            self.banner.setVisible(False)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.subtitle.setText(
                f"Provedor ativo: {provider['name']} · modelo {provider['model']}"
            )

    def _add_bubble(self, role, text):
        bubble = MessageBubble(role, text)
        wrapper = QHBoxLayout()
        if role == "user":
            wrapper.addStretch()
            wrapper.addWidget(bubble, 4)
        else:
            wrapper.addWidget(bubble, 4)
            wrapper.addStretch()
        container = QWidget()
        container.setLayout(wrapper)
        self.msgs_layout.insertWidget(self.msgs_layout.count() - 1, container)
        QThread.msleep(1)
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _send(self):
        text = self.input.text().strip()
        if not text or (self._worker and self._worker.isRunning()):
            return
        self.input.clear()
        self._history.append({"role": "user", "content": text})
        self._add_bubble("user", text)

        self.send_btn.setEnabled(False)
        self.input.setEnabled(False)
        self._add_bubble("assistant", "Pensando...")
        self._thinking_container = self.msgs_layout.itemAt(self.msgs_layout.count() - 2).widget()

        self._worker = AgentWorker(list(self._history))
        self._worker.finished_ok.connect(self._on_reply)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    def _clear_thinking(self):
        if getattr(self, "_thinking_container", None):
            self._thinking_container.setParent(None)
            self._thinking_container.deleteLater()
            self._thinking_container = None

    def _on_reply(self, reply):
        self._clear_thinking()
        self._history.append({"role": "assistant", "content": reply})
        self._add_bubble("assistant", reply)
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()

    def _on_error(self, err):
        self._clear_thinking()
        self._add_bubble("assistant", f"⚠ Erro ao consultar o provedor de IA:\n{err}")
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
