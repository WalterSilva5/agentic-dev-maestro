from datetime import datetime

from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import (
    ActivityLog,
    BoardColumn,
    Comment,
    Label,
    Task,
    TaskChecklist,
    TaskDependency,
    get_session,
)
from maestro_local.gui.theme import TYPE_COLORS, TYPE_LABELS, current_theme


def _h_divider(theme):
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    line.setStyleSheet(f"color: {theme.border_light};")
    line.setFixedHeight(1)
    return line


class TaskDetailDialog(QDialog):
    task_updated = Signal()

    def __init__(self, task_id: int, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setWindowTitle("Detalhes da Tarefa")
        self.resize(800, 700)
        self.setMinimumSize(600, 500)

        t = current_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        s = get_session()
        try:
            task = s.query(Task).get(task_id)
            if not task:
                layout.addWidget(QLabel("Tarefa nao encontrada"))
                return

            # --- Header Row 1: Code, Type, Priority, Column ---
            header1 = QHBoxLayout()
            code_lbl = QLabel(task.code)
            code_lbl.setStyleSheet(
                f"font-family: monospace; font-size: 16px; color: {t.text_muted};"
            )
            header1.addWidget(code_lbl)

            self.type_combo = QComboBox()
            for k, v in TYPE_LABELS.items():
                self.type_combo.addItem(v, k)
            idx = self.type_combo.findData(task.type or "FEATURE")
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.type_combo.currentIndexChanged.connect(
                lambda: self._save_field("type", self.type_combo.currentData())
            )
            header1.addWidget(self.type_combo)

            self.priority_combo = QComboBox()
            for p in ["LOW", "MEDIUM", "HIGH", "URGENT"]:
                self.priority_combo.addItem(p, p)
            idx = self.priority_combo.findData(task.priority or "MEDIUM")
            if idx >= 0:
                self.priority_combo.setCurrentIndex(idx)
            self.priority_combo.currentIndexChanged.connect(
                lambda: self._save_field("priority", self.priority_combo.currentData())
            )
            header1.addWidget(self.priority_combo)

            header1.addStretch()

            self.col_combo = QComboBox()
            columns = (
                s.query(BoardColumn)
                .filter(BoardColumn.project_id == task.project_id)
                .order_by(BoardColumn.order)
                .all()
            )
            for c in columns:
                self.col_combo.addItem(c.name, c.id)
            idx = self.col_combo.findData(task.column_id)
            if idx >= 0:
                self.col_combo.setCurrentIndex(idx)
            self.col_combo.currentIndexChanged.connect(
                lambda: self._move(self.col_combo.currentData())
            )
            col_label = QLabel("Coluna:")
            col_label.setStyleSheet(f"color: {t.text_secondary};")
            header1.addWidget(col_label)
            header1.addWidget(self.col_combo)

            layout.addLayout(header1)

            # --- Header Row 2: Due date, Assignee, Labels ---
            header2 = QHBoxLayout()
            header2.setSpacing(12)

            due_label = QLabel("Prazo:")
            due_label.setStyleSheet(f"color: {t.text_secondary};")
            header2.addWidget(due_label)

            self.due_date_edit = QDateEdit()
            self.due_date_edit.setCalendarPopup(True)
            self.due_date_edit.setDisplayFormat("dd/MM/yyyy")
            self.due_date_edit.setSpecialValueText("Sem data")
            if task.due_date:
                self.due_date_edit.setDate(
                    QDate(task.due_date.year, task.due_date.month, task.due_date.day)
                )
            else:
                self.due_date_edit.setDate(self.due_date_edit.minimumDate())
            self.due_date_edit.dateChanged.connect(self._save_due_date)
            header2.addWidget(self.due_date_edit)

            assignee_label = QLabel("Responsavel:")
            assignee_label.setStyleSheet(f"color: {t.text_secondary};")
            header2.addWidget(assignee_label)

            self.assignee_input = QLineEdit(task.assignee or "")
            self.assignee_input.setPlaceholderText("Responsavel...")
            self.assignee_input.setMaximumWidth(150)
            self.assignee_input.editingFinished.connect(
                lambda: self._save_field(
                    "assignee", self.assignee_input.text().strip() or None
                )
            )
            header2.addWidget(self.assignee_input)

            self.human_check = QCheckBox("Requer desenvolvedor")
            self.human_check.setChecked(task.requires_human or False)
            self.human_check.setToolTip(
                "Marque para tarefas que devem ser feitas por um desenvolvedor humano, "
                "nao por agentes de IA"
            )
            self.human_check.toggled.connect(
                lambda val: self._save_field("requires_human", val)
            )
            header2.addWidget(self.human_check)

            header2.addStretch()
            layout.addLayout(header2)

            layout.addWidget(_h_divider(t))

            # --- Title ---
            self.title_edit = QLineEdit(task.title)
            self.title_edit.setStyleSheet("font-size: 16px; font-weight: 600;")
            self.title_edit.editingFinished.connect(
                lambda: self._save_field("title", self.title_edit.text())
            )
            layout.addWidget(self.title_edit)

            # --- Labels row (rebuilt dynamically) ---
            self._labels_container = QWidget()
            self._labels_container_layout = QVBoxLayout(self._labels_container)
            self._labels_container_layout.setContentsMargins(0, 0, 0, 0)
            self._labels_container_layout.setSpacing(0)
            layout.addWidget(self._labels_container)
            self._rebuild_labels()

            layout.addWidget(_h_divider(t))

            # --- Tabs ---
            tabs = QTabWidget()

            # Info (scrollable)
            info_scroll = QScrollArea()
            info_scroll.setWidgetResizable(True)
            info_scroll.setFrameShape(QFrame.NoFrame)

            info_inner = QWidget()
            info_layout = QVBoxLayout(info_inner)
            info_layout.setSpacing(8)
            info_layout.setContentsMargins(8, 8, 8, 8)

            desc_label = QLabel("Descricao:")
            desc_label.setStyleSheet(f"color: {t.text_secondary}; font-weight: 600; font-size: 12px;")
            info_layout.addWidget(desc_label)
            self.desc_edit = QTextEdit(task.description or "")
            self.desc_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.desc_edit.textChanged.connect(lambda: self._auto_resize(self.desc_edit))
            info_layout.addWidget(self.desc_edit)

            obj_label = QLabel("Objetivo:")
            obj_label.setStyleSheet(f"color: {t.text_secondary}; font-weight: 600; font-size: 12px;")
            info_layout.addWidget(obj_label)
            self.obj_edit = QTextEdit(task.objective or "")
            self.obj_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.obj_edit.textChanged.connect(lambda: self._auto_resize(self.obj_edit))
            info_layout.addWidget(self.obj_edit)

            acc_label = QLabel("Aceite:")
            acc_label.setStyleSheet(f"color: {t.text_secondary}; font-weight: 600; font-size: 12px;")
            info_layout.addWidget(acc_label)
            self.acc_edit = QTextEdit(task.acceptance or "")
            self.acc_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.acc_edit.textChanged.connect(lambda: self._auto_resize(self.acc_edit))
            info_layout.addWidget(self.acc_edit)

            est_row = QHBoxLayout()
            est_label = QLabel("Estimativa:")
            est_label.setStyleSheet(f"color: {t.text_secondary}; font-weight: 600; font-size: 12px;")
            est_row.addWidget(est_label)
            self.est_spin = QDoubleSpinBox()
            self.est_spin.setRange(0, 999)
            self.est_spin.setSingleStep(0.5)
            self.est_spin.setSuffix(" homem-dia")
            self.est_spin.setValue(task.estimate_md or 0)
            est_row.addWidget(self.est_spin)
            est_row.addStretch()
            info_layout.addLayout(est_row)

            save_info = QPushButton("Salvar alteracoes")
            save_info.clicked.connect(self._save_info)
            info_layout.addWidget(save_info)

            info_layout.addWidget(_h_divider(t))
            created_lbl = QLabel(
                f"Criada em: {task.created_at.strftime('%d/%m/%Y %H:%M') if task.created_at else '--'}"
            )
            created_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px;")
            info_layout.addWidget(created_lbl)
            updated_lbl = QLabel(
                f"Atualizada em: {task.updated_at.strftime('%d/%m/%Y %H:%M') if task.updated_at else '--'}"
            )
            updated_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px;")
            info_layout.addWidget(updated_lbl)

            info_layout.addStretch()
            info_scroll.setWidget(info_inner)
            tabs.addTab(info_scroll, "Info")

            # Checklist
            cl_tab = QWidget()
            cl_layout = QVBoxLayout(cl_tab)
            self.cl_list = QWidget()
            self.cl_list_layout = QVBoxLayout(self.cl_list)
            self.cl_list_layout.setContentsMargins(0, 0, 0, 0)
            self.cl_list_layout.setSpacing(4)

            for item in task.checklist:
                self._add_cl_row(item.id, item.title, item.checked)

            cl_layout.addWidget(self.cl_list)
            cl_layout.addStretch()

            add_cl = QHBoxLayout()
            self.cl_input = QLineEdit()
            self.cl_input.setPlaceholderText("Novo item...")
            self.cl_input.returnPressed.connect(self._add_checklist)
            cl_add_btn = QPushButton("+")
            cl_add_btn.setFixedWidth(40)
            cl_add_btn.clicked.connect(self._add_checklist)
            add_cl.addWidget(self.cl_input)
            add_cl.addWidget(cl_add_btn)
            cl_layout.addLayout(add_cl)

            tabs.addTab(cl_tab, "Checklist")

            # Comentarios
            comments_tab = QWidget()
            cm_layout = QVBoxLayout(comments_tab)
            self.comments_list = QListWidget()
            comments = (
                s.query(Comment)
                .filter(Comment.task_id == task_id)
                .order_by(Comment.created_at)
                .all()
            )
            for c in comments:
                type_prefix = ""
                if c.type and c.type != "COMMENT":
                    type_prefix = f"[{c.type}] "
                author = c.author or "local"
                dt = c.created_at.strftime("%d/%m %H:%M") if c.created_at else ""
                self.comments_list.addItem(f"{dt} -- {author}: {type_prefix}{c.body}")
            cm_layout.addWidget(self.comments_list)

            cm_form = QHBoxLayout()
            self.comment_input = QLineEdit()
            self.comment_input.setPlaceholderText("Comentario...")
            self.comment_input.returnPressed.connect(self._add_comment)
            cm_btn = QPushButton("Enviar")
            cm_btn.clicked.connect(self._add_comment)
            cm_form.addWidget(self.comment_input)
            cm_form.addWidget(cm_btn)
            cm_layout.addLayout(cm_form)

            tabs.addTab(comments_tab, f"Comentarios ({len(comments)})")

            # Atividade
            act_tab = QWidget()
            act_layout = QVBoxLayout(act_tab)
            act_list = QListWidget()
            activities = (
                s.query(ActivityLog)
                .filter(
                    ActivityLog.entity_type == "task",
                    ActivityLog.entity_id == task_id,
                )
                .order_by(ActivityLog.created_at.desc())
                .limit(20)
                .all()
            )
            for a in activities:
                dt = a.created_at.strftime("%d/%m %H:%M") if a.created_at else ""
                act_list.addItem(
                    f"{dt} -- {a.action}" + (f": {a.detail}" if a.detail else "")
                )
            if not activities:
                act_list.addItem("Nenhuma atividade registrada.")
            act_layout.addWidget(act_list)
            tabs.addTab(act_tab, "Atividade")

            # Dependencias
            dep_tab = QWidget()
            dep_layout = QVBoxLayout(dep_tab)

            blocked_label = QLabel("Bloqueada por:")
            blocked_label.setStyleSheet("font-weight: 600;")
            dep_layout.addWidget(blocked_label)
            self.blocked_by_list = QListWidget()
            for d in task.blocked_by:
                blocker = d.blocker
                item_text = f"{blocker.code} -- {blocker.title}"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, d.id)
                self.blocked_by_list.addItem(list_item)
            dep_layout.addWidget(self.blocked_by_list)

            blocking_label = QLabel("Bloqueia:")
            blocking_label.setStyleSheet("font-weight: 600;")
            dep_layout.addWidget(blocking_label)
            blocking_list = QListWidget()
            for d in task.blocking:
                blocked = d.blocked
                blocking_list.addItem(f"{blocked.code} -- {blocked.title}")
            dep_layout.addWidget(blocking_list)

            add_dep = QHBoxLayout()
            self.dep_input = QLineEdit()
            self.dep_input.setPlaceholderText("Codigo da tarefa bloqueadora (ex: DEMO-1)")
            dep_btn = QPushButton("Adicionar")
            dep_btn.clicked.connect(self._add_dep)
            add_dep.addWidget(self.dep_input)
            add_dep.addWidget(dep_btn)
            dep_layout.addLayout(add_dep)

            rm_dep_btn = QPushButton("Remover selecionada")
            rm_dep_btn.setProperty("flat", True)
            rm_dep_btn.clicked.connect(self._remove_dep)
            dep_layout.addWidget(rm_dep_btn)

            tabs.addTab(dep_tab, "Dependencias")

            # Subtarefas
            subtasks_tab = QWidget()
            sub_layout = QVBoxLayout(subtasks_tab)

            subtasks = (
                s.query(Task)
                .filter(
                    Task.parent_id == task_id,
                    Task.deleted_at == None,
                )
                .all()
            )

            for st in subtasks:
                row = QHBoxLayout()
                code_st = QLabel(st.code)
                code_st.setStyleSheet(
                    f"font-family: monospace; color: {t.text_muted};"
                )
                row.addWidget(code_st)
                title_st = QLabel(st.title)
                row.addWidget(title_st, 1)
                status_st = QLabel(st.status or "")
                status_st.setStyleSheet(f"color: {t.text_muted};")
                row.addWidget(status_st)
                sub_layout.addLayout(row)

            if not subtasks:
                empty = QLabel("Nenhuma subtarefa")
                empty.setStyleSheet(f"color: {t.text_muted};")
                sub_layout.addWidget(empty)

            sub_layout.addStretch()
            tabs.addTab(subtasks_tab, f"Subtarefas ({len(subtasks)})")

            layout.addWidget(tabs, 1)

            # --- Bottom bar ---
            bottom = QHBoxLayout()
            bottom.addStretch()
            del_btn = QPushButton("Excluir tarefa")
            del_btn.setStyleSheet(f"background-color: {t.danger};")
            del_btn.clicked.connect(self._delete)
            bottom.addWidget(del_btn)
            layout.addLayout(bottom)
        finally:
            s.close()

        QTimer.singleShot(0, self._init_auto_resize)

    # ------------------------------------------------------------------ #
    # Labels management (rebuilt inline, no dialog close)
    # ------------------------------------------------------------------ #

    def _rebuild_labels(self):
        t = current_theme()
        # Clear existing content
        while self._labels_container_layout.count():
            item = self._labels_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                _clear_layout(item.layout())

        labels_row = QWidget()
        row_layout = QHBoxLayout(labels_row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        lbl_label = QLabel("Labels:")
        lbl_label.setStyleSheet(f"color: {t.text_secondary};")
        row_layout.addWidget(lbl_label)

        s = get_session()
        try:
            task = s.query(Task).get(self.task_id)
            if not task:
                return

            applied_ids = set()
            for lbl in task.labels:
                applied_ids.add(lbl.id)
                chip = QLabel(f" {lbl.name} x")
                color = lbl.color or "#868E96"
                chip.setStyleSheet(
                    f"background: {color}; color: white; padding: 2px 8px; "
                    f"border-radius: 10px; font-size: 11px; cursor: pointer;"
                )
                lid = lbl.id
                chip.mousePressEvent = lambda e, x=lid: self._remove_label(x)
                row_layout.addWidget(chip)

            self.label_combo = QComboBox()
            self.label_combo.addItem("+ Adicionar...", None)
            all_labels = s.query(Label).order_by(Label.name).all()
            for l in all_labels:
                if l.id not in applied_ids:
                    self.label_combo.addItem(l.name, l.id)
            self.label_combo.currentIndexChanged.connect(self._add_label_from_combo)
            row_layout.addWidget(self.label_combo)
            row_layout.addStretch()
        finally:
            s.close()

        self._labels_container_layout.addWidget(labels_row)

    # ------------------------------------------------------------------ #
    # Auto-resize text edits
    # ------------------------------------------------------------------ #

    def _auto_resize(self, editor):
        doc_height = int(editor.document().size().height()) + 10
        editor.setFixedHeight(max(36, min(doc_height, 300)))

    def _init_auto_resize(self):
        for ed in (self.desc_edit, self.obj_edit, self.acc_edit):
            self._auto_resize(ed)

    # ------------------------------------------------------------------ #
    # Checklist helpers
    # ------------------------------------------------------------------ #

    def _add_cl_row(self, item_id, title, checked):
        t = current_theme()
        row = QHBoxLayout()
        cb = QCheckBox(title)
        cb.setChecked(checked)
        iid = item_id
        cb.toggled.connect(lambda val, x=iid: self._toggle_cl(x))
        row.addWidget(cb, 1)
        rm = QPushButton("x")
        rm.setFixedSize(24, 24)
        rm.setStyleSheet(
            f"background: transparent; color: {t.danger}; font-weight: bold;"
        )
        rm.clicked.connect(lambda checked, x=iid: self._remove_cl(x))
        row.addWidget(rm)
        w = QWidget()
        w.setLayout(row)
        self.cl_list_layout.addWidget(w)

    # ------------------------------------------------------------------ #
    # Field persistence
    # ------------------------------------------------------------------ #

    def _save_field(self, field, value):
        s = get_session()
        try:
            task = s.query(Task).get(self.task_id)
            if task:
                setattr(task, field, value)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()

    def _save_due_date(self, qdate):
        s = get_session()
        try:
            task = s.query(Task).get(self.task_id)
            if task:
                if qdate == self.due_date_edit.minimumDate():
                    task.due_date = None
                else:
                    task.due_date = datetime(qdate.year(), qdate.month(), qdate.day())
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()

    def _move(self, column_id):
        if column_id is None:
            return
        s = get_session()
        try:
            task = s.query(Task).get(self.task_id)
            if task and task.column_id != column_id:
                old_col = task.column.name if task.column else "?"
                task.column_id = column_id
                new_col = s.query(BoardColumn).get(column_id)
                s.add(
                    ActivityLog(
                        entity_type="task",
                        entity_id=self.task_id,
                        action="moved",
                        detail=f"{old_col} -> {new_col.name if new_col else '?'}",
                    )
                )
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()

    def _save_info(self):
        s = get_session()
        try:
            task = s.query(Task).get(self.task_id)
            if task:
                task.description = self.desc_edit.toPlainText()
                task.objective = self.obj_edit.toPlainText()
                task.acceptance = self.acc_edit.toPlainText()
                task.estimate_md = self.est_spin.value() or None
                s.add(
                    ActivityLog(
                        entity_type="task",
                        entity_id=self.task_id,
                        action="updated",
                    )
                )
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()

    # ------------------------------------------------------------------ #
    # Checklist
    # ------------------------------------------------------------------ #

    def _add_checklist(self):
        title = self.cl_input.text().strip()
        if not title:
            return
        s = get_session()
        try:
            from sqlalchemy import func

            max_order = (
                s.query(func.coalesce(func.max(TaskChecklist.sort_order), -1))
                .filter(TaskChecklist.task_id == self.task_id)
                .scalar()
            )
            item = TaskChecklist(
                task_id=self.task_id, title=title, sort_order=max_order + 1
            )
            s.add(item)
            s.commit()
            self._add_cl_row(item.id, item.title, item.checked)
            self.cl_input.clear()
            self.task_updated.emit()
        finally:
            s.close()

    def _toggle_cl(self, item_id):
        s = get_session()
        try:
            item = s.query(TaskChecklist).get(item_id)
            if item:
                item.checked = not item.checked
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()

    def _remove_cl(self, item_id):
        s = get_session()
        try:
            item = s.query(TaskChecklist).get(item_id)
            if item:
                s.delete(item)
                s.commit()
                for i in reversed(range(self.cl_list_layout.count())):
                    w = self.cl_list_layout.itemAt(i).widget()
                    if w:
                        w.deleteLater()
                remaining = (
                    s.query(TaskChecklist)
                    .filter(TaskChecklist.task_id == self.task_id)
                    .order_by(TaskChecklist.sort_order)
                    .all()
                )
                for it in remaining:
                    self._add_cl_row(it.id, it.title, it.checked)
                self.task_updated.emit()
        finally:
            s.close()

    # ------------------------------------------------------------------ #
    # Comments
    # ------------------------------------------------------------------ #

    def _add_comment(self):
        body = self.comment_input.text().strip()
        if not body:
            return
        s = get_session()
        try:
            c = Comment(task_id=self.task_id, body=body)
            s.add(c)
            s.add(
                ActivityLog(
                    entity_type="task",
                    entity_id=self.task_id,
                    action="commented",
                )
            )
            s.commit()
            dt = c.created_at.strftime("%d/%m %H:%M") if c.created_at else ""
            self.comments_list.addItem(f"{dt} -- local: {body}")
            self.comment_input.clear()
            self.task_updated.emit()
        finally:
            s.close()

    # ------------------------------------------------------------------ #
    # Labels (no dialog close on add/remove)
    # ------------------------------------------------------------------ #

    def _add_label_from_combo(self):
        label_id = self.label_combo.currentData()
        if label_id is None:
            return
        s = get_session()
        try:
            task = s.query(Task).get(self.task_id)
            label = s.query(Label).get(label_id)
            if task and label:
                task.labels.append(label)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()
        self._rebuild_labels()

    def _remove_label(self, label_id):
        s = get_session()
        try:
            task = s.query(Task).get(self.task_id)
            label = s.query(Label).get(label_id)
            if task and label and label in task.labels:
                task.labels.remove(label)
                s.commit()
                self.task_updated.emit()
        finally:
            s.close()
        self._rebuild_labels()

    # ------------------------------------------------------------------ #
    # Dependencies
    # ------------------------------------------------------------------ #

    def _add_dep(self):
        code = self.dep_input.text().strip().upper()
        if not code:
            return
        parts = code.split("-")
        if len(parts) != 2:
            return
        s = get_session()
        try:
            from maestro_local.db.models import Project

            project = s.query(Project).filter(Project.key == parts[0]).first()
            if not project:
                return
            blocker = (
                s.query(Task)
                .filter(
                    Task.project_id == project.id,
                    Task.number == int(parts[1]),
                    Task.deleted_at == None,
                )
                .first()
            )
            if not blocker or blocker.id == self.task_id:
                return
            existing = (
                s.query(TaskDependency)
                .filter(
                    TaskDependency.blocker_id == blocker.id,
                    TaskDependency.blocked_id == self.task_id,
                )
                .first()
            )
            if existing:
                return
            dep = TaskDependency(blocker_id=blocker.id, blocked_id=self.task_id)
            s.add(dep)
            s.add(
                ActivityLog(
                    entity_type="task",
                    entity_id=self.task_id,
                    action="dependency_added",
                    detail=code,
                )
            )
            s.commit()
            self.blocked_by_list.addItem(f"{blocker.code} -- {blocker.title}")
            self.dep_input.clear()
            self.task_updated.emit()
        finally:
            s.close()

    def _remove_dep(self):
        item = self.blocked_by_list.currentItem()
        if not item:
            return
        dep_id = item.data(Qt.UserRole)
        if not dep_id:
            return
        s = get_session()
        try:
            dep = s.query(TaskDependency).get(dep_id)
            if dep:
                s.delete(dep)
                s.add(
                    ActivityLog(
                        entity_type="task",
                        entity_id=self.task_id,
                        action="dependency_removed",
                    )
                )
                s.commit()
                self.blocked_by_list.takeItem(self.blocked_by_list.row(item))
                self.task_updated.emit()
        finally:
            s.close()

    # ------------------------------------------------------------------ #
    # Delete (with confirmation)
    # ------------------------------------------------------------------ #

    def _delete(self):
        reply = QMessageBox.question(
            self,
            "Confirmar exclusao",
            "Tem certeza que deseja excluir esta tarefa?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        s = get_session()
        try:
            task = s.query(Task).get(self.task_id)
            if task:
                task.deleted_at = datetime.utcnow()
                s.add(
                    ActivityLog(
                        entity_type="task",
                        entity_id=self.task_id,
                        action="deleted",
                    )
                )
                s.commit()
                self.task_updated.emit()
                self.accept()
        finally:
            s.close()


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
