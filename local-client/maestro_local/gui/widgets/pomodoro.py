from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class PomodoroWidget(QFrame):
    def __init__(self):
        super().__init__()
        self._duration = 25 * 60
        self._remaining = self._duration
        self._running = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        self._icon = QLabel("🍅")
        self._icon.setFixedWidth(16)
        title_row.addWidget(self._icon)
        self._title = QLabel("Pomodoro")
        title_row.addWidget(self._title)
        title_row.addStretch()
        outer.addLayout(title_row)

        self._time_label = QLabel(self._fmt(self._remaining))
        self._time_label.setAlignment(Qt.AlignCenter)
        outer.addWidget(self._time_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn = QPushButton("▶  Iniciar")
        self._btn.setFixedHeight(26)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.clicked.connect(self._toggle)
        btn_row.addWidget(self._btn, 1)

        self._reset_btn = QPushButton("↺")
        self._reset_btn.setFixedSize(26, 26)
        self._reset_btn.setCursor(Qt.PointingHandCursor)
        self._reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(self._reset_btn)

        outer.addLayout(btn_row)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def _fmt(self, secs):
        return f"{secs // 60:02d}:{secs % 60:02d}"

    def _toggle(self):
        if self._running:
            self._timer.stop()
            self._running = False
            self._btn.setText("▶  Iniciar")
        else:
            self._timer.start()
            self._running = True
            self._btn.setText("⏸  Pausar")

    def _reset(self):
        self._timer.stop()
        self._running = False
        self._remaining = self._duration
        self._time_label.setText(self._fmt(self._remaining))
        self._btn.setText("▶  Iniciar")

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            self._running = False
            self._remaining = 0
            self._btn.setText("▶  Iniciar")
            self._time_label.setText("00:00")
            return
        self._time_label.setText(self._fmt(self._remaining))

    def set_duration_minutes(self, minutes: int):
        self._duration = minutes * 60
        if not self._running:
            self._remaining = self._duration
            self._time_label.setText(self._fmt(self._remaining))

    def apply_theme(self, t):
        self.setStyleSheet(
            f"PomodoroWidget {{ background: {t.bg_card}; "
            f"border: 1px solid {t.border}; border-radius: 8px; }}"
        )
        self._title.setStyleSheet(
            f"color: {t.text_muted}; font-size: 10px; font-weight: 600; "
            f"text-transform: uppercase; letter-spacing: 1px; background: transparent; border: none;"
        )
        self._icon.setStyleSheet("background: transparent; border: none;")
        self._time_label.setStyleSheet(
            f"color: {t.text_primary}; font-size: 22px; font-weight: 700; "
            f"font-family: monospace; background: transparent; border: none;"
        )
        self._btn.setStyleSheet(
            f"background: {t.accent}; color: white; border: none; border-radius: 6px; "
            f"font-size: 11px; font-weight: 600; padding: 0 8px;"
        )
        self._reset_btn.setStyleSheet(
            f"background: {t.bg_badge}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: 6px; font-size: 12px; padding: 0;"
        )
