import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import load_config, save_config
from maestro_local.db.models import (
    ActivityLog,
    BoardColumn,
    Comment,
    DailyNote,
    DATA_DIR,
    DB_PATH,
    Project,
    Task,
    get_session,
)
from maestro_local.gui.theme import current_theme


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() or c in " -_." else "_" for c in name).strip()


class DailyView(QWidget):
    def __init__(self):
        super().__init__()
        self._today = date.today().isoformat()

        main = QVBoxLayout(self)
        main.setContentsMargins(24, 24, 24, 24)
        main.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Diario de Trabalho")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        # Date selector
        self.date_combo = QComboBox()
        self.date_combo.setFixedWidth(140)
        self.date_combo.currentTextChanged.connect(self._on_date_changed)
        header.addWidget(self.date_combo)

        main.addLayout(header)

        # Scroll content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)

        t = current_theme()

        # --- Notes section ---
        notes_frame = QFrame()
        notes_frame.setStyleSheet(
            f"QFrame#notesFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-radius: 10px; padding: 16px; }}"
        )
        notes_frame.setObjectName("notesFrame")
        notes_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        notes_layout = QVBoxLayout(notes_frame)
        notes_layout.setSpacing(8)
        notes_layout.setContentsMargins(16, 12, 16, 12)

        notes_header = QHBoxLayout()
        notes_title = QLabel("Notas do dia")
        notes_title.setStyleSheet(
            f"font-weight: 700; font-size: 14px; color: {t.text_primary}; border: none;"
        )
        notes_header.addWidget(notes_title)
        notes_header.addStretch()

        self._editor_mode = "edit"

        self.toggle_btn = QPushButton("Visualizar")
        self.toggle_btn.setFixedHeight(30)
        self.toggle_btn.setStyleSheet(
            f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: 6px; padding: 4px 14px; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; }}"
        )
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_preview)
        notes_header.addWidget(self.toggle_btn)

        tmpl_btn = QPushButton("Usar template")
        tmpl_btn.setFixedHeight(30)
        tmpl_btn.setStyleSheet(
            f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: 6px; padding: 4px 14px; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; }}"
        )
        tmpl_btn.setCursor(Qt.PointingHandCursor)
        tmpl_btn.clicked.connect(self._insert_template)
        notes_header.addWidget(tmpl_btn)

        save_btn = QPushButton("Salvar")
        save_btn.setFixedHeight(30)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_notes)
        notes_header.addWidget(save_btn)
        notes_layout.addLayout(notes_header)

        # Stacked widget: editor (0) / preview (1)
        self.editor_stack = QStackedWidget()
        self.editor_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.editor_stack.setMinimumHeight(200)

        # --- Edit mode ---
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "## Foco do Dia\n"
            "- Objetivo principal:\n"
            "- Prioridade maxima:\n\n"
            "---\n\n"
            "## Tarefas Planejadas\n"
            "- [ ] ...\n\n"
            "---\n\n"
            "## Bloqueios / Problemas / Duvidas\n"
            "- Descricao do problema\n"
            "- Dependencia / quem pode ajudar\n\n"
            "---\n\n"
            "## Anotacoes Rapidas\n"
            "- Ideias\n"
            "- Decisoes tomadas\n"
            "- Links uteis\n\n"
            "---\n\n"
            "## Check-out do Dia\n"
            "- O que foi concluido:\n"
            "- O que ficou pendente:\n"
            "- Proximo passo amanha:"
        )
        self.notes_edit.setAcceptRichText(False)
        self.notes_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.notes_edit.setStyleSheet(
            f"QTextEdit {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 8px; padding: 12px; font-family: monospace; font-size: 13px; "
            f"color: {t.text_primary}; }}"
        )
        self.editor_stack.addWidget(self.notes_edit)

        # --- Preview mode ---
        self.notes_preview = QTextBrowser()
        self.notes_preview.setOpenExternalLinks(True)
        self.notes_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.notes_preview.setStyleSheet(
            f"QTextBrowser {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 8px; padding: 12px; font-size: 13px; "
            f"color: {t.text_primary}; }}"
        )
        self.editor_stack.addWidget(self.notes_preview)

        notes_layout.addWidget(self.editor_stack, 1)
        self.content_layout.addWidget(notes_frame)

        # --- Generate report ---
        actions_row = QHBoxLayout()

        gen_btn = QPushButton("Gerar Relatorio do Dia")
        gen_btn.setFixedHeight(36)
        gen_btn.setCursor(Qt.PointingHandCursor)
        gen_btn.clicked.connect(self._generate_report)
        actions_row.addWidget(gen_btn)

        actions_row.addStretch()

        # Backup button
        backup_btn = QPushButton("Backup do Banco")
        backup_btn.setFixedHeight(36)
        backup_btn.setStyleSheet(
            f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: 8px; padding: 8px 18px; "
            f"font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; }}"
        )
        backup_btn.setCursor(Qt.PointingHandCursor)
        backup_btn.clicked.connect(self._backup_db)
        actions_row.addWidget(backup_btn)

        self.content_layout.addLayout(actions_row)

        # --- Activity summary (tasks worked on) ---
        self.activity_frame = QFrame()
        self.activity_frame.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-radius: 10px; padding: 16px; }}"
        )
        self.activity_layout = QVBoxLayout(self.activity_frame)
        self.activity_layout.setSpacing(6)
        self.content_layout.addWidget(self.activity_frame)

        # --- Report output ---
        self.report_frame = QFrame()
        self.report_frame.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-radius: 10px; padding: 16px; }}"
        )
        self.report_frame.setVisible(False)
        report_inner = QVBoxLayout(self.report_frame)
        report_inner.setSpacing(8)

        report_header = QHBoxLayout()
        report_title = QLabel("Relatorio Gerado")
        report_title.setStyleSheet(
            f"font-weight: 700; font-size: 14px; color: {t.text_primary}; border: none;"
        )
        report_header.addWidget(report_title)
        report_header.addStretch()

        copy_btn = QPushButton("Copiar")
        copy_btn.setFixedHeight(28)
        copy_btn.setStyleSheet(
            f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: 6px; padding: 4px 14px; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; }}"
        )
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_report)
        report_header.addWidget(copy_btn)

        export_btn = QPushButton("Exportar .md")
        export_btn.setFixedHeight(28)
        export_btn.setStyleSheet(
            f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: 6px; padding: 4px 14px; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; }}"
        )
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_report)
        report_header.addWidget(export_btn)

        report_inner.addLayout(report_header)

        self.report_output = QTextEdit()
        self.report_output.setReadOnly(True)
        self.report_output.setMinimumHeight(250)
        self.report_output.setStyleSheet(
            f"QTextEdit {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 8px; padding: 10px; font-family: monospace; font-size: 13px; "
            f"color: {t.text_primary}; }}"
        )
        report_inner.addWidget(self.report_output)
        self.content_layout.addWidget(self.report_frame)

        # --- Obsidian sync section ---
        obsidian_frame = QFrame()
        obsidian_frame.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-radius: 10px; padding: 16px; }}"
        )
        obs_layout = QVBoxLayout(obsidian_frame)
        obs_layout.setSpacing(8)

        obs_title = QLabel("Obsidian Vault")
        obs_title.setStyleSheet(
            f"font-weight: 700; font-size: 14px; color: {t.text_primary}; border: none;"
        )
        obs_layout.addWidget(obs_title)

        obs_hint = QLabel(
            "Configure um vault do Obsidian por projeto para exportar dados como Markdown estruturado."
        )
        obs_hint.setWordWrap(True)
        obs_hint.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; border: none;")
        obs_layout.addWidget(obs_hint)

        obs_row = QHBoxLayout()
        obs_proj_label = QLabel("Projeto:")
        obs_proj_label.setStyleSheet(f"font-weight: 600; font-size: 12px; border: none;")
        obs_row.addWidget(obs_proj_label)

        self.obs_project_combo = QComboBox()
        self.obs_project_combo.setFixedWidth(200)
        self.obs_project_combo.currentIndexChanged.connect(self._on_obs_project_changed)
        obs_row.addWidget(self.obs_project_combo)

        self.obs_path_input = QLabel("Nenhum vault configurado")
        self.obs_path_input.setStyleSheet(
            f"color: {t.text_muted}; font-size: 12px; border: none;"
        )
        obs_row.addWidget(self.obs_path_input, 1)

        obs_browse = QPushButton("Selecionar Vault")
        obs_browse.setFixedHeight(30)
        obs_browse.setStyleSheet(
            f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: 6px; padding: 6px 14px; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; }}"
        )
        obs_browse.setCursor(Qt.PointingHandCursor)
        obs_browse.clicked.connect(self._browse_vault)
        obs_row.addWidget(obs_browse)

        obs_sync = QPushButton("Sincronizar")
        obs_sync.setFixedHeight(30)
        obs_sync.setCursor(Qt.PointingHandCursor)
        obs_sync.clicked.connect(self._sync_obsidian)
        obs_row.addWidget(obs_sync)

        obs_layout.addLayout(obs_row)

        obs_struct = QLabel(
            "Estrutura: Vault / Projeto / {Board, Tasks, Reports, Docs}"
        )
        obs_struct.setStyleSheet(
            f"color: {t.text_muted}; font-size: 11px; font-style: italic; border: none;"
        )
        obs_layout.addWidget(obs_struct)

        self.content_layout.addWidget(obsidian_frame)

        self.obs_status_label = QLabel("")
        self.obs_status_label.setStyleSheet(
            f"color: {t.text_muted}; font-size: 11px; border: none; padding: 0 4px;"
        )
        self.content_layout.addWidget(self.obs_status_label)

        self.content_layout.addStretch()

        scroll.setWidget(content)
        main.addWidget(scroll, 1)

        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._auto_sync_obsidian)
        self._sync_timer.start(5 * 60 * 1000)

    def refresh(self):
        self._populate_dates()
        self._load_day(self._today)
        self._refresh_activity()
        self._refresh_obs_projects()

    def _populate_dates(self):
        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        today = date.today()
        for i in range(30):
            d = today - timedelta(days=i)
            self.date_combo.addItem(d.isoformat())
        s = get_session()
        try:
            notes = s.query(DailyNote.date).order_by(DailyNote.date.desc()).all()
            existing = {n.date for n in notes}
            combo_dates = {self.date_combo.itemText(i) for i in range(self.date_combo.count())}
            for d in sorted(existing - combo_dates, reverse=True):
                self.date_combo.addItem(d)
        finally:
            s.close()
        idx = self.date_combo.findText(self._today)
        if idx >= 0:
            self.date_combo.setCurrentIndex(idx)
        self.date_combo.blockSignals(False)

    def _on_date_changed(self, text):
        if text:
            self._today = text
            self._load_day(text)
            self._refresh_activity()

    def _load_day(self, day_str):
        s = get_session()
        try:
            note = s.query(DailyNote).filter(DailyNote.date == day_str).first()
            self.notes_edit.setPlainText(note.body if note else "")
            if self._editor_mode == "preview":
                self._update_preview()
            if note and note.report:
                self.report_output.setPlainText(note.report)
                self.report_frame.setVisible(True)
            else:
                self.report_output.clear()
                self.report_frame.setVisible(False)
        finally:
            s.close()

    def _toggle_preview(self):
        t = current_theme()
        if self._editor_mode == "edit":
            self._editor_mode = "preview"
            self._update_preview()
            self.editor_stack.setCurrentIndex(1)
            self.toggle_btn.setText("Editar")
            self.toggle_btn.setStyleSheet(
                f"QPushButton {{ background: {t.accent}; color: {t.text_on_accent}; "
                f"border: none; border-radius: 6px; padding: 4px 14px; "
                f"font-size: 12px; font-weight: 600; }}"
                f"QPushButton:hover {{ background: {t.accent_hover}; }}"
            )
        else:
            self._editor_mode = "edit"
            self.editor_stack.setCurrentIndex(0)
            self.toggle_btn.setText("Visualizar")
            self.toggle_btn.setStyleSheet(
                f"QPushButton {{ background: {t.bg_badge}; color: {t.text_secondary}; "
                f"border: 1px solid {t.border}; border-radius: 6px; padding: 4px 14px; "
                f"font-size: 12px; font-weight: 600; }}"
                f"QPushButton:hover {{ background: {t.bg_hover}; }}"
            )

    def _update_preview(self):
        md = self.notes_edit.toPlainText()
        t = current_theme()
        html = self._md_to_html(md, t)
        self.notes_preview.setHtml(html)

    @staticmethod
    def _md_to_html(md: str, t) -> str:
        import re

        lines = md.split("\n")
        html_lines = []
        in_ul = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("### "):
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False
                html_lines.append(
                    f'<h3 style="color:{t.text_primary};margin:14px 0 6px 0;font-size:14px;">'
                    f"{stripped[4:]}</h3>"
                )
            elif stripped.startswith("## "):
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False
                html_lines.append(
                    f'<h2 style="color:{t.text_primary};margin:18px 0 8px 0;font-size:16px;'
                    f'border-bottom:1px solid {t.border_light};padding-bottom:6px;">'
                    f"{stripped[3:]}</h2>"
                )
            elif stripped.startswith("# "):
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False
                html_lines.append(
                    f'<h1 style="color:{t.text_primary};margin:20px 0 10px 0;font-size:20px;">'
                    f"{stripped[2:]}</h1>"
                )
            elif stripped == "---":
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False
                html_lines.append(
                    f'<hr style="border:none;border-top:1px solid {t.border_light};margin:12px 0;">'
                )
            elif stripped.startswith("- [x] "):
                if not in_ul:
                    html_lines.append('<ul style="margin:4px 0;padding-left:20px;">')
                    in_ul = True
                text = stripped[6:]
                text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
                text = re.sub(r"`(.+?)`", rf'<code style="background:{t.bg_badge};padding:1px 4px;border-radius:3px;">\1</code>', text)
                html_lines.append(
                    f'<li style="color:{t.text_muted};text-decoration:line-through;margin:3px 0;">'
                    f"&#9745; {text}</li>"
                )
            elif stripped.startswith("- [ ] "):
                if not in_ul:
                    html_lines.append('<ul style="margin:4px 0;padding-left:20px;">')
                    in_ul = True
                text = stripped[6:]
                text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
                text = re.sub(r"`(.+?)`", rf'<code style="background:{t.bg_badge};padding:1px 4px;border-radius:3px;">\1</code>', text)
                html_lines.append(
                    f'<li style="color:{t.text_primary};margin:3px 0;">'
                    f"&#9744; {text}</li>"
                )
            elif stripped.startswith("- "):
                if not in_ul:
                    html_lines.append('<ul style="margin:4px 0;padding-left:20px;">')
                    in_ul = True
                text = stripped[2:]
                text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
                text = re.sub(r"`(.+?)`", rf'<code style="background:{t.bg_badge};padding:1px 4px;border-radius:3px;">\1</code>', text)
                html_lines.append(
                    f'<li style="color:{t.text_primary};margin:3px 0;">{text}</li>'
                )
            elif stripped == "":
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False
                html_lines.append("<br>")
            else:
                if in_ul:
                    html_lines.append("</ul>")
                    in_ul = False
                text = stripped
                text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
                text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
                text = re.sub(r"`(.+?)`", rf'<code style="background:{t.bg_badge};padding:1px 4px;border-radius:3px;">\1</code>', text)
                html_lines.append(
                    f'<p style="color:{t.text_primary};margin:4px 0;">{text}</p>'
                )

        if in_ul:
            html_lines.append("</ul>")

        body = "\n".join(html_lines)
        return (
            f'<div style="font-family: Inter, Segoe UI, Noto Sans, sans-serif; '
            f'font-size: 13px; line-height: 1.6; padding: 4px;">{body}</div>'
        )

    def _insert_template(self):
        if self.notes_edit.toPlainText().strip():
            from PySide6.QtWidgets import QMessageBox
            r = QMessageBox.question(
                self, "Substituir conteudo?",
                "Ja existe conteudo nas notas. Deseja substituir pelo template?",
            )
            if r != QMessageBox.Yes:
                return
        self.notes_edit.setPlainText(
            "## Foco do Dia\n"
            "- Objetivo principal:\n"
            "- Prioridade maxima:\n\n"
            "---\n\n"
            "## Tarefas Planejadas\n"
            "- [ ] ...\n\n"
            "---\n\n"
            "## Bloqueios / Problemas / Duvidas\n"
            "- Descricao do problema\n"
            "- Dependencia / quem pode ajudar\n\n"
            "---\n\n"
            "## Anotacoes Rapidas\n"
            "- Ideias\n"
            "- Decisoes tomadas\n"
            "- Links uteis\n\n"
            "---\n\n"
            "## Check-out do Dia\n"
            "- O que foi concluido:\n"
            "- O que ficou pendente:\n"
            "- Proximo passo amanha:\n"
        )

    def _save_notes(self):
        body = self.notes_edit.toPlainText()
        s = get_session()
        try:
            note = s.query(DailyNote).filter(DailyNote.date == self._today).first()
            if note:
                note.body = body
                note.updated_at = datetime.utcnow()
            else:
                note = DailyNote(date=self._today, body=body)
                s.add(note)
            s.commit()
        finally:
            s.close()

    def _refresh_activity(self):
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t = current_theme()

        act_title = QLabel("Atividade do dia")
        act_title.setStyleSheet(
            f"font-weight: 700; font-size: 14px; color: {t.text_primary}; border: none;"
        )
        self.activity_layout.addWidget(act_title)

        s = get_session()
        try:
            day_start = datetime.fromisoformat(f"{self._today}T00:00:00")
            day_end = datetime.fromisoformat(f"{self._today}T23:59:59")

            activities = (
                s.query(ActivityLog)
                .filter(ActivityLog.created_at >= day_start, ActivityLog.created_at <= day_end)
                .order_by(ActivityLog.created_at.desc())
                .all()
            )

            task_ids = set()
            for a in activities:
                if a.entity_type == "task":
                    task_ids.add(a.entity_id)

            comments = (
                s.query(Comment)
                .filter(Comment.created_at >= day_start, Comment.created_at <= day_end)
                .all()
            )
            for c in comments:
                task_ids.add(c.task_id)

            if not task_ids:
                empty = QLabel("Nenhuma atividade registrada neste dia")
                empty.setStyleSheet(f"color: {t.text_muted}; font-size: 13px; border: none; padding: 8px 0;")
                self.activity_layout.addWidget(empty)
                return

            tasks = s.query(Task).filter(Task.id.in_(task_ids)).all()
            for task in tasks:
                row = QHBoxLayout()
                row.setSpacing(8)

                code_lbl = QLabel(task.code)
                code_lbl.setFixedWidth(80)
                code_lbl.setStyleSheet(
                    f"font-family: monospace; font-size: 12px; color: {t.accent}; "
                    f"font-weight: 600; border: none;"
                )
                row.addWidget(code_lbl)

                status_lbl = QLabel(task.status)
                status_lbl.setFixedWidth(80)
                status_lbl.setStyleSheet(
                    f"color: {t.text_muted}; font-size: 11px; border: none;"
                )
                row.addWidget(status_lbl)

                title_lbl = QLabel(task.title)
                title_lbl.setStyleSheet(
                    f"color: {t.text_primary}; font-size: 13px; border: none;"
                )
                row.addWidget(title_lbl, 1)

                container = QWidget()
                container.setLayout(row)
                self.activity_layout.addWidget(container)
        finally:
            s.close()

    def _generate_report(self):
        self._save_notes()

        s = get_session()
        try:
            day_start = datetime.fromisoformat(f"{self._today}T00:00:00")
            day_end = datetime.fromisoformat(f"{self._today}T23:59:59")

            activities = (
                s.query(ActivityLog)
                .filter(ActivityLog.created_at >= day_start, ActivityLog.created_at <= day_end)
                .order_by(ActivityLog.created_at)
                .all()
            )

            task_ids = set()
            for a in activities:
                if a.entity_type == "task":
                    task_ids.add(a.entity_id)

            comments = (
                s.query(Comment)
                .filter(Comment.created_at >= day_start, Comment.created_at <= day_end)
                .all()
            )
            for c in comments:
                task_ids.add(c.task_id)

            tasks = s.query(Task).filter(Task.id.in_(task_ids)).all() if task_ids else []

            note = s.query(DailyNote).filter(DailyNote.date == self._today).first()
            user_notes = note.body if note else ""

            lines = [f"# Relatorio Diario — {self._today}", ""]

            # Tasks worked on
            if tasks:
                lines.append("## Tarefas trabalhadas")
                lines.append("")
                for task in tasks:
                    status = task.status
                    ttype = task.type or "FEATURE"
                    lines.append(f"- **{task.code}** — {task.title} [{ttype}] (_{status}_)")
                lines.append("")

            # Activity timeline
            if activities:
                lines.append("## Atividades")
                lines.append("")
                for a in activities:
                    time_str = a.created_at.strftime("%H:%M") if a.created_at else ""
                    lines.append(f"- `{time_str}` {a.action}: {a.detail or ''}")
                lines.append("")

            # Comments/reviews of the day
            reviews = [c for c in comments if c.type == "CODE_REVIEW"]
            if reviews:
                lines.append("## Code Reviews")
                lines.append("")
                for r in reviews:
                    task = s.query(Task).get(r.task_id)
                    code = task.code if task else f"#{r.task_id}"
                    lines.append(f"### {code}")
                    lines.append(r.body or "")
                    lines.append("")

            # User notes
            if user_notes.strip():
                lines.append("## Notas")
                lines.append("")
                lines.append(user_notes.strip())
                lines.append("")

            # Summary
            lines.append("## Resumo")
            lines.append("")
            lines.append(f"- **Tarefas tocadas**: {len(tasks)}")
            lines.append(f"- **Atividades registradas**: {len(activities)}")
            lines.append(f"- **Code reviews**: {len(reviews)}")
            done_today = sum(
                1 for task in tasks
                if s.query(BoardColumn).get(task.column_id)
                and s.query(BoardColumn).get(task.column_id).is_done
            )
            lines.append(f"- **Concluidas hoje**: {done_today}")

            report = "\n".join(lines)

            # Save report
            if note:
                note.report = report
                note.updated_at = datetime.utcnow()
            else:
                note = DailyNote(date=self._today, body=user_notes, report=report)
                s.add(note)
            s.commit()

            self.report_output.setPlainText(report)
            self.report_frame.setVisible(True)
        finally:
            s.close()

    def _copy_report(self):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.report_output.toPlainText())

    def _export_report(self):
        text = self.report_output.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar relatorio", f"relatorio-{self._today}.md", "Markdown (*.md)"
        )
        if path:
            Path(path).write_text(text, encoding="utf-8")

    # --- Backup ---

    def _backup_db(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Salvar backup",
            f"maestro-backup-{date.today().isoformat()}.db",
            "SQLite Database (*.db)",
        )
        if not dest:
            return
        try:
            shutil.copy2(DB_PATH, dest)
            QMessageBox.information(
                self, "Backup concluido",
                f"Banco de dados copiado para:\n{dest}",
            )
        except Exception as e:
            QMessageBox.warning(self, "Erro no backup", str(e))

    # --- Obsidian ---

    def _refresh_obs_projects(self):
        self.obs_project_combo.blockSignals(True)
        self.obs_project_combo.clear()
        s = get_session()
        try:
            projects = s.query(Project).order_by(Project.name).all()
            for p in projects:
                self.obs_project_combo.addItem(f"{p.key} — {p.name}", p.id)
        finally:
            s.close()
        self.obs_project_combo.blockSignals(False)
        if self.obs_project_combo.count() > 0:
            self._on_obs_project_changed(0)

    def _on_obs_project_changed(self, idx):
        pid = self.obs_project_combo.currentData()
        if pid is None:
            return
        cfg = load_config()
        vaults = cfg.get("obsidian_vaults", {})
        vault_path = vaults.get(str(pid))
        t = current_theme()
        if vault_path:
            self.obs_path_input.setText(vault_path)
            self.obs_path_input.setStyleSheet(
                f"color: {t.text_primary}; font-size: 12px; border: none;"
            )
        else:
            self.obs_path_input.setText("Nenhum vault configurado")
            self.obs_path_input.setStyleSheet(
                f"color: {t.text_muted}; font-size: 12px; border: none;"
            )

    def _browse_vault(self):
        pid = self.obs_project_combo.currentData()
        if pid is None:
            return
        d = QFileDialog.getExistingDirectory(self, "Selecionar pasta do Obsidian Vault")
        if not d:
            return
        cfg = load_config()
        vaults = cfg.get("obsidian_vaults", {})
        vaults[str(pid)] = d
        cfg["obsidian_vaults"] = vaults
        save_config(cfg)
        self._on_obs_project_changed(self.obs_project_combo.currentIndex())

    def _auto_sync_obsidian(self):
        cfg = load_config()
        vaults = cfg.get("obsidian_vaults", {})
        if not vaults:
            return
        s = get_session()
        try:
            synced = 0
            for pid_str, vault_path in vaults.items():
                if not vault_path or not Path(vault_path).is_dir():
                    continue
                project = s.query(Project).get(int(pid_str))
                if not project:
                    continue
                self._sync_project_to_vault(s, project, vault_path)
                synced += 1
            if synced:
                now = datetime.now().strftime("%H:%M")
                self.obs_status_label.setText(f"Auto-sync: {synced} projeto(s) sincronizado(s) às {now}")
        except Exception:
            pass
        finally:
            s.close()

    def _sync_project_to_vault(self, s, project, vault_path):
        base = Path(vault_path) / _sanitize(project.name)
        (base / "Board").mkdir(parents=True, exist_ok=True)
        (base / "Tasks").mkdir(parents=True, exist_ok=True)
        (base / "Reports").mkdir(parents=True, exist_ok=True)
        (base / "Docs").mkdir(parents=True, exist_ok=True)

        readme = [
            f"# {project.name}", "",
            f"**Chave**: {project.key}",
            f"**Descricao**: {project.description or '—'}",
            f"**Criado em**: {project.created_at.strftime('%Y-%m-%d') if project.created_at else '—'}",
            "", "## Estrutura", "",
            "- `Board/` — Estado atual de cada coluna do kanban",
            "- `Tasks/` — Detalhes de cada tarefa",
            "- `Reports/` — Relatorios diarios",
            "- `Docs/` — Documentos do projeto",
        ]
        (base / "README.md").write_text("\n".join(readme), encoding="utf-8")

        columns = s.query(BoardColumn).filter(
            BoardColumn.project_id == project.id
        ).order_by(BoardColumn.order).all()

        for col in columns:
            tasks = (
                s.query(Task)
                .filter(Task.column_id == col.id, Task.deleted_at == None)
                .order_by(Task.rank)
                .all()
            )
            lines = [f"# {col.name}", ""]
            if not tasks:
                lines.append("_Nenhuma tarefa nesta coluna._")
            else:
                for t in tasks:
                    pri = t.priority or "MEDIUM"
                    ttype = t.type or "FEATURE"
                    human = " 🧑‍💻" if t.requires_human else ""
                    lines.append(
                        f"- [[{t.code} - {_sanitize(t.title)}|{t.code}]] "
                        f"[{ttype}] ({pri}){human}"
                    )
            lines.append("")
            col_name = _sanitize(col.name)
            (base / "Board" / f"{col_name}.md").write_text("\n".join(lines), encoding="utf-8")

        all_tasks = (
            s.query(Task)
            .filter(Task.project_id == project.id, Task.deleted_at == None)
            .order_by(Task.number)
            .all()
        )
        for task in all_tasks:
            lines = [
                f"# {task.code} — {task.title}", "",
                f"**Tipo**: {task.type or 'FEATURE'}",
                f"**Prioridade**: {task.priority or 'MEDIUM'}",
                f"**Status**: {task.status}",
                f"**Criado**: {task.created_at.strftime('%Y-%m-%d %H:%M') if task.created_at else '—'}",
            ]
            if task.assignee:
                lines.append(f"**Responsavel**: {task.assignee}")
            if task.due_date:
                lines.append(f"**Prazo**: {task.due_date.strftime('%Y-%m-%d')}")
            if task.requires_human:
                lines.append("**Requer desenvolvedor**: Sim")
            if task.estimate_md:
                lines.append(f"**Estimativa**: {task.estimate_md} dias")
            lines.append("")
            if task.description:
                lines.extend(["## Descricao", "", task.description, ""])
            if task.objective:
                lines.extend(["## Objetivo", "", task.objective, ""])
            if task.acceptance:
                lines.extend(["## Criterios de Aceite", "", task.acceptance, ""])
            if task.checklist:
                lines.extend(["## Checklist", ""])
                for ci in task.checklist:
                    mark = "x" if ci.checked else " "
                    lines.append(f"- [{mark}] {ci.title}")
                lines.append("")
            if task.comments:
                lines.extend(["## Comentarios", ""])
                for c in task.comments:
                    ts = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
                    lines.append(f"### [{c.type}] {ts}")
                    lines.append(c.body or "")
                    lines.append("")
            fname = f"{task.code} - {_sanitize(task.title)}.md"
            (base / "Tasks" / fname).write_text("\n".join(lines), encoding="utf-8")

        notes = s.query(DailyNote).filter(DailyNote.report != "").order_by(DailyNote.date).all()
        for note in notes:
            (base / "Reports" / f"{note.date}.md").write_text(note.report or "", encoding="utf-8")

        from maestro_local.db.models import Document
        docs = s.query(Document).filter(
            (Document.project_id == project.id) | (Document.task_id.in_(
                s.query(Task.id).filter(Task.project_id == project.id)
            ))
        ).all()
        for doc in docs:
            lines = [f"# {doc.title}", ""]
            if doc.body:
                lines.append(doc.body)
            fname = f"{_sanitize(doc.title)}.md"
            (base / "Docs" / fname).write_text("\n".join(lines), encoding="utf-8")

    def _sync_obsidian(self):
        pid = self.obs_project_combo.currentData()
        if pid is None:
            return
        cfg = load_config()
        vault_path = cfg.get("obsidian_vaults", {}).get(str(pid))
        if not vault_path:
            QMessageBox.warning(self, "Vault nao configurado", "Selecione uma pasta de vault primeiro.")
            return

        s = get_session()
        try:
            project = s.query(Project).get(pid)
            if not project:
                return
            self._sync_project_to_vault(s, project, vault_path)
            base = Path(vault_path) / _sanitize(project.name)
            QMessageBox.information(
                self, "Sincronizacao concluida",
                f"Dados exportados para:\n{base}",
            )
        except Exception as e:
            QMessageBox.warning(self, "Erro na sincronizacao", str(e))
        finally:
            s.close()
