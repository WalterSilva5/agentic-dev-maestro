from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import (
    create_workspace,
    delete_workspace,
    get_active_workspace_id,
    list_workspaces,
    set_active_workspace,
    update_workspace,
)
from maestro_local.gui.theme import current_theme

WORKSPACE_COLORS = [
    "#4C5FD0", "#7B8DFF", "#2196F3", "#0097A7",
    "#1E8A4A", "#66BB6A", "#8BC34A", "#CDDC39",
    "#F9A825", "#FF9800", "#FF5722", "#D1242F",
    "#E91E63", "#9C27B0", "#673AB7", "#795548",
]

ICON_EMOJIS = [
    "🚀", "💼", "🏠", "📦", "🎯", "🔬", "📚", "🎨",
    "⚡", "🔧", "🌐", "🛡️", "🎮", "📊", "🧪", "💡",
    "🏗️", "📱", "🖥️", "🤖", "🌱", "🔥", "⭐", "🎵",
]


class WorkspaceItem(QFrame):
    clicked = Signal(str)

    def __init__(self, ws: dict, is_active: bool):
        super().__init__()
        self._ws_id = ws["id"]
        self.setCursor(Qt.PointingHandCursor)

        t = current_theme()
        ws_color = ws.get("color") or t.accent

        bg = t.bg_selected if is_active else "transparent"
        border = ws_color if is_active else "transparent"
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
        icon_bg = ws_color if is_active else t.bg_badge
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

        desc = ws.get("description", "")
        if desc:
            desc_label = QLabel(desc if len(desc) <= 40 else desc[:37] + "...")
            desc_label.setStyleSheet(
                f"font-size: 10px; color: {t.text_muted}; border: none;"
            )
            text_col.addWidget(desc_label)
        else:
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


class _IconColorSection(QWidget):
    """Reusable icon + color picker grid."""

    def __init__(self, initial_icon="W", initial_color=""):
        super().__init__()
        t = current_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # --- Icon ---
        icon_header = QHBoxLayout()
        icon_lbl = QLabel("Icone")
        icon_lbl.setStyleSheet(f"font-size: 12px; color: {t.text_muted}; font-weight: 600;")
        icon_header.addWidget(icon_lbl)

        self.icon_input = QLineEdit()
        self.icon_input.setFixedWidth(50)
        self.icon_input.setMaxLength(2)
        self.icon_input.setAlignment(Qt.AlignCenter)
        self.icon_input.setText(initial_icon)
        icon_header.addWidget(self.icon_input)
        icon_header.addStretch()
        layout.addLayout(icon_header)

        emoji_grid = QGridLayout()
        emoji_grid.setSpacing(4)
        for i, emoji in enumerate(ICON_EMOJIS):
            btn = QPushButton(emoji)
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
                f"border-radius: 6px; font-size: 15px; padding: 0; }}"
                f"QPushButton:hover {{ background: {t.bg_hover}; border-color: {t.border}; }}"
            )
            btn.clicked.connect(lambda _, e=emoji: self.icon_input.setText(e))
            emoji_grid.addWidget(btn, i // 8, i % 8)
        layout.addLayout(emoji_grid)

        # --- Color ---
        color_lbl = QLabel("Cor do workspace")
        color_lbl.setStyleSheet(f"font-size: 12px; color: {t.text_muted}; font-weight: 600;")
        layout.addWidget(color_lbl)

        self.selected_color = initial_color
        self._color_btns = []

        color_grid = QGridLayout()
        color_grid.setSpacing(4)
        for i, c in enumerate(WORKSPACE_COLORS):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, clr=c: self._select_color(clr))
            self._color_btns.append((btn, c))
            color_grid.addWidget(btn, i // 8, i % 8)
        layout.addLayout(color_grid)

        self._update_color_styles()

    def _select_color(self, color):
        self.selected_color = color
        self._update_color_styles()

    def _update_color_styles(self):
        t = current_theme()
        for btn, c in self._color_btns:
            border = f"3px solid {t.text_primary}" if c == self.selected_color else "2px solid transparent"
            btn.setStyleSheet(
                f"background: {c}; border-radius: 14px; border: {border}; min-height: 0;"
            )

    def get_icon(self) -> str:
        return self.icon_input.text().strip() or "W"

    def get_color(self) -> str:
        return self.selected_color


class CreateWorkspaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Workspace")
        self.setMinimumSize(420, 460)

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

        # Name
        name_label = QLabel("Nome")
        name_label.setStyleSheet(f"font-size: 12px; color: {t.text_muted}; font-weight: 600;")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Trabalho, Estudos, Pessoal...")
        layout.addWidget(self.name_input)

        # Description
        desc_label = QLabel("Descricao (opcional)")
        desc_label.setStyleSheet(f"font-size: 12px; color: {t.text_muted}; font-weight: 600;")
        layout.addWidget(desc_label)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Descreva o proposito deste workspace...")
        layout.addWidget(self.desc_input)

        # Icon & Color
        self.icon_color = _IconColorSection()
        layout.addWidget(self.icon_color)

        # Buttons
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
        icon = self.icon_color.get_icon() or name[0].upper()
        color = self.icon_color.get_color()
        desc = self.desc_input.text().strip()
        self.result_ws = create_workspace(name, icon, description=desc, color=color)
        self.accept()


class EditWorkspaceDialog(QDialog):
    def __init__(self, ws: dict, parent=None):
        super().__init__(parent)
        self._ws_id = ws["id"]
        self.setWindowTitle(f"Editar — {ws['name']}")
        self.setMinimumSize(420, 500)

        t = current_theme()
        self.setStyleSheet(
            f"QDialog {{ background: {t.bg_card}; color: {t.text_primary}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Editar workspace")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {t.text_primary};")
        layout.addWidget(title)

        # Name
        name_label = QLabel("Nome")
        name_label.setStyleSheet(f"font-size: 12px; color: {t.text_muted}; font-weight: 600;")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setText(ws["name"])
        layout.addWidget(self.name_input)

        # Description
        desc_label = QLabel("Descricao")
        desc_label.setStyleSheet(f"font-size: 12px; color: {t.text_muted}; font-weight: 600;")
        layout.addWidget(desc_label)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Descreva o proposito deste workspace...")
        self.desc_input.setMaximumHeight(80)
        self.desc_input.setPlainText(ws.get("description", ""))
        layout.addWidget(self.desc_input)

        # Icon & Color
        self.icon_color = _IconColorSection(
            initial_icon=ws.get("icon", "W"),
            initial_color=ws.get("color", ""),
        )
        layout.addWidget(self.icon_color)

        # ID (read-only info)
        id_row = QHBoxLayout()
        id_lbl = QLabel("ID:")
        id_lbl.setStyleSheet(f"font-size: 11px; color: {t.text_muted};")
        id_row.addWidget(id_lbl)
        id_val = QLabel(ws["id"])
        id_val.setStyleSheet(f"font-size: 11px; color: {t.text_muted}; font-family: monospace;")
        id_row.addWidget(id_val)
        id_row.addStretch()
        layout.addLayout(id_row)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setProperty("flat", True)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Salvar")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self.saved = False

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            return
        update_workspace(
            self._ws_id,
            name=name,
            icon=self.icon_color.get_icon(),
            description=self.desc_input.toPlainText().strip(),
            color=self.icon_color.get_color(),
        )
        self.saved = True
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
        self.setMinimumSize(500, 400)

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        scroll_content = QWidget()
        self.items_layout = QVBoxLayout(scroll_content)
        self.items_layout.setSpacing(8)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

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
            ws_color = ws.get("color") or t.accent

            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
                f"border-left: 4px solid {ws_color}; border-radius: 8px; }}"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            card_layout.setSpacing(6)

            # Top row: icon + name + badges
            top_row = QHBoxLayout()
            top_row.setSpacing(10)

            icon_lbl = QLabel(ws.get("icon", "W"))
            icon_lbl.setFixedSize(32, 32)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet(
                f"background: {ws_color}; color: {t.text_on_accent}; "
                f"font-size: 14px; font-weight: 700; border-radius: 8px; border: none;"
            )
            top_row.addWidget(icon_lbl)

            name_col = QVBoxLayout()
            name_col.setSpacing(0)
            name_lbl = QLabel(ws["name"])
            name_lbl.setStyleSheet(
                f"font-weight: 600; font-size: 14px; border: none;"
            )
            name_col.addWidget(name_lbl)

            desc = ws.get("description", "")
            if desc:
                desc_lbl = QLabel(desc if len(desc) <= 60 else desc[:57] + "...")
                desc_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
                name_col.addWidget(desc_lbl)

            top_row.addLayout(name_col, 1)

            if ws["id"] == active_id:
                active_badge = QLabel("ativo")
                active_badge.setStyleSheet(
                    f"background: {t.success}; color: white; padding: 2px 8px; "
                    f"border-radius: 6px; font-size: 10px; font-weight: 600; border: none;"
                )
                top_row.addWidget(active_badge)

            card_layout.addLayout(top_row)

            # Bottom row: id + action buttons
            bottom_row = QHBoxLayout()
            bottom_row.setSpacing(8)

            id_lbl = QLabel(ws["id"])
            id_lbl.setStyleSheet(
                f"font-family: monospace; font-size: 10px; color: {t.text_muted}; border: none;"
            )
            bottom_row.addWidget(id_lbl)
            bottom_row.addStretch()

            edit_btn = QPushButton("Editar")
            edit_btn.setFixedHeight(26)
            edit_btn.setStyleSheet(
                f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
                f"border: 1px solid {t.border}; border-radius: 6px; padding: 3px 12px; "
                f"font-size: 11px; }}"
                f"QPushButton:hover {{ background: {t.bg_hover}; }}"
            )
            ws_id = ws["id"]
            ws_copy = dict(ws)
            edit_btn.clicked.connect(lambda _, w=ws_copy: self._edit(w))
            bottom_row.addWidget(edit_btn)

            if len(workspaces) > 1:
                del_btn = QPushButton("Excluir")
                del_btn.setFixedHeight(26)
                del_btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {t.danger}; "
                    f"border: 1px solid {t.danger}; border-radius: 6px; padding: 3px 10px; "
                    f"font-size: 11px; }}"
                    f"QPushButton:hover {{ background: {t.danger}; color: white; }}"
                )
                ws_name = ws["name"]
                del_btn.clicked.connect(lambda _, wid=ws_id, wname=ws_name: self._delete(wid, wname))
                bottom_row.addWidget(del_btn)

            card_layout.addLayout(bottom_row)
            self.items_layout.addWidget(card)

        self.items_layout.addStretch()

    def _edit(self, ws: dict):
        dlg = EditWorkspaceDialog(ws, self)
        if dlg.exec() == QDialog.Accepted and dlg.saved:
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
        self.setFixedHeight(38)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(6)

        self._icon = QLabel()
        self._icon.setFixedSize(24, 24)
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

        ws_color = active.get("color") or t.accent

        self._icon.setText(active.get("icon", "W"))
        self._icon.setStyleSheet(
            f"background: {ws_color}; color: {t.text_on_accent}; "
            f"font-size: 11px; font-weight: 700; border-radius: 6px;"
        )
        self._name.setText(active["name"])
        self._name.setStyleSheet(
            f"font-weight: 600; font-size: 12px; color: {t.text_primary};"
        )
        self._chevron.setStyleSheet(
            f"color: {t.text_muted}; font-size: 9px;"
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
