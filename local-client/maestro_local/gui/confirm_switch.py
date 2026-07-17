"""Confirmação ao trocar de ambiente (workspace).

Trocar de workspace troca o banco ativo e recarrega todas as telas — é uma ação
com efeito amplo, então pede um OK explícito em vez de acontecer num clique solto.
"""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from maestro_local.config import list_workspaces
from maestro_local.i18n import t


def _workspace_name(ws_id: str) -> str:
    ws = next((w for w in list_workspaces() if w.get("id") == ws_id), None)
    return (ws or {}).get("name") or ws_id


def confirm_workspace_switch(parent, ws_id: str) -> bool:
    """Pergunta antes de trocar de workspace. True = usuário confirmou."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(t("Trocar de workspace"))
    box.setText(t("Trocar para o workspace “{name}”?").format(name=_workspace_name(ws_id)))
    box.setInformativeText(
        t("As telas serão recarregadas com os dados desse workspace."))
    ok = box.addButton(QMessageBox.Ok)
    box.addButton(QMessageBox.Cancel)
    box.setDefaultButton(ok)
    box.exec()
    return box.clickedButton() is ok
