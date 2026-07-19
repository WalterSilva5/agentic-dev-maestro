"""Etapa 3 — Resultado.

Transcrição (editável), resumo da IA e a barra de ações agrupada. Os campos
vêm antes da barra porque as ações agem sobre eles; o toggle de visualização
fica no cabeçalho do resumo, junto do campo que controla.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget,
)

from maestro_local.gui.flow_layout import FlowLayout
from maestro_local.gui.meetings.section_card import SectionCard
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t


def _vsep() -> QFrame:
    """Separador vertical entre grupos da barra de ações."""
    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setFixedSize(1, 24)
    sep.setStyleSheet(f"color: {current_theme().border};")
    return sep


def action_group(label: str, buttons: list) -> QWidget:
    """Grupo rotulado de botões, num container próprio para quebrar como
    unidade em telas estreitas (o rótulo nunca se separa dos seus botões)."""
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    row.addWidget(_vsep())
    lbl = QLabel(label)
    lbl.setObjectName("subtitle")
    row.addWidget(lbl)
    for b in buttons:
        row.addWidget(b)
    return w


class ResultCard(SectionCard):
    transcript_edited = Signal()
    md_view_toggled = Signal()
    analyze_requested = Signal()
    export_requested = Signal()
    copy_requested = Signal()
    tasks_requested = Signal()
    save_day_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "3", t("Resultado"),
            t("Corrija a transcrição se precisar — o agente revisa os itens sozinho. "
              "Depois, use o resumo e mande as ações para o board."),
            parent)
        lay = self.body

        # --- Transcrição (editável) ---
        self.transcript_label = QLabel(t("Transcrição:"))
        lay.addWidget(self.transcript_label)
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText(t("A transcrição aparecerá aqui..."))
        self.transcript_edit.setMinimumHeight(120)
        self.transcript_edit.setToolTip(
            t("Você pode corrigir a transcrição a qualquer momento — o agente revisa "
              "os itens automaticamente após a edição."))
        self.transcript_edit.textChanged.connect(lambda: self.transcript_edited.emit())
        lay.addWidget(self.transcript_edit, 1)

        # --- Resumo (IA) + toggle de visualização ---
        head = QHBoxLayout()
        head.setSpacing(8)
        self.summary_label = QLabel(t("Resumo (IA):"))
        head.addWidget(self.summary_label)
        head.addStretch()
        self.md_view_btn = QPushButton(t("👁 Visualizar"))
        self.md_view_btn.setProperty("flat", "true")
        self.md_view_btn.setFixedHeight(28)
        self.md_view_btn.setCursor(Qt.PointingHandCursor)
        self.md_view_btn.setToolTip(
            t("Alterna entre o código Markdown e a visualização formatada do resumo."))
        self.md_view_btn.clicked.connect(lambda: self.md_view_toggled.emit())
        head.addWidget(self.md_view_btn)
        lay.addLayout(head)

        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText(
            t("O resumo estruturado aparecerá aqui após a análise."))
        self.result_edit.setMinimumHeight(120)
        self.result_edit.setVisible(False)
        lay.addWidget(self.result_edit, 1)

        # --- Barra de ações agrupada ---
        #   [Analisar] │ Documento: Exportar/Copiar │ Enviar para: tarefas/Meu Dia
        actions = FlowLayout(h_spacing=8, v_spacing=6)

        self.analyze_btn = QPushButton(t("↻ Analisar com IA"))
        self.analyze_btn.setFixedHeight(32)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.setToolTip(
            t("Gera o resumo e os itens de novo a partir da transcrição atual."))
        self.analyze_btn.clicked.connect(lambda: self.analyze_requested.emit())
        actions.addWidget(self.analyze_btn)

        self.export_btn = QPushButton(t("Exportar (.md)"))
        self.export_btn.setProperty("flat", "true")
        self.export_btn.setFixedHeight(32)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setToolTip(
            t("Exporta um markdown único com todos os itens de todas as abas + transcrição."))
        self.export_btn.clicked.connect(lambda: self.export_requested.emit())
        self.copy_btn = QPushButton(t("Copiar (.md)"))
        self.copy_btn.setProperty("flat", "true")
        self.copy_btn.setFixedHeight(32)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setToolTip(
            t("Copia o markdown completo da reunião para a área de transferência."))
        self.copy_btn.clicked.connect(lambda: self.copy_requested.emit())
        actions.addWidget(action_group(t("Documento:"), [self.export_btn, self.copy_btn]))

        self.tasks_btn = QPushButton(t("Criar tarefas das ações"))
        self.tasks_btn.setFixedHeight(32)
        self.tasks_btn.setCursor(Qt.PointingHandCursor)
        self.tasks_btn.clicked.connect(lambda: self.tasks_requested.emit())
        self.save_day_btn = QPushButton(t("Meu Dia"))
        self.save_day_btn.setProperty("flat", "true")
        self.save_day_btn.setFixedHeight(32)
        self.save_day_btn.setCursor(Qt.PointingHandCursor)
        self.save_day_btn.setToolTip(t("Adiciona o resumo ao relatório do Meu Dia."))
        self.save_day_btn.clicked.connect(lambda: self.save_day_requested.emit())
        self.save_day_btn.setEnabled(False)
        actions.addWidget(action_group(t("Enviar para:"),
                                       [self.tasks_btn, self.save_day_btn]))
        lay.addLayout(actions)

    # ------------------------------------------------------------------
    def set_md_preview(self, preview: bool) -> None:
        """Ajusta o rótulo do toggle conforme o modo do resumo."""
        self.md_view_btn.setText(t("✎ Código") if preview else t("👁 Visualizar"))
