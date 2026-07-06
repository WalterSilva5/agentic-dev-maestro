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


class TodoRow(QFrame):
    def __init__(self, todo_data, on_toggle, on_delete):
        super().__init__()
        t = current_theme()
        self.setStyleSheet(
            f"TodoRow {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-radius: 8px; }}"
            f"TodoRow:hover {{ border-color: {t.border}; }}"
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 10, 6)
        row.setSpacing(10)

        tid = todo_data["id"]
        done = todo_data["done"]

        check = QCheckBox()
        check.setChecked(done)
        check.setCursor(Qt.PointingHandCursor)
        check.toggled.connect(lambda checked: on_toggle(tid, checked))
        row.addWidget(check)

        # Bolinha de prioridade
        prio = todo_data.get("priority", "MEDIUM")
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {PRIORITY_COLORS.get(prio, t.text_muted)}; border: none; font-size: 12px;")
        dot.setToolTip(dict(TODO_PRIORITIES).get(prio, prio))
        row.addWidget(dot)

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

        # Horário agendado (vermelho se vencido)
        due = todo_data.get("due_at")
        if due:
            overdue = (not done) and due <= datetime.now()
            due_lbl = QLabel(("⏰ " if overdue else "🕑 ") + due.strftime("%d/%m %H:%M"))
            due_lbl.setStyleSheet(
                f"color: {t.danger if overdue else t.text_muted}; font-size: 11px; "
                f"font-weight: {'700' if overdue else '400'}; border: none;"
            )
            row.addWidget(due_lbl)

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
                    }
                    self.rows_layout.addWidget(TodoRow(data, self._toggle, self._delete))
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
                       priority=self.prio_combo.currentData(), due_at=due))
            s.commit()
            self.input.clear()
            self.sched_check.setChecked(False)
            self.refresh()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _toggle(self, todo_id, checked):
        s = get_session()
        try:
            td = s.query(Todo).get(todo_id)
            if td:
                td.done = checked
                td.completed_at = datetime.utcnow() if checked else None
                s.commit()
                self.refresh()
        finally:
            s.close()

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
