import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QDate, QSize, QTimer
from PySide6.QtGui import QFont  # noqa: F401
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QDateEdit,
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

from maestro_local.config import get_active_workspace_id, list_workspaces, load_config, save_config
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
from maestro_local.i18n import t as _t


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() or c in " -_." else "_" for c in name).strip()


class DailyView(QWidget):
    def __init__(self):
        super().__init__()
        self._today = date.today().isoformat()

        main = QVBoxLayout(self)
        main.setContentsMargins(8, 8, 8, 8)
        main.setSpacing(6)

        # Header
        header = QHBoxLayout()
        title = QLabel(_t("Meu Dia"))
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        # Date picker
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setFixedWidth(140)
        self.date_edit.setFixedHeight(28)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        header.addWidget(self.date_edit)

        main.addLayout(header)

        # Scroll content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 2, 0)
        self.content_layout.setSpacing(6)

        # --- Obsidian sync section (top of daily view) ---
        self.obsidian_frame = QFrame()
        self.obsidian_frame.setProperty("class", "card")
        obs_layout = QVBoxLayout(self.obsidian_frame)
        obs_layout.setSpacing(4)

        self.obs_title = QLabel("Obsidian Vault")
        self.obs_title.setProperty("class", "cardTitle")
        obs_layout.addWidget(self.obs_title)

        self.obs_hint = QLabel(
            _t("Configure um vault do Obsidian por projeto para exportar dados como Markdown estruturado.")
        )
        self.obs_hint.setWordWrap(True)
        self.obs_hint.setProperty("class", "hint")
        obs_layout.addWidget(self.obs_hint)

        obs_row1 = QHBoxLayout()
        obs_row1.setSpacing(6)
        self.obs_proj_label = QLabel(_t("Projeto:"))
        self.obs_proj_label.setProperty("class", "sectionLabel")
        obs_row1.addWidget(self.obs_proj_label)

        self.obs_project_combo = QComboBox()
        self.obs_project_combo.setMinimumWidth(100)
        self.obs_project_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.obs_project_combo.currentIndexChanged.connect(self._on_obs_project_changed)
        obs_row1.addWidget(self.obs_project_combo, 1)

        self.obs_browse = QPushButton(_t("Vault..."))
        self.obs_browse.setFixedHeight(24)
        self.obs_browse.setProperty("class", "secondary")
        self.obs_browse.setCursor(Qt.PointingHandCursor)
        self.obs_browse.clicked.connect(self._browse_vault)
        obs_row1.addWidget(self.obs_browse)

        obs_sync = QPushButton(_t("Sync"))
        obs_sync.setFixedHeight(24)
        obs_sync.setMinimumWidth(50)
        obs_sync.setCursor(Qt.PointingHandCursor)
        obs_sync.clicked.connect(self._sync_obsidian)
        obs_row1.addWidget(obs_sync)

        obs_layout.addLayout(obs_row1)

        self.obs_path_input = QLabel(_t("Nenhum vault configurado"))
        self.obs_path_input.setProperty("class", "hint")
        obs_layout.addWidget(self.obs_path_input)

        self.content_layout.addWidget(self.obsidian_frame)

        self.obs_status_label = QLabel("")
        self.obs_status_label.setProperty("class", "hint")
        self.content_layout.addWidget(self.obs_status_label)

        # --- Notes section ---
        self.notes_frame = QFrame()
        self.notes_frame.setProperty("class", "card")
        self.notes_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        notes_layout = QVBoxLayout(self.notes_frame)
        notes_layout.setSpacing(4)
        notes_layout.setContentsMargins(6, 6, 6, 6)

        notes_header = QHBoxLayout()
        self.notes_title = QLabel(_t("Notas do dia"))
        self.notes_title.setProperty("class", "cardTitle")
        notes_header.addWidget(self.notes_title)
        notes_header.addStretch()

        self._editor_mode = "edit"

        self.toggle_btn = QPushButton(_t("Preview"))
        self.toggle_btn.setFixedHeight(24)
        self.toggle_btn.setProperty("class", "secondary")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_preview)
        notes_header.addWidget(self.toggle_btn)

        self.tmpl_btn = QPushButton(_t("Template"))
        self.tmpl_btn.setFixedHeight(24)
        self.tmpl_btn.setProperty("class", "secondary")
        self.tmpl_btn.setCursor(Qt.PointingHandCursor)
        self.tmpl_btn.clicked.connect(self._insert_template)
        notes_header.addWidget(self.tmpl_btn)

        save_btn = QPushButton(_t("Salvar"))
        save_btn.setFixedHeight(24)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_notes)
        notes_header.addWidget(save_btn)
        notes_layout.addLayout(notes_header)

        # Stacked widget: editor (0) / preview (1)
        self.editor_stack = QStackedWidget()
        self.editor_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.editor_stack.setMinimumHeight(150)

        # --- Edit mode ---
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            _t(
                "## Foco do Dia\n"
                "- Objetivo principal:\n"
                "- Prioridade máxima:\n\n"
                "---\n\n"
                "## Tarefas Planejadas\n"
                "- [ ] ...\n\n"
                "---\n\n"
                "## Bloqueios / Problemas / Dúvidas\n"
                "- Descrição do problema\n"
                "- Dependência / quem pode ajudar\n\n"
                "---\n\n"
                "## Anotações Rápidas\n"
                "- Ideias\n"
                "- Decisões tomadas\n"
                "- Links úteis\n\n"
                "---\n\n"
                "## Check-out do Dia\n"
                "- O que foi concluído:\n"
                "- O que ficou pendente:\n"
                "- Próximo passo amanhã:"
            )
        )
        self.notes_edit.setAcceptRichText(False)
        self.notes_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.notes_edit.setProperty("class", "mono")
        self.editor_stack.addWidget(self.notes_edit)

        # --- Preview mode ---
        self.notes_preview = QTextBrowser()
        self.notes_preview.setOpenExternalLinks(True)
        self.notes_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.notes_preview.setProperty("class", "preview")
        self.editor_stack.addWidget(self.notes_preview)

        notes_layout.addWidget(self.editor_stack, 1)
        self.content_layout.addWidget(self.notes_frame)

        # --- Generate report ---
        actions_row = QHBoxLayout()

        gen_btn = QPushButton(_t("Gerar Relatório do Dia"))
        gen_btn.setFixedHeight(28)
        gen_btn.setCursor(Qt.PointingHandCursor)
        gen_btn.clicked.connect(self._generate_report)
        actions_row.addWidget(gen_btn)

        actions_row.addStretch()

        self.backup_btn = QPushButton(_t("Backup DB"))
        self.backup_btn.setFixedHeight(28)
        self.backup_btn.setProperty("class", "secondary")
        self.backup_btn.setCursor(Qt.PointingHandCursor)
        self.backup_btn.setToolTip(_t("Exportar backup do banco de dados SQLite"))
        self.backup_btn.clicked.connect(self._backup_db)
        actions_row.addWidget(self.backup_btn)

        self.content_layout.addLayout(actions_row)

        # --- Activity summary (tasks worked on) ---
        self.activity_frame = QFrame()
        self.activity_frame.setProperty("class", "card")
        self.activity_layout = QVBoxLayout(self.activity_frame)
        self.activity_layout.setSpacing(4)
        self.content_layout.addWidget(self.activity_frame)

        # --- Report output ---
        self.report_frame = QFrame()
        self.report_frame.setProperty("class", "card")
        self.report_frame.setVisible(False)
        report_inner = QVBoxLayout(self.report_frame)
        report_inner.setSpacing(4)

        report_header = QHBoxLayout()
        self.report_title = QLabel(_t("Relatório Gerado"))
        self.report_title.setProperty("class", "cardTitle")
        report_header.addWidget(self.report_title)

        report_header.addStretch()

        hint_btn = QPushButton(_t("Dica IA"))
        hint_btn.setFixedHeight(24)
        hint_btn.setProperty("class", "secondary")
        hint_btn.setCursor(Qt.PointingHandCursor)
        hint_btn.clicked.connect(self._toggle_report_hint)
        report_header.addWidget(hint_btn)

        copy_btn = QPushButton(_t("Copiar"))
        copy_btn.setFixedHeight(24)
        copy_btn.setProperty("class", "secondary")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_report)
        report_header.addWidget(copy_btn)

        export_btn = QPushButton(".md")
        export_btn.setFixedHeight(24)
        export_btn.setProperty("class", "secondary")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_report)
        report_header.addWidget(export_btn)

        report_inner.addLayout(report_header)

        t = current_theme()
        ws_id = get_active_workspace_id()
        ws_name = ws_id
        for ws in list_workspaces():
            if ws["id"] == ws_id:
                ws_name = ws.get("name", ws_id)
                break
        self._hint_prompt = _t(
            "Gere o relatório diário de trabalho de hoje no workspace \"{ws_name}\" "
            "usando a skill maestro-daily-report. "
            "Consulte as atividades e notas do dia via API (porta 9777) e crie um resumo em bullet list."
        ).format(ws_name=ws_name)
        self.report_hint_frame = QFrame()
        self.report_hint_frame.setVisible(False)
        self.report_hint_frame.setStyleSheet(
            f"background: {t.accent_light}; color: {t.text_secondary}; "
            f"border: 1px solid {t.border}; border-radius: 6px; "
        )
        hint_inner = QVBoxLayout(self.report_hint_frame)
        hint_inner.setContentsMargins(8, 6, 8, 6)
        hint_inner.setSpacing(4)

        hint_text = QLabel(_t("Dica: peça a um agente de IA para resumir o relatório do workspace \"{ws_name}\" usando a skill instalada.").format(ws_name=ws_name))
        hint_text.setWordWrap(True)
        hint_text.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px; background: transparent; border: none;")
        hint_inner.addWidget(hint_text)

        hint_prompt_label = QLabel(_t("Prompt sugerido:\n\"{prompt}\"").format(prompt=self._hint_prompt))
        hint_prompt_label.setWordWrap(True)
        hint_prompt_label.setStyleSheet(f"color: {t.text_primary}; font-size: 11px; font-style: italic; background: transparent; border: none;")
        hint_inner.addWidget(hint_prompt_label)

        copy_hint_btn = QPushButton(_t("Copiar prompt"))
        copy_hint_btn.setFixedHeight(22)
        copy_hint_btn.setProperty("class", "secondary")
        copy_hint_btn.setCursor(Qt.PointingHandCursor)
        copy_hint_btn.clicked.connect(self._copy_hint_prompt)
        hint_inner.addWidget(copy_hint_btn, alignment=Qt.AlignLeft)

        report_inner.addWidget(self.report_hint_frame)

        self.report_output = QTextEdit()
        self.report_output.setReadOnly(True)
        self.report_output.setMinimumHeight(180)
        self.report_output.setProperty("class", "mono")
        report_inner.addWidget(self.report_output)
        self.content_layout.addWidget(self.report_frame)

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
        self.date_edit.blockSignals(True)
        qd = QDate.fromString(self._today, "yyyy-MM-dd")
        if qd.isValid():
            self.date_edit.setDate(qd)
        self.date_edit.blockSignals(False)

    def _on_date_changed(self, qdate):
        text = qdate.toString("yyyy-MM-dd")
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
        if self._editor_mode == "edit":
            self._editor_mode = "preview"
            self._update_preview()
            self.editor_stack.setCurrentIndex(1)
            self.toggle_btn.setText(_t("Edit"))
            self.toggle_btn.setProperty("class", "")
            self.toggle_btn.style().unpolish(self.toggle_btn)
            self.toggle_btn.style().polish(self.toggle_btn)
        else:
            self._editor_mode = "edit"
            self.editor_stack.setCurrentIndex(0)
            self.toggle_btn.setText(_t("Preview"))
            self.toggle_btn.setProperty("class", "secondary")
            self.toggle_btn.style().unpolish(self.toggle_btn)
            self.toggle_btn.style().polish(self.toggle_btn)

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
                self, _t("Substituir conteúdo?"),
                _t("Já existe conteúdo nas notas. Deseja substituir pelo template?"),
            )
            if r != QMessageBox.Yes:
                return
        self.notes_edit.setPlainText(
            _t(
                "## Foco do Dia\n"
                "- Objetivo principal:\n"
                "- Prioridade máxima:\n\n"
                "---\n\n"
                "## Tarefas Planejadas\n"
                "- [ ] ...\n\n"
                "---\n\n"
                "## Bloqueios / Problemas / Dúvidas\n"
                "- Descrição do problema\n"
                "- Dependência / quem pode ajudar\n\n"
                "---\n\n"
                "## Anotações Rápidas\n"
                "- Ideias\n"
                "- Decisões tomadas\n"
                "- Links úteis\n\n"
                "---\n\n"
                "## Check-out do Dia\n"
                "- O que foi concluído:\n"
                "- O que ficou pendente:\n"
                "- Próximo passo amanhã:\n"
            )
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

        act_title = QLabel(_t("Atividade do dia"))
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
                empty = QLabel(_t("Nenhuma atividade registrada neste dia"))
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

            lines = [_t("# Relatório Diário — {date}").format(date=self._today), ""]

            # Tasks worked on
            if tasks:
                lines.append(_t("## Tarefas trabalhadas"))
                lines.append("")
                for task in tasks:
                    status = task.status
                    ttype = task.type or "FEATURE"
                    lines.append(f"- **{task.code}** — {task.title} [{ttype}] (_{status}_)")
                lines.append("")

            # Activity timeline
            if activities:
                lines.append(_t("## Atividades"))
                lines.append("")
                for a in activities:
                    time_str = a.created_at.strftime("%H:%M") if a.created_at else ""
                    lines.append(f"- `{time_str}` {a.action}: {a.detail or ''}")
                lines.append("")

            # Comments/reviews of the day
            reviews = [c for c in comments if c.type == "CODE_REVIEW"]
            if reviews:
                lines.append(_t("## Code Reviews"))
                lines.append("")
                for r in reviews:
                    task = s.query(Task).get(r.task_id)
                    code = task.code if task else f"#{r.task_id}"
                    lines.append(f"### {code}")
                    lines.append(r.body or "")
                    lines.append("")

            # User notes
            if user_notes.strip():
                lines.append(_t("## Notas"))
                lines.append("")
                lines.append(user_notes.strip())
                lines.append("")

            # Summary
            lines.append(_t("## Resumo"))
            lines.append("")
            lines.append(_t("- **Tarefas tocadas**: {count}").format(count=len(tasks)))
            lines.append(_t("- **Atividades registradas**: {count}").format(count=len(activities)))
            lines.append(_t("- **Code reviews**: {count}").format(count=len(reviews)))
            done_today = sum(
                1 for task in tasks
                if s.query(BoardColumn).get(task.column_id)
                and s.query(BoardColumn).get(task.column_id).is_done
            )
            lines.append(_t("- **Concluídas hoje**: {count}").format(count=done_today))

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

    def _toggle_report_hint(self):
        self.report_hint_frame.setVisible(not self.report_hint_frame.isVisible())

    def _copy_hint_prompt(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._hint_prompt)

    def _copy_report(self):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.report_output.toPlainText())

    def _export_report(self):
        text = self.report_output.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, _t("Exportar relatório"), f"relatório-{self._today}.md", _t("Markdown (*.md)")
        )
        if path:
            Path(path).write_text(text, encoding="utf-8")

    # --- Backup ---

    def _backup_db(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, _t("Salvar backup"),
            f"maestro-backup-{date.today().isoformat()}.db",
            _t("SQLite Database (*.db)"),
        )
        if not dest:
            return
        try:
            shutil.copy2(DB_PATH, dest)
            QMessageBox.information(
                self, _t("Backup concluído"),
                _t("Banco de dados copiado para:\n{dest}").format(dest=dest),
            )
        except Exception as e:
            QMessageBox.warning(self, _t("Erro no backup"), str(e))

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

    def _get_workspace_vaults(self) -> dict:
        cfg = load_config()
        ws_id = get_active_workspace_id()
        all_vaults = cfg.get("workspace_vaults", {})
        # migrate from old global format
        if "obsidian_vaults" in cfg and ws_id not in all_vaults:
            all_vaults[ws_id] = cfg.pop("obsidian_vaults")
            cfg["workspace_vaults"] = all_vaults
            save_config(cfg)
        return all_vaults.get(ws_id, {})

    def _set_workspace_vault(self, pid_str: str, vault_path: str):
        cfg = load_config()
        ws_id = get_active_workspace_id()
        all_vaults = cfg.get("workspace_vaults", {})
        ws_vaults = all_vaults.get(ws_id, {})
        ws_vaults[pid_str] = vault_path
        all_vaults[ws_id] = ws_vaults
        cfg["workspace_vaults"] = all_vaults
        save_config(cfg)

    def _on_obs_project_changed(self, idx):
        pid = self.obs_project_combo.currentData()
        if pid is None:
            return
        vaults = self._get_workspace_vaults()
        vault_path = vaults.get(str(pid))
        if vault_path:
            self.obs_path_input.setText(vault_path)
            self.obs_path_input.setProperty("class", "sectionLabel")
        else:
            self.obs_path_input.setText(_t("Nenhum vault configurado"))
            self.obs_path_input.setProperty("class", "hint")
        self.obs_path_input.style().unpolish(self.obs_path_input)
        self.obs_path_input.style().polish(self.obs_path_input)

    def _browse_vault(self):
        pid = self.obs_project_combo.currentData()
        if pid is None:
            return
        d = QFileDialog.getExistingDirectory(self, _t("Selecionar pasta do Obsidian Vault"))
        if not d:
            return
        self._set_workspace_vault(str(pid), d)
        self._on_obs_project_changed(self.obs_project_combo.currentIndex())

    def _auto_sync_obsidian(self):
        vaults = self._get_workspace_vaults()
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
                self.obs_status_label.setText(
                    _t("Auto-sync: {count} projeto(s) sincronizado(s) às {time}").format(count=synced, time=now)
                )
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
            f"**Descrição**: {project.description or '—'}",
            f"**Criado em**: {project.created_at.strftime('%Y-%m-%d') if project.created_at else '—'}",
            "", "## Estrutura", "",
            "- `Board/` — Estado atual de cada coluna do kanban",
            "- `Tasks/` — Detalhes de cada tarefa",
            "- `Reports/` — Relatórios diários",
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
                lines.append(f"**Responsável**: {task.assignee}")
            if task.due_date:
                lines.append(f"**Prazo**: {task.due_date.strftime('%Y-%m-%d')}")
            if task.requires_human:
                lines.append("**Requer desenvolvedor**: Sim")
            if task.estimate_md:
                lines.append(f"**Estimativa**: {task.estimate_md} dias")
            lines.append("")
            if task.description:
                lines.extend(["## Descrição", "", task.description, ""])
            if task.objective:
                lines.extend(["## Objetivo", "", task.objective, ""])
            if task.acceptance:
                lines.extend(["## Critérios de Aceite", "", task.acceptance, ""])
            if task.checklist:
                lines.extend(["## Checklist", ""])
                for ci in task.checklist:
                    mark = "x" if ci.checked else " "
                    lines.append(f"- [{mark}] {ci.title}")
                lines.append("")
            if task.comments:
                lines.extend(["## Comentários", ""])
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
        vaults = self._get_workspace_vaults()
        vault_path = vaults.get(str(pid))
        if not vault_path:
            QMessageBox.warning(self, _t("Vault não configurado"), _t("Selecione uma pasta de vault primeiro."))
            return

        s = get_session()
        try:
            project = s.query(Project).get(pid)
            if not project:
                return
            self._sync_project_to_vault(s, project, vault_path)
            base = Path(vault_path) / _sanitize(project.name)
            QMessageBox.information(
                self, _t("Sincronização concluída"),
                _t("Dados exportados para:\n{base}").format(base=base),
            )
        except Exception as e:
            QMessageBox.warning(self, _t("Erro na sincronização"), str(e))
        finally:
            s.close()
