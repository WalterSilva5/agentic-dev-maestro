from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import (
    ActivityLog,
    BoardColumn,
    Project,
    Task,
    get_session,
)
from maestro_local.gui.theme import current_theme
from maestro_local.gui.views.labels_view import LabelsView
from maestro_local.i18n import t as _t
from maestro_local.gui.views.metrics_view import MetricsView
from maestro_local.gui.views.todos_view import TodosView
from maestro_local.gui.widgets.pomodoro import PomodoroWidget


class DashboardView(QWidget):
    task_clicked = Signal(int)
    project_clicked = Signal(int)

    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        scroll.setWidget(container)
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(12)

        # Pomodoro em destaque no topo
        pomo_row = QHBoxLayout()
        self.pomodoro = PomodoroWidget()
        self.pomodoro.setMaximumWidth(260)
        self.pomodoro.apply_theme(current_theme())
        pomo_row.addWidget(self.pomodoro)
        pomo_row.addStretch()
        self._layout.addLayout(pomo_row)

        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(10)
        self._layout.addLayout(self._cards_row)

        self._summary_cards = {}
        for key, label in [
            ("total", _t("Tarefas ativas")),
            ("done_7d", _t("Concluidas (7 dias)")),
            ("overdue", _t("Vencidas")),
            ("in_progress", _t("Em progresso")),
        ]:
            card = self._make_summary_card(label)
            self._summary_cards[key] = card
            self._cards_row.addWidget(card["frame"])

        # Digest proativo (standup gerado por IA)
        self._digest_section = QFrame()
        self._digest_section.setProperty("class", "card")
        digest_layout = QVBoxLayout(self._digest_section)
        digest_layout.setContentsMargins(12, 10, 12, 10)
        digest_layout.setSpacing(8)
        digest_head = QHBoxLayout()
        digest_title = QLabel(_t("Digest (standup)"))
        digest_title.setProperty("class", "cardTitle")
        digest_head.addWidget(digest_title)
        digest_head.addStretch()
        self._digest_btn = QPushButton(_t("Gerar com IA"))
        self._digest_btn.setCursor(Qt.PointingHandCursor)
        self._digest_btn.clicked.connect(self._run_digest)
        digest_head.addWidget(self._digest_btn)
        digest_layout.addLayout(digest_head)
        self._digest_result = QLabel(_t('Gere um resumo "feito/fazendo/bloqueios" do seu trabalho recente.'))
        self._digest_result.setWordWrap(True)
        self._digest_result.setObjectName("subtitle")
        self._digest_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        digest_layout.addWidget(self._digest_result)
        self._layout.addWidget(self._digest_section)

        self._overdue_section = QFrame()
        self._overdue_section.setProperty("class", "card")
        self._overdue_layout = QVBoxLayout(self._overdue_section)
        self._overdue_layout.setContentsMargins(12, 10, 12, 10)
        self._overdue_layout.setSpacing(8)
        overdue_title = QLabel(_t("Tarefas vencidas"))
        overdue_title.setProperty("class", "cardTitle")
        self._overdue_layout.addWidget(overdue_title)
        self._overdue_list = QVBoxLayout()
        self._overdue_list.setSpacing(4)
        self._overdue_layout.addLayout(self._overdue_list)
        self._layout.addWidget(self._overdue_section)

        self._activity_section = QFrame()
        self._activity_section.setProperty("class", "card")
        self._activity_layout = QVBoxLayout(self._activity_section)
        self._activity_layout.setContentsMargins(12, 10, 12, 10)
        self._activity_layout.setSpacing(8)
        activity_title = QLabel(_t("Atividade recente"))
        activity_title.setProperty("class", "cardTitle")
        self._activity_layout.addWidget(activity_title)
        self._activity_list = QVBoxLayout()
        self._activity_list.setSpacing(4)
        self._activity_layout.addLayout(self._activity_list)
        self._layout.addWidget(self._activity_section)

        self._projects_section = QFrame()
        self._projects_section.setProperty("class", "card")
        self._projects_layout = QVBoxLayout(self._projects_section)
        self._projects_layout.setContentsMargins(12, 10, 12, 10)
        self._projects_layout.setSpacing(8)
        projects_title = QLabel(_t("Projetos"))
        projects_title.setProperty("class", "cardTitle")
        self._projects_layout.addWidget(projects_title)
        self._projects_list = QVBoxLayout()
        self._projects_list.setSpacing(8)
        self._projects_layout.addLayout(self._projects_list)
        self._layout.addWidget(self._projects_section)

        self._layout.addStretch()

        # Tudo em abas: a própria visão geral é a primeira aba
        self._overview_tab = scroll
        self._tabs = QTabWidget()
        self._tab_metrics = MetricsView()
        self._tab_todos = TodosView()
        self._tab_labels = LabelsView()
        self._tabs.addTab(self._overview_tab, _t("Visão geral"))
        self._tabs.addTab(self._tab_metrics, _t("Métricas"))
        self._tabs.addTab(self._tab_todos, _t("TODOs"))
        self._tabs.addTab(self._tab_labels, _t("Labels"))
        self._tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tabs, 1)

    def _on_tab_changed(self, _index):
        self._refresh_active_tab()

    def _refresh_active_tab(self):
        w = self._tabs.currentWidget()
        if w is self._overview_tab:
            self._refresh_overview()
        elif w and hasattr(w, "refresh"):
            w.refresh()

    def _make_summary_card(self, label_text):
        frame = QFrame()
        frame.setProperty("class", "card")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        value_label = QLabel("0")
        value_label.setObjectName("summaryValue")
        value_label.setAlignment(Qt.AlignLeft)

        title_label = QLabel(label_text)
        title_label.setProperty("class", "hint")

        layout.addWidget(value_label)
        layout.addWidget(title_label)
        return {"frame": frame, "value": value_label}

    def refresh(self):
        self._refresh_active_tab()

    def _run_digest(self):
        from maestro_local.api.app import _digest_context
        from maestro_local.digest import generate_digest
        self._digest_btn.setEnabled(False)
        self._digest_result.setText(_t("Gerando..."))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        s = get_session()
        try:
            context = _digest_context(s, 1)
        finally:
            s.close()
        try:
            d = generate_digest(context)
        except Exception as e:  # noqa: BLE001
            self._digest_result.setText(_t("Erro no digest") + f": {e}")
            return
        finally:
            QApplication.restoreOverrideCursor()
            self._digest_btn.setEnabled(True)

        def _sec(emoji, label, items):
            if not items:
                return ""
            lis = "".join(f"<li>{x}</li>" for x in items)
            return f"<b>{emoji} {label}</b><ul>{lis}</ul>"

        html = ""
        if d.get("summary"):
            html += f"<p>{d['summary']}</p>"
        html += _sec("✅", _t("Feito"), d.get("done"))
        html += _sec("🔨", _t("Fazendo"), d.get("doing"))
        html += _sec("🚧", _t("Bloqueios"), d.get("blockers"))
        self._digest_result.setText(html or _t("Sem conteúdo."))

    def _refresh_overview(self):
        s = get_session()
        try:
            self._refresh_summary(s)
            self._refresh_overdue(s)
            self._refresh_activity(s)
            self._refresh_projects(s)
        finally:
            s.close()

    def _refresh_summary(self, s):
        active_tasks = (
            s.query(Task).filter(Task.deleted_at.is_(None)).all()
        )
        self._summary_cards["total"]["value"].setText(str(len(active_tasks)))

        done_cols = {
            c.id for c in s.query(BoardColumn).filter(BoardColumn.is_done.is_(True)).all()
        }
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        done_recent = [
            t for t in active_tasks
            if t.column_id in done_cols and t.updated_at and t.updated_at >= seven_days_ago
        ]
        self._summary_cards["done_7d"]["value"].setText(str(len(done_recent)))

        today = datetime.utcnow().date()
        overdue = [
            t for t in active_tasks
            if t.due_date and (t.due_date.date() if hasattr(t.due_date, 'date') else t.due_date) < today and t.column_id not in done_cols
        ]
        self._summary_cards["overdue"]["value"].setText(str(len(overdue)))

        fazendo_cols = {
            c.id
            for c in s.query(BoardColumn).filter(BoardColumn.name == "Fazendo").all()
        }
        in_progress = [t for t in active_tasks if t.column_id in fazendo_cols]
        self._summary_cards["in_progress"]["value"].setText(str(len(in_progress)))

    def _refresh_overdue(self, s):
        self._clear_layout(self._overdue_list)

        done_cols = {
            c.id for c in s.query(BoardColumn).filter(BoardColumn.is_done.is_(True)).all()
        }
        today = datetime.utcnow().date()
        overdue_tasks = (
            s.query(Task)
            .filter(
                Task.deleted_at.is_(None),
                Task.due_date < today,
                Task.column_id.notin_(done_cols) if done_cols else True,
            )
            .order_by(Task.due_date.asc())
            .all()
        )

        if not overdue_tasks:
            empty = QLabel(_t("Nenhuma tarefa vencida"))
            empty.setProperty("class", "hint")
            self._overdue_list.addWidget(empty)
            return

        projects = {p.id: p for p in s.query(Project).all()}

        for task in overdue_tasks:
            row = QWidget()
            row.setCursor(Qt.PointingHandCursor)
            hl = QHBoxLayout(row)
            hl.setContentsMargins(8, 6, 8, 6)
            hl.setSpacing(12)

            code_lbl = QLabel(task.code)
            code_lbl.setProperty("class", "hint")
            code_lbl.setFixedWidth(80)
            hl.addWidget(code_lbl)

            title_lbl = QLabel(task.title)
            title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            hl.addWidget(title_lbl)

            due_str = task.due_date.strftime("%d/%m") if hasattr(task.due_date, "strftime") else str(task.due_date)
            due_lbl = QLabel(due_str)
            due_lbl.setProperty("class", "hint")
            hl.addWidget(due_lbl)

            proj = projects.get(task.project_id)
            if proj:
                proj_lbl = QLabel(proj.key)
                proj_lbl.setProperty("class", "hint")
                hl.addWidget(proj_lbl)

            if task.assignee:
                assignee_lbl = QLabel(task.assignee)
                assignee_lbl.setProperty("class", "hint")
                hl.addWidget(assignee_lbl)

            task_id = task.id
            row.mousePressEvent = lambda _, tid=task_id: self.task_clicked.emit(tid)
            self._overdue_list.addWidget(row)

    def _refresh_activity(self, s):
        self._clear_layout(self._activity_list)

        entries = (
            s.query(ActivityLog)
            .order_by(ActivityLog.created_at.desc())
            .limit(15)
            .all()
        )

        if not entries:
            empty = QLabel(_t("Nenhuma atividade registrada"))
            empty.setProperty("class", "hint")
            self._activity_list.addWidget(empty)
            return

        current_date = None
        for entry in entries:
            entry_date = entry.created_at.date() if entry.created_at else None
            if entry_date and entry_date != current_date:
                current_date = entry_date
                date_lbl = QLabel(current_date.strftime("%d/%m/%Y"))
                date_lbl.setProperty("class", "cardTitle")
                self._activity_list.addWidget(date_lbl)

            row = QHBoxLayout()
            row.setSpacing(12)
            row.setContentsMargins(8, 2, 8, 2)

            time_str = entry.created_at.strftime("%H:%M") if entry.created_at else ""
            time_lbl = QLabel(time_str)
            time_lbl.setProperty("class", "hint")
            time_lbl.setFixedWidth(45)
            row.addWidget(time_lbl)

            action_lbl = QLabel(entry.action or "")
            action_lbl.setFixedWidth(100)
            row.addWidget(action_lbl)

            detail_lbl = QLabel(entry.detail or "")
            detail_lbl.setProperty("class", "hint")
            detail_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            detail_lbl.setWordWrap(True)
            row.addWidget(detail_lbl)

            wrapper = QWidget()
            wrapper.setLayout(row)
            self._activity_list.addWidget(wrapper)

    def _refresh_projects(self, s):
        self._clear_layout(self._projects_list)

        projects = s.query(Project).order_by(Project.name).all()

        if not projects:
            empty = QLabel(_t("Nenhum projeto"))
            empty.setProperty("class", "hint")
            self._projects_list.addWidget(empty)
            return

        for project in projects:
            card = QFrame()
            card.setCursor(Qt.PointingHandCursor)
            vl = QVBoxLayout(card)
            vl.setContentsMargins(8, 8, 8, 8)
            vl.setSpacing(8)

            header = QHBoxLayout()
            name_lbl = QLabel(_t("{key} - {name}").format(key=project.key, name=project.name))
            name_lbl.setProperty("class", "cardTitle")
            header.addWidget(name_lbl)
            header.addStretch()
            vl.addLayout(header)

            columns = (
                s.query(BoardColumn)
                .filter(BoardColumn.project_id == project.id)
                .order_by(BoardColumn.order)
                .all()
            )
            tasks = (
                s.query(Task)
                .filter(Task.project_id == project.id, Task.deleted_at.is_(None))
                .all()
            )

            total = len(tasks)
            done_count = sum(
                1 for t in tasks
                if any(c.id == t.column_id and c.is_done for c in columns)
            )

            progress_row = QHBoxLayout()
            progress_row.setSpacing(8)

            bar = QProgressBar()
            bar.setMinimum(0)
            bar.setMaximum(max(total, 1))
            bar.setValue(done_count)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            progress_row.addWidget(bar, 1)

            ratio_lbl = QLabel(f"{done_count}/{total}")
            ratio_lbl.setProperty("class", "hint")
            progress_row.addWidget(ratio_lbl)
            vl.addLayout(progress_row)

            col_tasks = {}
            for t in tasks:
                col_tasks.setdefault(t.column_id, 0)
                col_tasks[t.column_id] += 1

            cols_row = QHBoxLayout()
            cols_row.setSpacing(10)
            for col in columns:
                count = col_tasks.get(col.id, 0)
                if count == 0:
                    continue
                col_lbl = QLabel(f"{col.name}: {count}")
                col_lbl.setProperty("class", "hint")
                cols_row.addWidget(col_lbl)
            cols_row.addStretch()
            vl.addLayout(cols_row)

            pid = project.id
            card.mousePressEvent = lambda _, p=pid: self.project_clicked.emit(p)
            self._projects_list.addWidget(card)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                DashboardView._clear_layout(item.layout())
