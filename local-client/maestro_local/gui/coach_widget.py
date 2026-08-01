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
        close.setFixedSize(22, 22)
        close.setCursor(Qt.PointingHandCursor)
        close.setToolTip(t("Dispensar"))
        # Estilo próprio: a classe "flat" do tema usa padding 8x16, que num
        # botão de 22x22 não deixa espaço e o ✕ some.
        self._close = close
        close.clicked.connect(self.hide)
        head.addWidget(close)
        lay.addLayout(head)

        self._msg = QLabel("")
        self._msg.setWordWrap(True)
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
        self._close.setStyleSheet(
            f"QPushButton {{ color: {th.text_muted}; background: transparent; "
            f"border: none; padding: 0; font-size: 13px; }} "
            f"QPushButton:hover {{ color: {th.text_primary}; }}")
        self._msg.setStyleSheet(
            f"color: {th.text_secondary}; font-size: 12px; border: none; background: transparent;")
        self._msg.setText(text)
        self.reposition()
        self.show()
        self.raise_()

    # Limites do card. Abaixo do mínimo o texto vira uma coluna ilegível;
    # acima do máximo a dica domina a janela.
    _LARGURA_MAX = 380
    _LARGURA_MIN = 240

    def reposition(self):
        """Redimensiona ao conteúdo/janela e reencosta no canto.

        A altura de um QLabel com quebra de linha depende da largura
        (heightForWidth) e o Qt não resolve isso sozinho ao dimensionar o pai —
        `adjustSize()` puro deixava o card baixo demais e cortava o texto.
        Por isso a largura é fixada primeiro e a altura calculada a partir dela.
        """
        pai = self.parent()
        if not pai:
            return
        largura = max(self._LARGURA_MIN,
                      min(self._LARGURA_MAX, pai.width() - 40))
        self.setFixedWidth(largura)

        m = self.layout().contentsMargins()
        util = largura - m.left() - m.right()
        self._msg.setFixedWidth(util)
        self._msg.setMinimumHeight(self._msg.heightForWidth(util))
        self.adjustSize()

        # Nunca sai da janela: em janela pequena, encosta no canto.
        self.move(max(0, pai.width() - self.width() - 20),
                  max(0, pai.height() - self.height() - 20))
