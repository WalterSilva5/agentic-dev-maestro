from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import load_config, save_config
from maestro_local.gui.theme import current_theme


class SettingsView(QWidget):
    notification_changed = Signal()

    def __init__(self):
        super().__init__()
        self._loading = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        title = QLabel("Configurações")
        title.setObjectName("sectionTitle")
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Configurações gerais da aplicação — pomodoro, notificações e preferências."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")
        main_layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        self._build_pomodoro_section()
        self._build_notification_section()

        self.cards_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        self._load_settings()

    def _make_card(self, icon, title_text):
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)

        badge = QLabel(icon)
        badge.setFixedSize(32, 32)
        badge.setAlignment(Qt.AlignCenter)
        t = current_theme()
        badge.setStyleSheet(
            f"background: {t.accent}; color: {t.text_on_accent}; "
            f"border-radius: 16px; font-size: 14px; font-weight: 800; border: none;"
        )
        header.addWidget(badge)

        heading = QLabel(title_text)
        heading.setProperty("class", "cardTitle")
        header.addWidget(heading)
        header.addStretch()

        layout.addLayout(header)
        self.cards_layout.addWidget(card)
        return card, layout

    def _build_pomodoro_section(self):
        card, layout = self._make_card("🍅", "Pomodoro")

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Duração da sessão (minutos):"))
        self.pomodoro_duration = QSpinBox()
        self.pomodoro_duration.setRange(1, 120)
        self.pomodoro_duration.setValue(25)
        self.pomodoro_duration.setFixedWidth(80)
        self.pomodoro_duration.valueChanged.connect(self._save_settings)
        row.addWidget(self.pomodoro_duration)
        row.addStretch()
        layout.addLayout(row)

    def _build_notification_section(self):
        card, layout = self._make_card("🔔", "Notificações push")

        desc = QLabel(
            "Envia notificações periódicas na área de trabalho com uma mensagem personalizada. "
            "Útil para lembretes de pausas, check-ins ou qualquer lembrete recorrente."
        )
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        self.notif_enabled = QCheckBox("Ativar notificações periódicas")
        self.notif_enabled.toggled.connect(self._on_notif_toggled)
        layout.addWidget(self.notif_enabled)

        self.notif_settings_frame = QFrame()
        notif_inner = QVBoxLayout(self.notif_settings_frame)
        notif_inner.setContentsMargins(0, 4, 0, 0)
        notif_inner.setSpacing(8)

        interval_row = QHBoxLayout()
        interval_row.setSpacing(8)
        interval_row.addWidget(QLabel("Intervalo (minutos):"))
        self.notif_interval = QSpinBox()
        self.notif_interval.setRange(1, 480)
        self.notif_interval.setValue(30)
        self.notif_interval.setFixedWidth(80)
        self.notif_interval.valueChanged.connect(self._save_settings)
        interval_row.addWidget(self.notif_interval)
        interval_row.addStretch()
        notif_inner.addLayout(interval_row)

        msg_row = QVBoxLayout()
        msg_row.setSpacing(4)
        msg_row.addWidget(QLabel("Mensagem:"))
        self.notif_message = QLineEdit()
        self.notif_message.setPlaceholderText("Ex: Hora de fazer um check-in no Maestro!")
        self.notif_message.setText("Hora de verificar suas tarefas no Maestro!")
        self.notif_message.textChanged.connect(self._save_settings)
        msg_row.addWidget(self.notif_message)
        notif_inner.addLayout(msg_row)

        self.notif_settings_frame.setVisible(False)
        layout.addWidget(self.notif_settings_frame)

    def _on_notif_toggled(self, checked):
        self.notif_settings_frame.setVisible(checked)
        self._save_settings()

    def _load_settings(self):
        self._loading = True
        cfg = load_config()
        settings = cfg.get("settings", {})

        self.pomodoro_duration.setValue(settings.get("pomodoro_minutes", 25))

        notif = settings.get("notifications", {})
        self.notif_enabled.setChecked(notif.get("enabled", False))
        self.notif_interval.setValue(notif.get("interval_minutes", 30))
        msg = notif.get("message", "Hora de verificar suas tarefas no Maestro!")
        self.notif_message.setText(msg)
        self.notif_settings_frame.setVisible(self.notif_enabled.isChecked())
        self._loading = False

    def _save_settings(self):
        if self._loading:
            return
        cfg = load_config()
        cfg["settings"] = {
            "pomodoro_minutes": self.pomodoro_duration.value(),
            "notifications": {
                "enabled": self.notif_enabled.isChecked(),
                "interval_minutes": self.notif_interval.value(),
                "message": self.notif_message.text(),
            },
        }
        save_config(cfg)
        self.notification_changed.emit()

    def get_notification_settings(self):
        return {
            "enabled": self.notif_enabled.isChecked(),
            "interval_minutes": self.notif_interval.value(),
            "message": self.notif_message.text(),
        }

    def refresh(self):
        self._load_settings()
