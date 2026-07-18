"""Etapa 1 — Preparar.

Entradas que o usuário monta ANTES de gravar: tipo da sessão, tópico (estudo),
pauta e contexto anexado. É o que faz o assistente começar já sabendo do que a
reunião se trata.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.flow_layout import FlowLayout
from maestro_local.gui.meetings.section_card import SectionCard
from maestro_local.gui.no_wheel_combo import NoWheelComboBox
from maestro_local.i18n import t


class PreparationCard(SectionCard):
    kind_changed = Signal()
    add_file_requested = Signal()
    capture_screen_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "1", t("Preparar"),
            t("Descreva a pauta e anexe contexto ANTES de gravar — assim o assistente "
              "já começa sabendo do que se trata. Opcional."),
            parent)
        lay = self.body

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(t("Tipo:")))
        self.kind_combo = NoWheelComboBox()
        self.kind_combo.addItem(t("Reunião"), "meeting")
        self.kind_combo.addItem(t("Estudo"), "study")
        self.kind_combo.currentIndexChanged.connect(lambda _i: self.kind_changed.emit())
        row.addWidget(self.kind_combo)
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText(t("Tópico do estudo"))
        self.topic_input.setVisible(False)
        row.addWidget(self.topic_input, 1)
        lay.addLayout(row)

        self.prep_edit = QTextEdit()
        self.prep_edit.setPlaceholderText(
            t("Pauta, objetivos, participantes, decisões esperadas, links… "
              "O assistente usa isto como base para já começar preparado.")
        )
        self.prep_edit.setMaximumHeight(84)
        lay.addWidget(self.prep_edit)

        # Contexto adicional (arquivos/imagens/captura de tela)
        ctx_row = FlowLayout(h_spacing=8, v_spacing=6)
        self.context_btn = QToolButton()
        self.context_btn.setText(t("➕ Adicionar contexto"))
        self.context_btn.setCursor(Qt.PointingHandCursor)
        self.context_btn.setPopupMode(QToolButton.InstantPopup)
        self.context_btn.setToolTip(
            t("Anexa arquivos (imagem, PDF, texto…) ou uma captura de tela como contexto "
              "para o assistente da reunião. Pode ser usado a qualquer momento.")
        )
        menu = QMenu(self.context_btn)
        menu.addAction(t("Arquivo (imagem, PDF, texto…)"),
                       lambda: self.add_file_requested.emit())
        menu.addAction(t("Capturar tela"),
                       lambda: self.capture_screen_requested.emit())
        self.context_btn.setMenu(menu)
        ctx_row.addWidget(self.context_btn)

        self.context_summary = QLabel(t("Nenhum contexto adicionado"))
        self.context_summary.setObjectName("subtitle")
        ctx_row.addWidget(self.context_summary)
        lay.addLayout(ctx_row)

        # Chips dos itens de contexto (preenchidos pela view)
        self.context_container = QWidget()
        self.context_layout = QVBoxLayout(self.context_container)
        self.context_layout.setContentsMargins(0, 0, 0, 0)
        self.context_layout.setSpacing(4)
        self.context_container.setVisible(False)
        lay.addWidget(self.context_container)

    # ------------------------------------------------------------------
    def kind(self) -> str:
        return self.kind_combo.currentData()

    def set_study_mode(self, is_study: bool) -> None:
        """No modo estudo aparece o campo de tópico."""
        self.topic_input.setVisible(is_study)
