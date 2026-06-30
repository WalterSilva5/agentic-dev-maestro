from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from maestro_local.i18n import t as _t


class TranscricoesQuickWidget(QFrame):
    """Acesso rápido às Transcrições na sidebar: inicia/para gravação em 1 clique."""

    toggle_requested = Signal()
    open_requested = Signal()

    def __init__(self):
        super().__init__()
        self._recording = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        self._icon = QLabel("🎙")
        self._icon.setFixedWidth(16)
        title_row.addWidget(self._icon)
        self._title = QLabel(_t("Transcrições"))
        title_row.addWidget(self._title)
        title_row.addStretch()
        self._open_btn = QPushButton(_t("abrir"))
        self._open_btn.setCursor(Qt.PointingHandCursor)
        self._open_btn.clicked.connect(self.open_requested.emit)
        title_row.addWidget(self._open_btn)
        outer.addLayout(title_row)

        self._time_label = QLabel("00:00")
        self._time_label.setAlignment(Qt.AlignCenter)
        outer.addWidget(self._time_label)

        self._btn = QPushButton("●  " + _t("Gravar"))
        self._btn.setFixedHeight(28)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.clicked.connect(self.toggle_requested.emit)
        outer.addWidget(self._btn)

    def set_recording(self, recording: bool, elapsed_seconds: int = 0):
        self._recording = recording
        m, s = divmod(int(elapsed_seconds), 60)
        self._time_label.setText(f"{m:02d}:{s:02d}")
        self._btn.setText("■  " + _t("Parar") if recording else "●  " + _t("Gravar"))
        self._apply_btn_style()

    def _apply_btn_style(self):
        if not hasattr(self, "_t"):
            return
        t = self._t
        if self._recording:
            bg = getattr(t, "danger", "#D32F2F")
        else:
            bg = t.accent
        self._btn.setStyleSheet(
            f"background: {bg}; color: white; border: none; border-radius: 6px; "
            f"font-size: 12px; font-weight: 600; padding: 0 8px;"
        )

    def apply_theme(self, t):
        self._t = t
        self.setStyleSheet(
            f"TranscricoesQuickWidget {{ background: {t.bg_card}; "
            f"border: 1px solid {t.border}; border-radius: 8px; }}"
        )
        self._title.setStyleSheet(
            f"color: {t.text_muted}; font-size: 10px; font-weight: 600; "
            f"text-transform: uppercase; letter-spacing: 1px; background: transparent; border: none;"
        )
        self._icon.setStyleSheet("background: transparent; border: none;")
        self._open_btn.setStyleSheet(
            f"color: {t.text_muted}; font-size: 10px; background: transparent; border: none;"
        )
        self._time_label.setStyleSheet(
            f"color: {t.text_primary}; font-size: 22px; font-weight: 700; "
            f"font-family: monospace; background: transparent; border: none;"
        )
        self._apply_btn_style()
