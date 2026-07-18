"""Etapa 2 — Gravar.

O botão de gravar fica em destaque; as fontes de áudio (microfone, áudio do
sistema, observador de tela) ficam num bloco recolhível, com um resumo do que
está selecionado quando fechado.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.flow_layout import FlowLayout
from maestro_local.gui.meetings.section_card import SectionCard
from maestro_local.gui.no_wheel_combo import NoWheelComboBox
from maestro_local.i18n import t


class RecordingCard(SectionCard):
    record_toggled = Signal()
    live_toggled = Signal(bool)
    screen_watch_toggled = Signal(bool)
    audio_selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "2", t("Gravar"),
            t("Grave a reunião. Com o assistente ao vivo, plano/ações/decisões aparecem "
              "em tempo real; ao parar, a análise é gerada automaticamente."),
            parent)
        lay = self.body

        # --- Configurações de áudio (recolhidas por padrão) ---
        head = QHBoxLayout()
        head.setSpacing(8)
        self.audio_toggle = QToolButton()
        self.audio_toggle.setText(t("▸ Configurações de áudio"))
        self.audio_toggle.setCheckable(True)
        self.audio_toggle.setAutoRaise(True)
        self.audio_toggle.setCursor(Qt.PointingHandCursor)
        self.audio_toggle.toggled.connect(self._on_audio_toggled)
        head.addWidget(self.audio_toggle)
        self.audio_summary = QLabel("")
        self.audio_summary.setObjectName("subtitle")
        head.addWidget(self.audio_summary, 1)
        lay.addLayout(head)

        self.audio_box = QWidget()
        box = QVBoxLayout(self.audio_box)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)

        mic_row = QHBoxLayout()
        mic_row.setSpacing(8)
        mic_row.addWidget(QLabel(t("Microfone:")))
        self.mic_combo = NoWheelComboBox()
        self.mic_combo.currentIndexChanged.connect(
            lambda _i: self.audio_selection_changed.emit())
        mic_row.addWidget(self.mic_combo, 1)
        box.addLayout(mic_row)

        mon_row = QHBoxLayout()
        mon_row.setSpacing(8)
        mon_row.addWidget(QLabel(t("Áudio do sistema:")))
        self.monitor_combo = NoWheelComboBox()
        self.monitor_combo.currentIndexChanged.connect(
            lambda _i: self.audio_selection_changed.emit())
        mon_row.addWidget(self.monitor_combo, 1)
        box.addLayout(mon_row)

        screen_row = QHBoxLayout()
        screen_row.setSpacing(8)
        self.screen_watch_check = QCheckBox(t("👁 Assistente vê a tela"))
        self.screen_watch_check.setToolTip(
            t("Captura periodicamente o monitor selecionado e envia à IA para ajudar a "
              "resolver tarefas com base no que está na tela. Usa um provedor com visão e "
              "consome mais IA. Pode ligar/desligar a qualquer momento durante a reunião.")
        )
        self.screen_watch_check.toggled.connect(
            lambda on: self.screen_watch_toggled.emit(on))
        screen_row.addWidget(self.screen_watch_check)
        self.screen_combo = NoWheelComboBox()
        self.screen_combo.setMinimumWidth(150)
        screen_row.addWidget(self.screen_combo, 1)
        box.addLayout(screen_row)

        self.screen_watch_status = QLabel("")
        self.screen_watch_status.setObjectName("subtitle")
        self.screen_watch_status.setVisible(False)
        box.addWidget(self.screen_watch_status)

        self.audio_box.setVisible(False)
        lay.addWidget(self.audio_box)

        # --- Ação principal ---
        actions = FlowLayout(h_spacing=8, v_spacing=6)
        self.record_btn = QPushButton(t("● Gravar e transcrever"))
        self.record_btn.setFixedHeight(34)
        self.record_btn.setCursor(Qt.PointingHandCursor)
        self.record_btn.clicked.connect(lambda: self.record_toggled.emit())
        actions.addWidget(self.record_btn)

        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-family: monospace; font-size: 16px;")
        actions.addWidget(self.timer_label)

        self.live_check = QCheckBox(t("Assistente ao vivo"))
        self.live_check.setToolTip(
            t("Transcreve e extrai ações/decisões durante a gravação (mais uso de CPU/IA). "
              "Pode ser ligado/desligado a qualquer momento, inclusive no meio da gravação.")
        )
        self.live_check.toggled.connect(lambda on: self.live_toggled.emit(on))
        actions.addWidget(self.live_check)
        lay.addLayout(actions)

    # ------------------------------------------------------------------
    def _on_audio_toggled(self, on: bool) -> None:
        self.audio_box.setVisible(on)
        self.audio_toggle.setText(
            t("▾ Configurações de áudio") if on else t("▸ Configurações de áudio"))
        self.update_audio_summary()

    def update_audio_summary(self) -> None:
        """Resumo das fontes (visível só quando o bloco está recolhido)."""
        if self.audio_toggle.isChecked():
            self.audio_summary.setText("")
            return
        mic = self.mic_combo.currentText() if self.mic_combo.currentData() else t("Nenhum")
        mon = (self.monitor_combo.currentText()
               if self.monitor_combo.currentData() else t("Nenhum"))
        self.audio_summary.setText(
            t("🎙 {mic}  ·  🔊 {mon}").format(mic=mic[:28], mon=mon[:28]))
