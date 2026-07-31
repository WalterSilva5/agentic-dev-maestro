"""Indicador do fluxo da reunião: preparar → gravar → transcrever → analisar.

Um resumo compacto de onde a reunião está no processo, sem precisar ler o
status_label ou inferir pelo que está visível na tela. Puramente informativo
— não interage, só reflete o estado calculado pela view.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t

STAGES = ("preparar", "gravar", "transcrever", "analisar")

_STAGE_LABELS = {
    "preparar": lambda: t("Preparar"),
    "gravar": lambda: t("Gravar"),
    "transcrever": lambda: t("Transcrever"),
    "analisar": lambda: t("Analisar"),
}


class FlowIndicator(QWidget):
    """Barra horizontal com as 4 etapas; a atual e as concluídas se destacam."""

    def __init__(self, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self._dots: dict[str, QLabel] = {}
        self._labels: dict[str, QLabel] = {}
        self._connectors: list[QFrame] = []

        for i, stage in enumerate(STAGES):
            if i > 0:
                conn = QFrame()
                conn.setFrameShape(QFrame.HLine)
                conn.setFixedHeight(2)
                row.addWidget(conn, 1)
                self._connectors.append(conn)

            cell = QHBoxLayout()
            cell.setSpacing(6)
            dot = QLabel("●")
            dot.setFixedWidth(14)
            cell.addWidget(dot)
            label = QLabel(_STAGE_LABELS[stage]())
            cell.addWidget(label)
            row.addLayout(cell)
            self._dots[stage] = dot
            self._labels[stage] = label

        self._stage = "preparar"
        self._apply_styles()

    def set_stage(self, stage: str) -> None:
        """Marca `stage` como a etapa atual; as anteriores ficam "concluídas"."""
        if stage not in STAGES or stage == self._stage:
            return
        self._stage = stage
        self._apply_styles()

    def stage(self) -> str:
        return self._stage

    # ------------------------------------------------------------------
    def _apply_styles(self) -> None:
        """Três níveis visuais: concluída (cinza escuro), atual (accent, em
        destaque) e futura (cinza claro).

        A etapa concluída NÃO usa o verde de sucesso de propósito: com o accent
        teal da paleta, verde e teal ficam quase indistinguíveis lado a lado.
        Além disso, só a etapa atual em cor forte deixa o olho ir direto para
        onde a reunião está — o ✓ já carrega o "concluído".
        """
        th = current_theme()
        current_idx = STAGES.index(self._stage)
        for i, stage in enumerate(STAGES):
            dot, label = self._dots[stage], self._labels[stage]
            if i < current_idx:
                dot.setText("✓")
                color = th.text_secondary
                weight = 600
            elif i == current_idx:
                dot.setText("●")
                color = th.accent
                weight = 700
            else:
                dot.setText("○")
                color = th.text_muted
                weight = 500
            dot.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            label.setStyleSheet(
                f"color: {color}; font-weight: {weight}; font-size: 12px; "
                f"background: transparent; border: none;")
        for i, conn in enumerate(self._connectors):
            # conector i fica entre a etapa i e i+1
            done = i < current_idx
            conn.setStyleSheet(f"background: {th.border if done else th.border_light};")
