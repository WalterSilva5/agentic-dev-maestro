from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import Todo, get_session
from maestro_local.gui.theme import PRIORITY_COLORS, current_theme
from maestro_local.i18n import t as _t

TODO_PRIORITIES = [("LOW", "Baixa"), ("MEDIUM", "Média"), ("HIGH", "Alta")]
TODO_RECURRENCES = [
    ("NONE", "Não repete"), ("DAILY", "Diária"),
    ("WEEKLY", "Semanal"), ("MONTHLY", "Mensal"),
]


class TodoRow(QFrame):
    def __init__(self, todo_data, on_toggle, on_delete, on_update):
        super().__init__()
        t = current_theme()
        self.setStyleSheet(
            f"TodoRow {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-radius: 8px; }}"
            f"TodoRow:hover {{ border-color: {t.border}; }}"
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 10, 6)
        row.setSpacing(8)

        tid = todo_data["id"]
        done = todo_data["done"]

        check = QCheckBox()
        check.setChecked(done)
        check.setCursor(Qt.PointingHandCursor)
        check.toggled.connect(lambda checked: on_toggle(tid, checked))
        row.addWidget(check)

        text = QLabel(todo_data["text"])
        text.setWordWrap(True)
        if done:
            text.setStyleSheet(
                f"color: {t.text_muted}; font-size: 14px; border: none; "
                f"text-decoration: line-through;"
            )
        else:
            text.setStyleSheet(f"color: {t.text_primary}; font-size: 14px; border: none;")
        row.addWidget(text, 1)

        small_combo = (
            f"QComboBox {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 4px; padding: 2px 6px; font-size: 11px; color: {t.text_muted}; }}"
        )

        # Prioridade (edição inline)
        prio_combo = QComboBox()
        for val, label in TODO_PRIORITIES:
            prio_combo.addItem(_t(label), val)
        idx = prio_combo.findData(todo_data.get("priority", "MEDIUM"))
        prio_combo.setCurrentIndex(idx if idx >= 0 else 1)
        prio_combo.setStyleSheet(small_combo)
        pc = PRIORITY_COLORS.get(todo_data.get("priority", "MEDIUM"), t.text_muted)
        prio_combo.setStyleSheet(small_combo + f"QComboBox {{ border-left: 3px solid {pc}; }}")
        prio_combo.currentIndexChanged.connect(
            lambda _i, c=prio_combo: on_update(tid, "priority", c.currentData())
        )
        row.addWidget(prio_combo)

        # Recorrência (edição inline)
        rec_combo = QComboBox()
        for val, label in TODO_RECURRENCES:
            rec_combo.addItem(("🔁 " if val != "NONE" else "") + _t(label), val)
        ridx = rec_combo.findData(todo_data.get("recurrence", "NONE"))
        rec_combo.setCurrentIndex(ridx if ridx >= 0 else 0)
        rec_combo.setStyleSheet(small_combo)
        rec_combo.currentIndexChanged.connect(
            lambda _i, c=rec_combo: on_update(tid, "recurrence", c.currentData())
        )
        row.addWidget(rec_combo)

        # Prazo (edição inline: editar / limpar / definir)
        due = todo_data.get("due_at")
        if due:
            overdue = (not done) and due <= datetime.now()
            due_edit = QDateTimeEdit(QDateTime(due))
            due_edit.setCalendarPopup(True)
            due_edit.setDisplayFormat("dd/MM HH:mm")
            due_edit.setFixedWidth(120)
            due_edit.setStyleSheet(
                f"QDateTimeEdit {{ background: {t.bg_input}; border: 1px solid "
                f"{t.danger if overdue else t.border_light}; border-radius: 4px; "
                f"padding: 2px 6px; font-size: 11px; "
                f"color: {t.danger if overdue else t.text_muted}; }}"
            )
            due_edit.setToolTip(_t("Vencido") if overdue else _t("Agendado"))
            due_edit.dateTimeChanged.connect(
                lambda qdt: on_update(tid, "due_at", qdt.toPython())
            )
            row.addWidget(due_edit)
            clear_btn = QPushButton("🚫")
            clear_btn.setFixedSize(22, 22)
            clear_btn.setCursor(Qt.PointingHandCursor)
            clear_btn.setToolTip(_t("Remover agendamento"))
            clear_btn.setStyleSheet("background: transparent; border: none; font-size: 11px;")
            clear_btn.clicked.connect(lambda: on_update(tid, "due_at_set", None))
            row.addWidget(clear_btn)
        else:
            sched_btn = QPushButton("🕑")
            sched_btn.setFixedSize(24, 24)
            sched_btn.setCursor(Qt.PointingHandCursor)
            sched_btn.setToolTip(_t("Agendar para daqui a 1h"))
            sched_btn.setStyleSheet("background: transparent; border: none; font-size: 13px;")
            sched_btn.clicked.connect(
                lambda: on_update(tid, "due_at_set", QDateTime.currentDateTime().addSecs(3600).toPython())
            )
            row.addWidget(sched_btn)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            f"background: transparent; color: {t.text_muted}; border: none; "
            f"font-size: 14px; border-radius: 4px;"
        )
        del_btn.clicked.connect(lambda: on_delete(tid))
        row.addWidget(del_btn)


class TodosView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(_t("TODOs"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(_t("Lista rápida de pendências, sem board nem colunas"))
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText(_t("Adicionar um TODO..."))
        self.input.returnPressed.connect(self._add)
        add_row.addWidget(self.input, 1)

        self.prio_combo = QComboBox()
        for val, label in TODO_PRIORITIES:
            self.prio_combo.addItem(_t(label), val)
        self.prio_combo.setCurrentIndex(1)  # Média
        self.prio_combo.setFixedWidth(90)
        add_row.addWidget(self.prio_combo)

        self.rec_combo = QComboBox()
        for val, label in TODO_RECURRENCES:
            self.rec_combo.addItem(("🔁 " if val != "NONE" else "") + _t(label), val)
        self.rec_combo.setFixedWidth(110)
        add_row.addWidget(self.rec_combo)

        self.sched_check = QCheckBox(_t("Agendar"))
        self.sched_check.toggled.connect(lambda on: self.due_edit.setEnabled(on))
        add_row.addWidget(self.sched_check)
        self.due_edit = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.due_edit.setEnabled(False)
        self.due_edit.setFixedWidth(150)
        add_row.addWidget(self.due_edit)

        add_btn = QPushButton(_t("Adicionar"))
        add_btn.setFixedHeight(32)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        self.counter = QLabel("")
        self.counter.setObjectName("subtitle")
        layout.addWidget(self.counter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.rows_widget = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setSpacing(6)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.rows_widget)
        layout.addWidget(scroll, 1)

        clear_row = QHBoxLayout()
        clear_row.addStretch()
        self.clear_btn = QPushButton(_t("Limpar concluídos"))
        self.clear_btn.setFixedHeight(28)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        t = current_theme()
        self.clear_btn.setStyleSheet(
            f"background: transparent; color: {t.text_muted}; border: 1px solid {t.border}; "
            f"border-radius: 6px; padding: 4px 12px; font-size: 12px;"
        )
        self.clear_btn.clicked.connect(self._clear_done)
        clear_row.addWidget(self.clear_btn)
        layout.addLayout(clear_row)

        self.refresh()

    def refresh(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        s = get_session()
        try:
            todos = s.query(Todo).order_by(Todo.done, Todo.sort_order, Todo.id).all()

            total = len(todos)
            done = sum(1 for td in todos if td.done)

            if not todos:
                t = current_theme()
                empty = QLabel(_t("Nenhum TODO ainda. Adicione um acima."))
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet(f"color: {t.text_muted}; font-size: 14px; padding: 40px;")
                self.rows_layout.addWidget(empty)
                self.counter.setText("")
            else:
                for td in todos:
                    data = {
                        "id": td.id, "text": td.text, "done": td.done,
                        "priority": td.priority or "MEDIUM", "due_at": td.due_at,
                        "recurrence": td.recurrence or "NONE",
                    }
                    self.rows_layout.addWidget(
                        TodoRow(data, self._toggle, self._delete, self._update)
                    )
                self.counter.setText(_t("{done} de {total} concluídos").format(done=done, total=total))

            self.rows_layout.addStretch()
        finally:
            s.close()

    def _add(self):
        text = self.input.text().strip()
        if not text:
            return
        due = None
        if self.sched_check.isChecked():
            due = self.due_edit.dateTime().toPython()  # datetime local ~= utcnow base
        s = get_session()
        try:
            max_order = s.query(Todo).count()
            s.add(Todo(text=text, sort_order=max_order,
                       priority=self.prio_combo.currentData(), due_at=due,
                       recurrence=self.rec_combo.currentData()))
            s.commit()
            self.input.clear()
            self.sched_check.setChecked(False)
            self.rec_combo.setCurrentIndex(0)
            self.refresh()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _toggle(self, todo_id, checked):
        from maestro_local.db.models import advance_todo_recurrence
        s = get_session()
        try:
            td = s.query(Todo).get(todo_id)
            if td:
                if checked and advance_todo_recurrence(td):
                    pass  # recorrente: reagendado para a próxima ocorrência
                else:
                    td.done = checked
                    td.completed_at = datetime.utcnow() if checked else None
                s.commit()
                self.refresh()
        finally:
            s.close()

    def _update(self, todo_id, field, value):
        """Edição inline: prioridade, recorrência ou prazo.

        "due_at" = edição pelo próprio QDateTimeEdit (salva sem refresh, para
        não destruir o widget durante a edição); "due_at_set" = definir/limpar
        (muda o layout da linha, então recarrega).
        """
        needs_refresh = field == "due_at_set"
        if field == "due_at_set":
            field = "due_at"
        s = get_session()
        try:
            td = s.query(Todo).get(todo_id)
            if td:
                setattr(td, field, value)
                if field == "due_at":
                    td.snoozed_until = None  # reagendou: limpa o adiamento
                s.commit()
        finally:
            s.close()
        if needs_refresh:
            self.refresh()

    def _delete(self, todo_id):
        s = get_session()
        try:
            td = s.query(Todo).get(todo_id)
            if td:
                s.delete(td)
                s.commit()
                self.refresh()
        finally:
            s.close()

    def _clear_done(self):
        s = get_session()
        try:
            s.query(Todo).filter(Todo.done.is_(True)).delete()
            s.commit()
            self.refresh()
        finally:
            s.close()
