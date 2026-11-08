import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import (
    DEFAULT_COLUMNS,
    BoardColumn,
    Project,
    Task,
    get_session,
)
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t


class ProjectCard(QFrame):
    open_clicked = Signal(int)
    delete_clicked = Signal(int)
    azure_clicked = Signal(int)
    edit_azure_clicked = Signal(int)

    def __init__(self, project_id, key, name, description, done, total, theme, azure_url=""):
        super().__init__()
        t = theme
        pct = int(done / total * 100) if total else 0
        self._azure_url = azure_url or ""

        self.setStyleSheet(
            f"ProjectCard {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-radius: 10px; }}"
            f"ProjectCard:hover {{ border-color: {t.accent}; }}"
        )
        self.setMinimumHeight(90)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Left accent bar
        accent_bar = QFrame()
        accent_bar.setFixedWidth(4)
        accent_bar.setStyleSheet(
            f"background: {t.accent}; border-radius: 4px 0 0 4px;"
        )
        outer.addWidget(accent_bar)

        # Content area
        content = QVBoxLayout()
        content.setContentsMargins(10, 8, 10, 8)
        content.setSpacing(6)

        # Top row: key badge + name
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        key_lbl = QLabel(key)
        key_lbl.setStyleSheet(
            f"background: {t.bg_badge}; color: {t.text_secondary}; "
            f"padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 12px; border: none;"
        )
        top_row.addWidget(key_lbl)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-weight: 700; font-size: 16px; color: {t.text_primary}; border: none;")
        top_row.addWidget(name_lbl, 1)
        content.addLayout(top_row)

        # Description (optional, max 2 lines)
        if description:
            desc_lbl = QLabel(description)
            desc_lbl.setWordWrap(True)
            desc_lbl.setMaximumHeight(36)
            desc_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; border: none;")
            content.addWidget(desc_lbl)

        # Stats row: progress text + bar
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)

        stats_lbl = QLabel(_t("{done}/{total} tarefas concluídas").format(done=done, total=total))
        stats_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        stats_row.addWidget(stats_lbl)

        bar = QProgressBar()
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        bar.setMaximumWidth(120)
        stats_row.addWidget(bar)

        stats_row.addStretch()

        # Azure link row (atalho)
        azure_row = QHBoxLayout()
        azure_row.setSpacing(6)
        if self._azure_url:
            az_btn = QPushButton("🔗 Azure Board ↗")
            az_btn.setFixedHeight(26)
            az_btn.setCursor(Qt.PointingHandCursor)
            az_btn.setStyleSheet(f"QPushButton {{ background: #0078d4; color: #fff; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 600; border: none; }}")
            az_btn.setToolTip(self._azure_url)
            az_btn.clicked.connect(lambda: self.azure_clicked.emit(project_id))
            azure_row.addWidget(az_btn)
            edit_az = QPushButton(_t("Editar link"))
            edit_az.setFixedHeight(26)
            edit_az.setProperty("flat", True)
            edit_az.setCursor(Qt.PointingHandCursor)
            edit_az.clicked.connect(lambda: self.edit_azure_clicked.emit(project_id))
            azure_row.addWidget(edit_az)
        else:
            no_lbl = QLabel(_t("Sem link Azure"))
            no_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
            azure_row.addWidget(no_lbl)
            set_az = QPushButton(_t("Definir link"))
            set_az.setFixedHeight(26)
            set_az.setProperty("flat", True)
            set_az.setCursor(Qt.PointingHandCursor)
            set_az.clicked.connect(lambda: self.edit_azure_clicked.emit(project_id))
            azure_row.addWidget(set_az)
        azure_row.addStretch()
        content.addLayout(azure_row)

        # Action buttons
        open_btn = QPushButton(_t("Abrir Board"))
        open_btn.setFixedHeight(32)
        open_btn.setStyleSheet(
            f"QPushButton {{ background: {t.accent}; color: {t.text_on_accent}; "
            f"border-radius: 6px; padding: 6px 16px; font-size: 12px; font-weight: 600; border: none; }}"
            f"QPushButton:hover {{ background: {t.accent_hover}; }}"
        )
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(lambda: self.open_clicked.emit(project_id))
        stats_row.addWidget(open_btn)

        del_btn = QPushButton(_t("Excluir"))
        del_btn.setFixedHeight(28)
        del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {t.danger}; "
            f"border: none; padding: 4px 10px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; }}"
        )
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(project_id))
        stats_row.addWidget(del_btn)

        content.addLayout(stats_row)

        outer.addLayout(content, 1)


class ProjectsView(QWidget):
    project_selected = Signal(int)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(10)

        title = QLabel(_t("Projetos"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # --- Creation form ---
        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form_outer = QVBoxLayout(form_frame)
        form_outer.setContentsMargins(10, 8, 10, 8)
        form_outer.setSpacing(10)

        form_title = QLabel(_t("Novo Projeto"))
        form_title.setProperty("class", "cardTitle")
        form_outer.addWidget(form_title)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(_t("Nome do projeto"))
        self.name_input.textChanged.connect(self._auto_key)
        form_layout.addRow(_t("Nome:"), self.name_input)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText(_t("Descrição breve (opcional)"))
        form_layout.addRow(_t("Descrição:"), self.desc_input)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("KEY")
        self.key_input.setMaximumWidth(120)
        form_layout.addRow(_t("Chave:"), self.key_input)

        self.azure_input = QLineEdit()
        self.azure_input.setPlaceholderText("https://dev.azure.com/.../_boards")
        form_layout.addRow(_t("Link Azure:"), self.azure_input)

        form_outer.addLayout(form_layout)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        add_btn = QPushButton(_t("+ Criar Projeto"))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._create)
        btn_row.addWidget(add_btn)
        form_outer.addLayout(btn_row)

        layout.addWidget(form_frame)

        # --- Project cards scroll area ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.scroll.setWidget(self.cards_container)

        layout.addWidget(self.scroll, 1)

        self.refresh()

    def _auto_key(self, text):
        """Auto-generate key from project name (first 3-4 uppercase chars)."""
        if not self.key_input.hasFocus():
            clean = re.sub(r"[^a-zA-Z0-9]", "", text).upper()
            self.key_input.setText(clean[:4] if len(clean) >= 4 else clean[:3])

    def refresh(self):
        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t = current_theme()
        s = get_session()
        try:
            projects = s.query(Project).order_by(Project.created_at).all()

            if not projects:
                # Empty state
                empty_w = QWidget()
                empty_l = QVBoxLayout(empty_w)
                empty_l.setAlignment(Qt.AlignCenter)
                empty_l.setSpacing(8)

                empty_title = QLabel(_t("Nenhum projeto criado"))
                empty_title.setAlignment(Qt.AlignCenter)
                empty_title.setStyleSheet(
                    f"color: {t.text_muted}; font-size: 16px; font-weight: 600;"
                )
                empty_l.addWidget(empty_title)

                empty_sub = QLabel(_t("Crie seu primeiro projeto para começar"))
                empty_sub.setAlignment(Qt.AlignCenter)
                empty_sub.setStyleSheet(f"color: {t.text_muted}; font-size: 13px;")
                empty_l.addWidget(empty_sub)

                self.cards_layout.addWidget(empty_w, 1)
                return

            for p in projects:
                total = s.query(Task).filter(
                    Task.project_id == p.id, Task.deleted_at == None  # noqa: E711
                ).count()
                done = (
                    s.query(Task)
                    .join(BoardColumn)
                    .filter(
                        Task.project_id == p.id,
                        Task.deleted_at == None,  # noqa: E711
                        BoardColumn.is_done == True,  # noqa: E712
                    )
                    .count()
                )

                card = ProjectCard(
                    project_id=p.id,
                    key=p.key,
                    name=p.name,
                    description=p.description or "",
                    done=done,
                    total=total,
                    theme=t,
                    azure_url=getattr(p, "azure_board_url", "") or "",
                )
                card.open_clicked.connect(self.project_selected.emit)
                card.delete_clicked.connect(self._delete)
                card.azure_clicked.connect(self._open_azure)
                card.edit_azure_clicked.connect(self._edit_azure)
                self.cards_layout.addWidget(card)

            self.cards_layout.addStretch()
        finally:
            s.close()

    def _create(self):
        name = self.name_input.text().strip()
        key = self.key_input.text().strip().upper()
        if not name or not key:
            return
        desc = self.desc_input.text().strip() or None
        azure = self.azure_input.text().strip() or ""
        s = get_session()
        try:
            p = Project(name=name, key=key, description=desc, azure_board_url=azure)
            s.add(p)
            s.flush()
            for col_def in DEFAULT_COLUMNS:
                col = BoardColumn(
                    project_id=p.id,
                    name=col_def["name"],
                    order=col_def["order"],
                    is_done=col_def.get("is_done", False),
                )
                s.add(col)
            s.commit()
            self.name_input.clear()
            self.key_input.clear()
            self.desc_input.clear()
            self.azure_input.clear()
            self.refresh()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _open_azure(self, project_id):
        s = get_session()
        try:
            p = s.get(Project, project_id)
            url = (getattr(p, "azure_board_url", "") or "").strip() if p else ""
            if url:
                from PySide6.QtGui import QDesktopServices
                from PySide6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl(url))
        finally:
            s.close()

    def _edit_azure(self, project_id):
        s = get_session()
        try:
            p = s.get(Project, project_id)
            cur = (getattr(p, "azure_board_url", "") or "") if p else ""
        finally:
            s.close()
        from PySide6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(self, _t("Link Azure"), _t("Link do board do Azure (cole a URL):"), text=cur)
        if not ok:
            return
        s = get_session()
        try:
            p = s.get(Project, project_id)
            if p is not None:
                p.azure_board_url = url.strip()
                s.commit()
            self.refresh()
        finally:
            s.close()

    def _delete(self, project_id):
        reply = QMessageBox.question(
            self,
            _t("Confirmar exclusão"),
            _t("Tem certeza? Todas as tarefas do projeto serão excluídas."),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        s = get_session()
        try:
            p = s.query(Project).get(project_id)
            if p:
                s.delete(p)
                s.commit()
            self.refresh()
        finally:
            s.close()
