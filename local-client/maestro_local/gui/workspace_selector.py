from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import (
    create_workspace,
    delete_workspace,
    get_active_workspace_id,
    list_workspaces,
    rename_workspace,
    set_active_workspace,
)
from maestro_local.gui.theme import current_theme


class WorkspaceItem(QFrame):
    clicked = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, ws: dict, is_active: bool):
        super().__init__()
        self._ws_id = ws["id"]
        self.setCursor(Qt.PointingHandCursor)

        t = current_theme()

        bg = t.bg_selected if is_active else "transparent"
        border = t.accent if is_active else "transparent"
        self.setStyleSheet(
            f"WorkspaceItem {{ background: {bg}; border: 1px solid {border}; "
            f"border-radius: 8px; padding: 4px; }}"
            f"WorkspaceItem:hover {{ background: {t.bg_hover}; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        icon_label = QLabel(ws.get("icon", "W"))
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_bg = t.accent if is_active else t.bg_badge
        icon_fg = t.text_on_accent if is_active else t.text_secondary
        icon_label.setStyleSheet(
            f"background: {icon_bg}; color: {icon_fg}; "
            f"font-size: 14px; font-weight: 700; border-radius: 8px; border: none;"
        )
        layout.addWidget(icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        name_label = QLabel(ws["name"])
        name_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {t.text_primary}; border: none;"
        )
        text_col.addWidget(name_label)

        id_label = QLabel(ws["id"])
        id_label.setStyleSheet(
            f"font-size: 10px; color: {t.text_muted}; border: none;"
        )
        text_col.addWidget(id_label)
        layout.addLayout(text_col, 1)

        if is_active:
            active_dot = QLabel("●")
            active_dot.setStyleSheet(
                f"color: {t.success}; font-size: 14px; border: none;"
            )
            layout.addWidget(active_dot)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._ws_id)
        super().mousePressEvent(event)


class CreateWorkspaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Workspace")
        self.setFixedSize(380, 200)

        t = current_theme()
        self.setStyleSheet(
            f"QDialog {{ background: {t.bg_card}; color: {t.text_primary}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Criar novo workspace")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {t.text_primary};")
        layout.addWidget(title)

        name_label = QLabel("Nome")
        name_label.setStyleSheet(f"font-size: 12px; color: {t.text_muted}; font-weight: 600;")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Trabalho, Estudos, Pessoal...")
        layout.addWidget(self.name_input)

        icon_row = QHBoxLayout()
        icon_label = QLabel("Icone (1 caractere)")
        icon_label.setStyleSheet(f"font-size: 12px; color: {t.text_muted}; font-weight: 600;")
        icon_row.addWidget(icon_label)
        self.icon_input = QLineEdit()
        self.icon_input.setFixedWidth(50)
        self.icon_input.setMaxLength(2)
        self.icon_input.setAlignment(Qt.AlignCenter)
        self.icon_input.setText("W")
        icon_row.addWidget(self.icon_input)
        icon_row.addStretch()
        layout.addLayout(icon_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setProperty("flat", True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        create_btn = QPushButton("Criar")
        create_btn.clicked.connect(self._on_create)
        btn_row.addWidget(create_btn)
        layout.addLayout(btn_row)

        self.result_ws = None

    def _on_create(self):
        name = self.name_input.text().strip()
        if not name:
            return
        icon = self.icon_input.text().strip() or name[0].upper()
        self.result_ws = create_workspace(name, icon)
        self.accept()


class WorkspaceSelectorPopup(QDialog):
    workspace_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        t = current_theme()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setStyleSheet(
            f"QFrame#wsContainer {{ background: {t.bg_card}; "
            f"border: 1px solid {t.border}; border-radius: 12px; }}"
        )
        container.setObjectName("wsContainer")
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(8, 12, 8, 12)
        self.container_layout.setSpacing(4)

        # Header
        header = QLabel("Workspaces")
        header.setStyleSheet(
            f"font-weight: 700; font-size: 12px; color: {t.text_muted}; "
            f"letter-spacing: 1px; padding: 4px 8px; border: none;"
        )
        self.container_layout.addWidget(header)

        # Workspace list
        self.ws_list_layout = QVBoxLayout()
        self.ws_list_layout.setSpacing(2)
        self.container_layout.addLayout(self.ws_list_layout)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {t.border_light};")
        self.container_layout.addWidget(sep)

        # Create button
        create_btn = QPushButton("  +   Novo workspace")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {t.text_secondary}; "
            f"border: none; border-radius: 8px; padding: 10px 10px; "
            f"font-size: 13px; text-align: left; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; color: {t.text_primary}; }}"
        )
        create_btn.clicked.connect(self._create_workspace)
        self.container_layout.addWidget(create_btn)

        # Manage button
        manage_btn = QPushButton("  ⚙   Gerenciar workspaces")
        manage_btn.setCursor(Qt.PointingHandCursor)
        manage_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {t.text_muted}; "
            f"border: none; border-radius: 8px; padding: 8px 10px; "
            f"font-size: 12px; text-align: left; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; color: {t.text_primary}; }}"
        )
        manage_btn.clicked.connect(self._manage_workspaces)
        self.container_layout.addWidget(manage_btn)

        outer.addWidget(container)

        self._populate()

    def _populate(self):
        while self.ws_list_layout.count():
            item = self.ws_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active_id = get_active_workspace_id()
        for ws in list_workspaces():
            item = WorkspaceItem(ws, ws["id"] == active_id)
            item.clicked.connect(self._switch_workspace)
            self.ws_list_layout.addWidget(item)

    def _switch_workspace(self, ws_id: str):
        if ws_id == get_active_workspace_id():
            self.close()
            return
        set_active_workspace(ws_id)
        self.workspace_changed.emit(ws_id)
        self.close()

    def _create_workspace(self):
        self.close()
        dlg = CreateWorkspaceDialog(self.parent())
        if dlg.exec() == QDialog.Accepted and dlg.result_ws:
            ws_id = dlg.result_ws["id"]
            set_active_workspace(ws_id)
            self.workspace_changed.emit(ws_id)

    def _manage_workspaces(self):
        self.close()
        dlg = ManageWorkspacesDialog(self.parent())
        dlg.workspace_changed.connect(self.workspace_changed.emit)
        dlg.exec()


class ManageWorkspacesDialog(QDialog):
    workspace_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar Workspaces")
        self.setMinimumSize(450, 350)

        t = current_theme()
        self.setStyleSheet(
            f"QDialog {{ background: {t.bg_card}; color: {t.text_primary}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Gerenciar Workspaces")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        hint = QLabel("Cada workspace tem seu proprio banco de dados isolado.")
        hint.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(6)
        layout.addLayout(self.items_layout)
        layout.addStretch()

        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

        self._populate()

    def _populate(self):
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t = current_theme()
        active_id = get_active_workspace_id()
        workspaces = list_workspaces()

        for ws in workspaces:
            row = QFrame()
            row.setStyleSheet(
                f"QFrame {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
                f"border-radius: 8px; padding: 8px; }}"
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)
            row_layout.setSpacing(10)

            icon_lbl = QLabel(ws.get("icon", "W"))
            icon_lbl.setFixedSize(28, 28)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet(
                f"background: {t.accent}; color: {t.text_on_accent}; "
                f"font-size: 12px; font-weight: 700; border-radius: 7px; border: none;"
            )
            row_layout.addWidget(icon_lbl)

            name_lbl = QLabel(ws["name"])
            name_lbl.setStyleSheet(
                f"font-weight: 600; font-size: 13px; border: none;"
            )
            row_layout.addWidget(name_lbl)

            if ws["id"] == active_id:
                active_badge = QLabel("ativo")
                active_badge.setStyleSheet(
                    f"background: {t.success}; color: white; padding: 2px 8px; "
                    f"border-radius: 6px; font-size: 10px; font-weight: 600; border: none;"
                )
                row_layout.addWidget(active_badge)

            row_layout.addStretch()

            rename_btn = QPushButton("Renomear")
            rename_btn.setFixedHeight(26)
            rename_btn.setStyleSheet(
                f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
                f"border: 1px solid {t.border}; border-radius: 6px; padding: 3px 10px; "
                f"font-size: 11px; }}"
                f"QPushButton:hover {{ background: {t.bg_hover}; }}"
            )
            ws_id = ws["id"]
            ws_name = ws["name"]
            rename_btn.clicked.connect(lambda _, wid=ws_id, wname=ws_name: self._rename(wid, wname))
            row_layout.addWidget(rename_btn)

            if len(workspaces) > 1:
                del_btn = QPushButton("Excluir")
                del_btn.setFixedHeight(26)
                del_btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {t.danger}; "
                    f"border: 1px solid {t.danger}; border-radius: 6px; padding: 3px 10px; "
                    f"font-size: 11px; }}"
                    f"QPushButton:hover {{ background: {t.danger}; color: white; }}"
                )
                del_btn.clicked.connect(lambda _, wid=ws_id, wname=ws_name: self._delete(wid, wname))
                row_layout.addWidget(del_btn)

            self.items_layout.addWidget(row)

    def _rename(self, ws_id, current_name):
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "Renomear workspace", "Novo nome:", text=current_name
        )
        if ok and new_name.strip():
            rename_workspace(ws_id, new_name.strip())
            self._populate()
            self.workspace_changed.emit(get_active_workspace_id())

    def _delete(self, ws_id, name):
        r = QMessageBox.warning(
            self, "Excluir workspace",
            f'Tem certeza que deseja excluir "{name}"?\n\n'
            f"Todos os dados (projetos, tarefas, notas) serao perdidos permanentemente.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if r == QMessageBox.Yes:
            active_id = get_active_workspace_id()
            deleted_active = ws_id == active_id
            delete_workspace(ws_id)
            self._populate()
            if deleted_active:
                new_active = get_active_workspace_id()
                self.workspace_changed.emit(new_active)


class WorkspaceSelectorButton(QWidget):
    """Obsidian-style workspace selector button for the sidebar."""
    workspace_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(48)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 6, 12, 6)
        self._layout.setSpacing(8)

        self._icon = QLabel()
        self._icon.setFixedSize(28, 28)
        self._icon.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._icon)

        self._name = QLabel()
        self._name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._layout.addWidget(self._name)

        self._chevron = QLabel("▾")
        self._layout.addWidget(self._chevron)

        self._update_display()

    def _update_display(self):
        t = current_theme()
        active_id = get_active_workspace_id()
        ws_list = list_workspaces()
        active = next((w for w in ws_list if w["id"] == active_id), None)

        if not active:
            active = {"name": "Default", "icon": "A"}

        self._icon.setText(active.get("icon", "W"))
        self._icon.setStyleSheet(
            f"background: {t.accent}; color: {t.text_on_accent}; "
            f"font-size: 12px; font-weight: 700; border-radius: 7px;"
        )
        self._name.setText(active["name"])
        self._name.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {t.text_primary};"
        )
        self._chevron.setStyleSheet(
            f"color: {t.text_muted}; font-size: 10px;"
        )
        self.setStyleSheet(
            f"WorkspaceSelectorButton {{ background: transparent; "
            f"border: 1px solid transparent; border-radius: 8px; }}"
            f"WorkspaceSelectorButton:hover {{ background: {t.bg_hover}; "
            f"border: 1px solid {t.border_light}; }}"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            popup = WorkspaceSelectorPopup(self)
            popup.workspace_changed.connect(self._on_workspace_changed)
            pos = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(pos.x(), pos.y() + 4)
            popup.show()
        super().mousePressEvent(event)

    def _on_workspace_changed(self, ws_id):
        self._update_display()
        self.workspace_changed.emit(ws_id)

    def refresh_display(self):
        self._update_display()
