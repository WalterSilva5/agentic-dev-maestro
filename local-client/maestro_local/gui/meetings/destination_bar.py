"""Destino da reunião: workspace + projeto.

Fica no topo da tela porque define para onde a reunião e as tarefas geradas
vão. Os combos ignoram a roda do mouse — trocar de workspace/projeto sem
querer ao rolar a página é caro (o workspace troca o banco ativo).
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from maestro_local.gui.flow_layout import FlowLayout
from maestro_local.gui.no_wheel_combo import NoWheelComboBox
from maestro_local.i18n import t


class DestinationBar(QFrame):
    """Barra de destino. Emite os índices trocados; quem decide o que fazer
    (confirmar, mover a gravação, sincronizar a sidebar) é a view."""

    workspace_index_changed = Signal()
    project_index_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)

        row = FlowLayout(h_spacing=8, v_spacing=6)
        row.addWidget(QLabel(t("📁 Destino:")))

        self.ws_combo = NoWheelComboBox()
        self.ws_combo.setMinimumWidth(120)
        self.ws_combo.setToolTip(
            t("Workspace de destino da reunião. Troque aqui caso esteja gravando "
              "para o workspace errado.")
        )
        self.ws_combo.currentIndexChanged.connect(lambda _i: self.workspace_index_changed.emit())
        row.addWidget(self.ws_combo)

        row.addWidget(QLabel(t("Projeto:")))
        self.proj_combo = NoWheelComboBox()
        self.proj_combo.setMinimumWidth(130)
        self.proj_combo.currentIndexChanged.connect(lambda _i: self.project_index_changed.emit())
        row.addWidget(self.proj_combo)

        lay.addLayout(row)

        hint = QLabel(t("É para onde a reunião e as tarefas geradas vão."))
        hint.setObjectName("subtitle")
        lay.addWidget(hint)
