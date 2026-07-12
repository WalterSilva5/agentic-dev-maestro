"""Coach proativo no desktop: worker que gera a dica em thread e um card
flutuante (canto inferior direito) que a exibe de forma não intrusiva."""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from maestro_local.db.models import get_session
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t


class CoachWorker(QThread):
    """Monta o contexto e pede uma dica ao provedor de IA (fora da GUI)."""

    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, recent_tips: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._recent = list(recent_tips or [])

    def run(self) -> None:
        from maestro_local import coach
        s = get_session()
        try:
            context = coach.build_context(s)
        finally:
            s.close()
        try:
            self.done.emit(coach.generate_tip(context, self._recent))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class CoachTip(QFrame):
    """Card flutuante com a dica do agente + ações (abrir assistente / dispensar)."""

    def __init__(self, parent, on_open):
        super().__init__(parent)
        self.hide()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 12, 12)
        lay.setSpacing(6)

        head = QHBoxLayout()
        self._title = QLabel(t("💡 Dica do agente"))
        head.addWidget(self._title)
        head.addStretch()
        close = QPushButton("✕")
        close.setProperty("flat", True)
        close.setFixedSize(22, 22)
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.hide)
        head.addWidget(close)
        lay.addLayout(head)

        self._msg = QLabel("")
        self._msg.setWordWrap(True)
        self._msg.setMaximumWidth(340)
        lay.addWidget(self._msg)

        actions = QHBoxLayout()
        actions.addStretch()
        self._open = QPushButton(t("Abrir Assistente"))
        self._open.setProperty("flat", True)
        self._open.setCursor(Qt.PointingHandCursor)
        self._open.clicked.connect(lambda: (self.hide(), on_open()))
        actions.addWidget(self._open)
        lay.addLayout(actions)

    def show_tip(self, text: str, category: str = ""):
        th = current_theme()
        self.setStyleSheet(
            f"CoachTip {{ background: {th.bg_card}; border: 1px solid {th.accent}; "
            f"border-left: 4px solid {th.accent}; border-radius: 10px; }}")
        self._title.setStyleSheet(
            f"color: {th.text_primary}; font-weight: 700; border: none; background: transparent;")
        cat = f"  ·  {category}" if category else ""
        self._title.setText(t("💡 Dica do agente") + cat)
        self._msg.setStyleSheet(
            f"color: {th.text_secondary}; font-size: 12px; border: none; background: transparent;")
        self._msg.setText(text)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()

    def reposition(self):
        p = self.parent()
        if p:
            self.move(p.width() - self.width() - 20, p.height() - self.height() - 20)
