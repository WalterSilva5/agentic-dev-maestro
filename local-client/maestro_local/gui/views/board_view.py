import json
import time
from datetime import date, datetime

from PySide6.QtCore import QMimeData, QPoint, QPropertyAnimation, QRect, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
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
    Comment,
    Project,
    Sprint,
    Task,
    get_session,
)
from maestro_local.gui.theme import PRIORITY_COLORS, TYPE_COLORS, TYPE_LABELS, current_theme
from maestro_local.i18n import t as _t

MIME_TYPE = "application/x-maestro-task"


class FlowLayout(QLayout):
    """Layout horizontal que quebra para a próxima linha quando não cabe.

    Evita que os filtros/botões se sobreponham em janelas estreitas.
    """

    def __init__(self, parent=None, hspacing=8, vspacing=6):
        super().__init__(parent)
        self._items = []
        self._hspace = hspacing
        self._vspace = vspacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size + QSize(2, 2)

    def _do_layout(self, rect, test_only):
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            mn = item.minimumSize()
            w = max(hint.width(), mn.width())
            h = max(hint.height(), mn.height())
            next_x = x + w + self._hspace
            if next_x - self._hspace > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + self._vspace
                next_x = x + w + self._hspace
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), QSize(w, h)))
            x = next_x
            line_height = max(line_height, h)
        return y + line_height - rect.y()

PRIORITY_FILTER_MAP = {
    "Todas": None,
    "Baixa": "LOW",
    "Média": "MEDIUM",
    "Alta": "HIGH",
    "Urgente": "URGENT",
}

TYPE_FILTER_MAP = {
    "Todos": None,
    "Feature": "FEATURE",
    "Bug": "BUG",
    "Tech Debt": "TECH_DEBT",
    "Melhoria": "IMPROVEMENT",
    "Tarefa": "CHORE",
}


# ────────────────────────────────────────────────────────────
# TaskCard
# ────────────────────────────────────────────────────────────

class TaskCard(QFrame):
    clicked = Signal(int)
    move_next = Signal(int)
    sprint_changed = Signal(int, object)  # (task_id, sprint_id|None)
    archive_requested = Signal(int)

    def __init__(self, task_data: dict):
        super().__init__()
        self.task_id = task_data["id"]
        self.task_data = task_data
        self._drag_start = None
        self.setCursor(Qt.PointingHandCursor)

        t = current_theme()

        # Priority-based left border (or red if blocked)
        priority = task_data.get("priority", "MEDIUM")
        pc = PRIORITY_COLORS.get(priority, "#4C6EF5")
        blocked = bool(task_data.get("blocked_by"))
        left_color = t.danger if blocked else pc

        self.setStyleSheet(f"""
            TaskCard {{
                background-color: {t.bg_card};
                border: 1px solid {t.border_light};
                border-left: 4px solid {left_color};
                border-radius: 8px;
            }}
            TaskCard:hover {{
                border-color: {t.border_focus};
                border-left: 4px solid {left_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # -- Blocked indicator (prominent) --
        if blocked:
            blocked_bar = QFrame()
            blocked_bar.setFixedHeight(20)
            blocked_bar.setStyleSheet(
                f"background: {t.danger}; border-radius: 3px;"
            )
            blocked_label = QLabel(_t("BLOQUEADA"))
            blocked_label.setAlignment(Qt.AlignCenter)
            blocked_label.setStyleSheet(
                "color: white; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
            )
            bar_layout = QHBoxLayout(blocked_bar)
            bar_layout.setContentsMargins(6, 0, 6, 0)
            bar_layout.addWidget(blocked_label)
            layout.addWidget(blocked_bar)

        # -- Top row: code + type badge + priority badge --
        top = QHBoxLayout()
        top.setSpacing(6)
        code = QLabel(task_data.get("code", ""))
        code.setStyleSheet(
            f"font-family: monospace; font-size: 11px; color: {t.text_muted}; border: none;"
        )
        top.addWidget(code)

        task_type = task_data.get("type", "FEATURE")
        type_badge = QLabel(TYPE_LABELS.get(task_type, task_type))
        tc = TYPE_COLORS.get(task_type, "#868E96")
        type_badge.setStyleSheet(
            f"background: {tc}; color: white; padding: 1px 6px; "
            f"border-radius: 3px; font-size: 10px; font-weight: 600; border: none;"
        )
        top.addWidget(type_badge)

        pri_badge = QLabel(priority[:3])
        pri_badge.setStyleSheet(
            f"color: {pc}; font-size: 10px; font-weight: 600; border: none;"
        )
        top.addWidget(pri_badge)

        top.addStretch()
        layout.addLayout(top)

        # -- Title --
        title = QLabel(task_data.get("title", ""))
        title.setWordWrap(True)
        title.setStyleSheet(
            f"font-size: 13px; color: {t.text_primary}; border: none; padding: 2px 0;"
        )
        layout.addWidget(title)

        # -- Labels --
        labels = task_data.get("labels", [])
        if labels:
            lbl_row = QHBoxLayout()
            lbl_row.setSpacing(4)
            for lbl in labels[:4]:
                chip = QLabel(lbl["name"])
                color = lbl.get("color", "#868E96")
                chip.setStyleSheet(
                    f"background: {color}; color: white; padding: 1px 6px; "
                    f"border-radius: 8px; font-size: 10px; border: none;"
                )
                lbl_row.addWidget(chip)
            lbl_row.addStretch()
            layout.addLayout(lbl_row)

        # -- Checklist progress --
        checklist = task_data.get("checklist", [])
        if checklist:
            done = sum(1 for c in checklist if c.get("checked"))
            total = len(checklist)
            cl_lbl = QLabel(_t("[ok] {done}/{total}").format(done=done, total=total))
            cl_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
            layout.addWidget(cl_lbl)

        # -- Bottom row: due_date + assignee + comments --
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        has_bottom = False

        # Due date
        due_str = task_data.get("due_date")
        if due_str:
            try:
                due_dt = datetime.fromisoformat(due_str).date()
                overdue = due_dt < date.today()
                due_color = t.danger if overdue else t.text_muted
                due_label = QLabel(f"\U0001f4c5 {due_dt.strftime('%d/%m')}")
                due_label.setStyleSheet(
                    f"color: {due_color}; font-size: 11px; font-weight: {'700' if overdue else '400'}; border: none;"
                )
                bottom.addWidget(due_label)
                has_bottom = True
            except (ValueError, TypeError):
                pass

        # Assignee initials
        assignee = task_data.get("assignee")
        if assignee:
            initials = "".join(
                part[0].upper() for part in assignee.split()[:2] if part
            ) or "?"
            avatar = QLabel(initials)
            avatar.setFixedSize(20, 20)
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet(
                f"background: {t.accent}; color: {t.text_on_accent}; "
                f"border-radius: 10px; font-size: 9px; font-weight: 700; border: none;"
            )
            bottom.addWidget(avatar)
            has_bottom = True

        # Requires human badge
        if task_data.get("requires_human"):
            human_badge = QLabel(_t("DEV"))
            human_badge.setStyleSheet(
                f"background: {t.warning}; color: white; padding: 1px 6px; "
                f"border-radius: 3px; font-size: 9px; font-weight: 700; border: none;"
            )
            human_badge.setToolTip(_t("Requer desenvolvedor"))
            bottom.addWidget(human_badge)
            has_bottom = True

        # Comment count
        comments_count = task_data.get("comments_count", 0)
        if comments_count > 0:
            cmt = QLabel(f"\U0001f4ac {comments_count}")
            cmt.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
            bottom.addWidget(cmt)
            has_bottom = True

        if has_bottom:
            bottom.addStretch()
            layout.addLayout(bottom)

        # -- Ação no rodapé: arquivar (colunas concluídas) ou avançar --
        if task_data.get("can_archive"):
            arch_btn = QPushButton(_t("Arquivar"))
            arch_btn.setProperty("class", "quickMove")
            arch_btn.setCursor(Qt.PointingHandCursor)
            arch_btn.setToolTip(_t("Arquivar: some do board e vai para Arquivados"))
            arch_btn.clicked.connect(lambda: self.archive_requested.emit(self.task_id))
            layout.addWidget(arch_btn, alignment=Qt.AlignRight)
        else:
            move_btn = QPushButton(_t("Mover →"))
            move_btn.setProperty("class", "quickMove")
            move_btn.setCursor(Qt.PointingHandCursor)
            move_btn.setToolTip(_t("Mover para próxima coluna"))
            move_btn.clicked.connect(lambda: self.move_next.emit(self.task_id))
            layout.addWidget(move_btn, alignment=Qt.AlignRight)

    # ── Drag & drop (unchanged) ──────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._drag_start:
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 20:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_TYPE, json.dumps({"task_id": self.task_id}).encode())
        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self._drag_start)

        drag.exec(Qt.MoveAction)
        self._drag_start = None

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_start:
            if (event.position().toPoint() - self._drag_start).manhattanLength() < 20:
                self.clicked.emit(self.task_id)
        self._drag_start = None
        super().mouseReleaseEvent(event)


# ────────────────────────────────────────────────────────────
# DropZone
# ────────────────────────────────────────────────────────────

class DropZone(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(40)
        self.setAcceptDrops(True)
        self._active = False

    def _set_active(self, active):
        if active != self._active:
            self._active = active
            t = current_theme()
            if active:
                self.setStyleSheet(
                    f"background: {t.accent_light}; border: 2px dashed {t.accent}; border-radius: 6px;"
                )
            else:
                self.setStyleSheet("")

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()
            self._set_active(True)

    def dragLeaveEvent(self, event):
        self._set_active(False)

    def dropEvent(self, event):
        self._set_active(False)
        parent = self.parent()
        while parent and not isinstance(parent, ColumnWidget):
            parent = parent.parent()
        if parent:
            parent.dropEvent(event)


# ────────────────────────────────────────────────────────────
# ColumnWidget
# ────────────────────────────────────────────────────────────

class ColumnWidget(QWidget):
    task_changed = Signal()

    def __init__(self, column_data: dict, project_id: int):
        super().__init__()
        self.column_id = column_data["id"]
        self.column_name = column_data["name"]
        self.project_id = project_id
        self.wip_limit = column_data.get("wip_limit")
        self.is_done = column_data.get("is_done", False)
        self.setFixedWidth(300)
        self.setAcceptDrops(True)
        self._highlight = False
        self._cards: list[TaskCard] = []

        t = current_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- Column header container --
        header_frame = QFrame()
        done_accent = t.success if self.is_done else t.bg_badge
        header_frame.setStyleSheet(
            f"QFrame {{ background: {done_accent}; border-radius: 10px 10px 0 0; "
            f"padding: 10px 12px; }}"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)

        name = QLabel(column_data["name"])
        name_color = t.text_on_accent if self.is_done else t.text_primary
        name.setStyleSheet(
            f"font-weight: 700; font-size: 13px; color: {name_color}; border: none; "
            f"letter-spacing: 0.3px;"
        )
        header_layout.addWidget(name)

        # Count badge with WIP limit awareness
        task_count = len(column_data.get("tasks", []))
        if self.wip_limit and self.wip_limit > 0:
            count_text = f"{task_count}/{self.wip_limit}"
            over_limit = task_count > self.wip_limit
        else:
            count_text = str(task_count)
            over_limit = False

        self.count_label = QLabel(count_text)
        badge_bg = t.danger if over_limit else (t.bg_card if self.is_done else t.bg_badge)
        badge_fg = "white" if over_limit else t.text_muted
        self.count_label.setStyleSheet(
            f"background: {badge_bg}; color: {badge_fg}; "
            f"padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;"
        )
        header_layout.addWidget(self.count_label)
        header_layout.addStretch()
        layout.addWidget(header_frame)

        # -- Cards scroll area --
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {t.bg_secondary}; }}"
        )
        scroll.setAcceptDrops(True)

        cards_widget = QWidget()
        cards_widget.setAcceptDrops(True)
        cards_widget.setStyleSheet(f"background: {t.bg_secondary}; border: none;")
        self.cards_layout = QVBoxLayout(cards_widget)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        self.cards_layout.setSpacing(8)

        for task in column_data.get("tasks", []):
            card = TaskCard(task)
            card.clicked.connect(self._open_task)
            card.move_next.connect(self._move_to_next)
            card.archive_requested.connect(self._on_archive)
            self.cards_layout.addWidget(card)
            self._cards.append(card)

        self.drop_zone = DropZone()
        self.cards_layout.addWidget(self.drop_zone)
        self.cards_layout.addStretch()
        scroll.setWidget(cards_widget)
        layout.addWidget(scroll, 1)

        # -- Quick add input --
        add_frame = QFrame()
        add_frame.setStyleSheet(
            f"QFrame {{ background: {t.bg_secondary}; border-radius: 0 0 10px 10px; "
            f"border-top: 1px solid {t.border_light}; padding: 4px 6px; }}"
        )
        add_row = QHBoxLayout(add_frame)
        add_row.setContentsMargins(6, 4, 6, 6)
        add_row.setSpacing(6)

        plus_icon = QLabel("+")
        plus_icon.setFixedSize(22, 22)
        plus_icon.setAlignment(Qt.AlignCenter)
        plus_icon.setStyleSheet(
            f"background: {t.accent}; color: {t.text_on_accent}; "
            f"border-radius: 11px; font-size: 14px; font-weight: 700;"
        )
        add_row.addWidget(plus_icon)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText(_t("Nova tarefa..."))
        self.add_input.setStyleSheet(
            f"QLineEdit {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px; color: {t.text_primary}; }}"
            f"QLineEdit:focus {{ border-color: {t.accent}; }}"
        )
        self.add_input.returnPressed.connect(self._add_task)
        add_row.addWidget(self.add_input)
        layout.addWidget(add_frame)

    def _on_sprint_changed(self, task_id, sprint_id):
        s = get_session()
        try:
            task = s.query(Task).get(task_id)
            if task:
                task.sprint_id = sprint_id
                s.commit()
        finally:
            s.close()
        self.task_changed.emit()

    def _on_archive(self, task_id):
        s = get_session()
        try:
            task = s.query(Task).get(task_id)
            if task:
                task.archived_at = datetime.utcnow()
                s.commit()
        finally:
            s.close()
        self.task_changed.emit()

    def get_cards(self) -> list[TaskCard]:
        return list(self._cards)

    def _update_highlight(self, active):
        if active != self._highlight:
            self._highlight = active
            t = current_theme()
            if active:
                self.setStyleSheet(
                    f"ColumnWidget {{ border: 2px dashed {t.accent}; border-radius: 8px; }}"
                )
            else:
                self.setStyleSheet("")

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()
            self._update_highlight(True)

    def dragLeaveEvent(self, event):
        self._update_highlight(False)

    def dropEvent(self, event):
        self._update_highlight(False)
        if not event.mimeData().hasFormat(MIME_TYPE):
            return
        data = json.loads(bytes(event.mimeData().data(MIME_TYPE)).decode())
        task_id = data["task_id"]
        s = get_session()
        try:
            task = s.query(Task).get(task_id)
            if not task or task.column_id == self.column_id:
                return
            old_col_name = task.column.name if task.column else "?"
            if self.column_name.lower() in ("revisão", "revisao", "review"):
                has_review = (
                    s.query(Comment)
                    .filter(Comment.task_id == task.id, Comment.type == "CODE_REVIEW")
                    .first()
                )
                if not has_review:
                    from PySide6.QtWidgets import QMessageBox

                    QMessageBox.warning(
                        self,
                        _t("Code Review obrigatório"),
                        _t(
                            "Adicione um comentário de Code Review antes de mover para Revisão.\n\n"
                            "Abra a tarefa e adicione um comentário do tipo CODE_REVIEW."
                        ),
                    )
                    return
            task.column_id = self.column_id
            task.updated_at = __import__("datetime").datetime.utcnow()
            s.add(
                ActivityLog(
                    entity_type="task",
                    entity_id=task_id,
                    action="moved",
                    detail=f"{old_col_name} -> {self.column_name}",
                )
            )
            s.commit()
            event.acceptProposedAction()
            self.task_changed.emit()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _add_task(self):
        title = self.add_input.text().strip()
        if not title:
            return
        s = get_session()
        try:
            project = s.query(Project).get(self.project_id)
            if not project:
                return
            project.task_seq += 1
            task = Task(
                project_id=self.project_id,
                column_id=self.column_id,
                number=project.task_seq,
                title=title,
                rank=f"{int(time.time() * 1000):x}",
            )
            s.add(task)
            s.commit()
            self.add_input.clear()
            self.task_changed.emit()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _move_to_next(self, task_id):
        s = get_session()
        try:
            task = s.query(Task).get(task_id)
            if not task:
                return
            columns = (
                s.query(BoardColumn)
                .filter(BoardColumn.project_id == self.project_id)
                .order_by(BoardColumn.order)
                .all()
            )
            col_ids = [c.id for c in columns]
            try:
                idx = col_ids.index(task.column_id)
            except ValueError:
                return
            if idx >= len(col_ids) - 1:
                return
            next_col = columns[idx + 1]
            old_col_name = task.column.name if task.column else "?"
            task.column_id = next_col.id
            task.updated_at = __import__("datetime").datetime.utcnow()
            s.add(
                ActivityLog(
                    entity_type="task",
                    entity_id=task_id,
                    action="moved",
                    detail=f"{old_col_name} -> {next_col.name}",
                )
            )
            s.commit()
            self.task_changed.emit()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _open_task(self, task_id):
        from maestro_local.gui.views.task_detail_dialog import TaskDetailDialog

        dlg = TaskDetailDialog(task_id, self)
        dlg.task_updated.connect(lambda: self.task_changed.emit())
        dlg.exec()


# ────────────────────────────────────────────────────────────
# FilterBar
# ────────────────────────────────────────────────────────────

class FilterBar(QWidget):
    filters_changed = Signal()

    def __init__(self):
        super().__init__()

        # FlowLayout: os filtros quebram para a próxima linha em vez de sobrepor.
        layout = FlowLayout(self, hspacing=8, vspacing=6)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_t("\U0001f50d Buscar por título ou código..."))
        self.search_input.setMinimumWidth(240)
        self.search_input.textChanged.connect(self._emit_changed)
        layout.addWidget(self.search_input)

        # Type filter
        type_label = QLabel(_t("Tipo:"))
        type_label.setProperty("class", "sectionLabel")
        layout.addWidget(type_label)
        self.type_combo = QComboBox()
        for _key in TYPE_FILTER_MAP.keys():
            self.type_combo.addItem(_t(_key), _key)
        self.type_combo.setMinimumWidth(96)
        self.type_combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(self.type_combo)

        # Priority filter
        pri_label = QLabel(_t("Prioridade:"))
        pri_label.setProperty("class", "sectionLabel")
        layout.addWidget(pri_label)
        self.priority_combo = QComboBox()
        for _key in PRIORITY_FILTER_MAP.keys():
            self.priority_combo.addItem(_t(_key), _key)
        self.priority_combo.setMinimumWidth(92)
        self.priority_combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(self.priority_combo)

        # Assignee filter
        assignee_label = QLabel(_t("Responsável:"))
        assignee_label.setProperty("class", "sectionLabel")
        layout.addWidget(assignee_label)
        self.assignee_combo = QComboBox()
        self.assignee_combo.addItem(_t("Todos"), "Todos")
        self.assignee_combo.setMinimumWidth(110)
        self.assignee_combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(self.assignee_combo)

        # Task count
        self.count_label = QLabel(_t("0 tarefas"))
        self.count_label.setProperty("class", "hint")
        layout.addWidget(self.count_label)

        sp = self.sizePolicy()
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)

    def _emit_changed(self):
        self.filters_changed.emit()

    def get_search_text(self) -> str:
        return self.search_input.text().strip().lower()

    def get_type_filter(self):
        return TYPE_FILTER_MAP.get(self.type_combo.currentData())

    def get_priority_filter(self):
        return PRIORITY_FILTER_MAP.get(self.priority_combo.currentData())

    def get_assignee_filter(self):
        data = self.assignee_combo.currentData()
        if data == "Todos":
            return None
        if data == "Sem responsável":
            return "__none__"
        return data

    def load_assignees(self, assignees: list[str]):
        current = self.assignee_combo.currentData()
        self.assignee_combo.blockSignals(True)
        self.assignee_combo.clear()
        self.assignee_combo.addItem(_t("Todos"), "Todos")
        self.assignee_combo.addItem(_t("Sem responsável"), "Sem responsável")
        for a in sorted(set(assignees)):
            self.assignee_combo.addItem(a, a)
        idx = self.assignee_combo.findData(current)
        if idx >= 0:
            self.assignee_combo.setCurrentIndex(idx)
        self.assignee_combo.blockSignals(False)

    def set_count(self, visible: int, total: int):
        if visible == total:
            self.count_label.setText(_t("{total} tarefas").format(total=total))
        else:
            self.count_label.setText(
                _t("{visible}/{total} tarefas").format(visible=visible, total=total)
            )


# ────────────────────────────────────────────────────────────
# SprintManagerDialog
# ────────────────────────────────────────────────────────────

SPRINT_STATUS_LABELS = {
    "PLANEJADA": "Planejada", "ATIVA": "Ativa", "CONCLUIDA": "Concluída",
}


class SprintManagerDialog(QDialog):
    """Cria e gerencia as sprints de um projeto (ativar, concluir, excluir)."""

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle(_t("Sprints do projeto"))
        self.resize(580, 520)
        root = QVBoxLayout(self)
        root.setSpacing(10)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(_t("Nome da sprint"))
        form.addRow(_t("Nome:"), self.name_input)
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText(_t("Meta/objetivo"))
        form.addRow(_t("Meta:"), self.goal_input)
        self.capacity_input = QDoubleSpinBox()
        self.capacity_input.setRange(0, 100000)
        self.capacity_input.setDecimals(1)
        self.capacity_input.setSuffix(" hd")
        form.addRow(_t("Capacidade:"), self.capacity_input)
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("AAAA-MM-DD")
        form.addRow(_t("Início:"), self.start_input)
        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("AAAA-MM-DD")
        form.addRow(_t("Fim:"), self.end_input)
        root.addLayout(form)

        create_btn = QPushButton(_t("+ Criar sprint"))
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.clicked.connect(self._create)
        root.addWidget(create_btn, alignment=Qt.AlignRight)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.scroll.setWidget(self.list_container)
        root.addWidget(self.scroll, 1)

        self._load()

    def _parse_date(self, text):
        text = (text or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    def _create(self):
        name = self.name_input.text().strip()
        if not name:
            return
        s = get_session()
        try:
            order = s.query(Sprint).filter(Sprint.project_id == self.project_id).count()
            s.add(Sprint(
                project_id=self.project_id, name=name,
                goal=self.goal_input.text().strip() or None,
                capacity=self.capacity_input.value() or None,
                start_date=self._parse_date(self.start_input.text()),
                end_date=self._parse_date(self.end_input.text()),
                sort_order=order,
            ))
            s.commit()
        finally:
            s.close()
        self.name_input.clear()
        self.goal_input.clear()
        self.capacity_input.setValue(0)
        self.start_input.clear()
        self.end_input.clear()
        self._load()

    def _load(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        t = current_theme()
        s = get_session()
        try:
            sprints = (
                s.query(Sprint)
                .filter(Sprint.project_id == self.project_id)
                .order_by(Sprint.sort_order, Sprint.id)
                .all()
            )
            if not sprints:
                empty = QLabel(_t("Nenhuma sprint ainda."))
                empty.setStyleSheet(f"color: {t.text_muted}; padding: 16px;")
                self.list_layout.addWidget(empty)
            for sp in sprints:
                self.list_layout.addWidget(self._sprint_row(sp, t))
            self.list_layout.addStretch()
        finally:
            s.close()

    def _sprint_row(self, sp, t):
        tasks = [tk for tk in sp.tasks if tk.deleted_at is None]
        done = [tk for tk in tasks if tk.column and tk.column.is_done]
        committed = sum(tk.estimate_md or 0 for tk in tasks)
        progress = round(len(done) / len(tasks) * 100) if tasks else 0

        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 8px; }}"
        )
        v = QVBoxLayout(row)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)

        top = QHBoxLayout()
        name = QLabel(sp.name)
        name.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {t.text_primary}; border: none;")
        top.addWidget(name)
        status_lbl = QLabel(_t(SPRINT_STATUS_LABELS.get(sp.status, sp.status)))
        sc = t.accent if sp.status == "ATIVA" else (t.success if sp.status == "CONCLUIDA" else t.text_muted)
        status_lbl.setStyleSheet(
            f"background: {t.bg_badge}; color: {sc}; padding: 1px 8px; border-radius: 4px; "
            f"font-size: 11px; font-weight: 600; border: none;"
        )
        top.addWidget(status_lbl)
        top.addStretch()
        v.addLayout(top)

        if sp.goal:
            goal = QLabel(sp.goal)
            goal.setWordWrap(True)
            goal.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px; border: none;")
            v.addWidget(goal)

        cap_txt = ""
        over = sp.capacity is not None and committed > sp.capacity
        if sp.capacity is not None:
            cap_txt = _t(" / capacidade {cap}hd").format(cap=f"{sp.capacity:.0f}") + (" ⚠" if over else "")
        stats = QLabel(
            _t("{done}/{total} tarefas · {progress}% · comprometido {committed}hd").format(
                done=len(done), total=len(tasks), progress=progress, committed=f"{committed:.0f}"
            ) + cap_txt
        )
        stats.setStyleSheet(
            f"color: {t.danger if over else t.text_muted}; font-size: 11px; border: none;"
        )
        v.addWidget(stats)

        btns = QHBoxLayout()
        btns.addStretch()
        if sp.status not in ("ATIVA", "CONCLUIDA"):
            act = QPushButton(_t("Ativar"))
            act.setCursor(Qt.PointingHandCursor)
            act.clicked.connect(lambda _=False, sid=sp.id: self._activate(sid))
            btns.addWidget(act)
        if sp.status != "CONCLUIDA":
            comp = QPushButton(_t("Concluir"))
            comp.setCursor(Qt.PointingHandCursor)
            comp.clicked.connect(lambda _=False, sid=sp.id: self._complete(sid))
            btns.addWidget(comp)
        dele = QPushButton(_t("Excluir"))
        dele.setCursor(Qt.PointingHandCursor)
        dele.setStyleSheet(f"QPushButton {{ color: {t.danger}; }}")
        dele.clicked.connect(lambda _=False, sid=sp.id: self._delete(sid))
        btns.addWidget(dele)
        v.addLayout(btns)
        return row

    def _activate(self, sprint_id):
        s = get_session()
        try:
            sp = s.query(Sprint).get(sprint_id)
            if sp:
                for other in s.query(Sprint).filter(
                    Sprint.project_id == sp.project_id, Sprint.id != sp.id, Sprint.status == "ATIVA"
                ).all():
                    other.status = "PLANEJADA"
                sp.status = "ATIVA"
                s.commit()
        finally:
            s.close()
        self._load()

    def _complete(self, sprint_id):
        s = get_session()
        try:
            sp = s.query(Sprint).get(sprint_id)
            if sp:
                for tk in [x for x in sp.tasks if x.deleted_at is None]:
                    if not (tk.column and tk.column.is_done):
                        tk.sprint_id = None  # volta ao backlog
                sp.status = "CONCLUIDA"
                s.commit()
        finally:
            s.close()
        self._load()

    def _delete(self, sprint_id):
        reply = QMessageBox.question(
            self, _t("Confirmar exclusão"),
            _t("Excluir a sprint? As tarefas voltam ao backlog."),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        s = get_session()
        try:
            sp = s.query(Sprint).get(sprint_id)
            if sp:
                for tk in sp.tasks:
                    tk.sprint_id = None
                s.delete(sp)
                s.commit()
        finally:
            s.close()
        self._load()


# ────────────────────────────────────────────────────────────
# ArchivedDialog
# ────────────────────────────────────────────────────────────

class ArchivedDialog(QDialog):
    """Board à parte com as tarefas arquivadas (desarquivar volta ao board)."""

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle(_t("Tarefas arquivadas"))
        self.resize(560, 500)
        root = QVBoxLayout(self)
        root.setSpacing(8)

        hint = QLabel(
            _t("Cards concluídos há mais de 3 dias são arquivados automaticamente e somem do board.")
        )
        hint.setWordWrap(True)
        hint.setProperty("class", "hint")
        root.addWidget(hint)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.scroll.setWidget(self.list_container)
        root.addWidget(self.scroll, 1)

        self._load()

    def _load(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        t = current_theme()
        s = get_session()
        try:
            tasks = (
                s.query(Task)
                .filter(
                    Task.project_id == self.project_id,
                    Task.deleted_at == None,  # noqa: E711
                    Task.archived_at != None,  # noqa: E711
                )
                .order_by(Task.archived_at.desc())
                .all()
            )
            if not tasks:
                empty = QLabel(_t("Nenhuma tarefa arquivada."))
                empty.setStyleSheet(f"color: {t.text_muted}; padding: 16px;")
                self.list_layout.addWidget(empty)
            for task in tasks:
                self.list_layout.addWidget(self._row(task, t))
            self.list_layout.addStretch()
        finally:
            s.close()

    def _row(self, task, t):
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 8px; }}"
        )
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(8)
        when = task.archived_at.strftime("%d/%m") if task.archived_at else ""
        lbl = QLabel(f"{task.code}  {task.title}")
        lbl.setStyleSheet(f"color: {t.text_primary}; font-size: 13px; border: none;")
        lbl.setWordWrap(True)
        h.addWidget(lbl, 1)
        when_lbl = QLabel(when)
        when_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        h.addWidget(when_lbl)
        btn = QPushButton(_t("Desarquivar"))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _=False, tid=task.id: self._unarchive(tid))
        h.addWidget(btn)
        return row

    def _unarchive(self, task_id):
        s = get_session()
        try:
            task = s.query(Task).get(task_id)
            if task:
                task.archived_at = None
                if task.column and task.column.is_done:
                    task.done_at = datetime.utcnow()  # reinicia a contagem
                s.commit()
        finally:
            s.close()
        self._load()


# ────────────────────────────────────────────────────────────
# SprintPlanningView — board de alocação (colunas = Backlog + sprints)
# ────────────────────────────────────────────────────────────

class SprintPlanningView(QWidget):
    task_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        intro = QLabel(_t("Distribua o backlog entre as sprints. Cada card tem um seletor para mover de sprint."))
        intro.setObjectName("subtitle")
        intro.setWordWrap(True)
        root.addWidget(intro)

        # Criar sprint
        form = QHBoxLayout()
        form.setSpacing(6)
        self.name_in = QLineEdit()
        self.name_in.setPlaceholderText(_t("Nome da sprint"))
        form.addWidget(self.name_in, 2)
        self.goal_in = QLineEdit()
        self.goal_in.setPlaceholderText(_t("Meta/objetivo"))
        form.addWidget(self.goal_in, 2)
        self.cap_in = QDoubleSpinBox()
        self.cap_in.setRange(0, 100000)
        self.cap_in.setDecimals(1)
        self.cap_in.setSuffix(" hd")
        form.addWidget(self.cap_in)
        add_btn = QPushButton(_t("+ Criar sprint"))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._create)
        form.addWidget(add_btn)
        root.addLayout(form)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.cont = QWidget()
        self.cols_layout = QHBoxLayout(self.cont)
        self.cols_layout.setAlignment(Qt.AlignLeft)
        self.cols_layout.setSpacing(10)
        self.scroll.setWidget(self.cont)
        root.addWidget(self.scroll, 1)

    def set_project(self, project_id):
        self.project_id = project_id
        self.refresh()

    def refresh(self):
        while self.cols_layout.count():
            item = self.cols_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.project_id:
            return
        t = current_theme()
        s = get_session()
        try:
            sprints = (
                s.query(Sprint)
                .filter(Sprint.project_id == self.project_id)
                .order_by(Sprint.sort_order, Sprint.id)
                .all()
            )
            tasks = s.query(Task).filter(
                Task.project_id == self.project_id,
                Task.deleted_at == None,  # noqa: E711
                Task.archived_at == None,  # noqa: E711
            ).all()
            opts = [(sp.id, sp.name) for sp in sprints]
            backlog = [tk for tk in tasks if tk.sprint_id is None]
            self.cols_layout.addWidget(self._column(None, backlog, opts, t))
            for sp in sprints:
                lst = [tk for tk in tasks if tk.sprint_id == sp.id]
                self.cols_layout.addWidget(self._column(sp, lst, opts, t))
            self.cols_layout.addStretch()
        finally:
            s.close()

    def _column(self, sp, tasks, opts, t):
        col = QWidget()
        col.setFixedWidth(280)
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        header = QFrame()
        is_backlog = sp is None
        header.setStyleSheet(
            f"QFrame {{ background: {t.bg_badge}; border-radius: 10px; padding: 8px; }}"
        )
        hv = QVBoxLayout(header)
        hv.setContentsMargins(10, 8, 10, 8)
        hv.setSpacing(4)
        title_row = QHBoxLayout()
        name = QLabel(_t("Backlog") if is_backlog else sp.name)
        name.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {t.text_primary}; border: none;")
        title_row.addWidget(name, 1)
        count = QLabel(str(len(tasks)))
        count.setStyleSheet(
            f"background: {t.bg_card}; color: {t.text_muted}; padding: 1px 8px; "
            f"border-radius: 10px; font-size: 11px; border: none;"
        )
        title_row.addWidget(count)
        hv.addLayout(title_row)

        if not is_backlog:
            status_lbl = {"PLANEJADA": _t("Planejada"), "ATIVA": _t("Ativa"), "CONCLUIDA": _t("Concluída")}
            committed = sum(tk.estimate_md or 0 for tk in tasks)
            done = sum(1 for tk in tasks if tk.column and tk.column.is_done)
            over = sp.capacity is not None and committed > sp.capacity
            meta = QLabel(
                _t("{status} · {committed}hd").format(
                    status=status_lbl.get(sp.status, sp.status), committed=f"{committed:.0f}"
                ) + (
                    _t(" / cap {cap}hd").format(cap=f"{sp.capacity:.0f}") + (" ⚠" if over else "")
                    if sp.capacity is not None else ""
                ) + _t(" · {done} concl.").format(done=done)
            )
            meta.setStyleSheet(
                f"color: {t.danger if over else t.text_muted}; font-size: 11px; border: none;"
            )
            meta.setWordWrap(True)
            hv.addWidget(meta)

            actions = QHBoxLayout()
            actions.setSpacing(4)
            if sp.status not in ("ATIVA", "CONCLUIDA"):
                b = QPushButton(_t("Ativar"))
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _=False, sid=sp.id: self._activate(sid))
                actions.addWidget(b)
            if sp.status != "CONCLUIDA":
                b = QPushButton(_t("Concluir"))
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _=False, sid=sp.id: self._complete(sid))
                actions.addWidget(b)
            b = QPushButton(_t("Excluir"))
            b.setStyleSheet(f"QPushButton {{ color: {t.danger}; }}")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, sid=sp.id: self._delete(sid))
            actions.addWidget(b)
            actions.addStretch()
            hv.addLayout(actions)

        v.addWidget(header)

        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cards_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        cards_w = QWidget()
        cards_l = QVBoxLayout(cards_w)
        cards_l.setContentsMargins(2, 2, 2, 2)
        cards_l.setSpacing(6)
        cur = None if is_backlog else sp.id
        for tk in tasks:
            cards_l.addWidget(self._card(tk, cur, opts, t))
        cards_l.addStretch()
        cards_scroll.setWidget(cards_w)
        v.addWidget(cards_scroll, 1)
        return col

    def _card(self, task, cur_sprint_id, opts, t):
        card = QFrame()
        pc = PRIORITY_COLORS.get(task.priority or "MEDIUM", "#4C6EF5")
        card.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-left: 3px solid {pc}; border-radius: 8px; }}"
        )
        v = QVBoxLayout(card)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)
        code = QLabel(task.code)
        code.setStyleSheet(f"font-family: monospace; font-size: 10px; color: {t.text_muted}; border: none;")
        v.addWidget(code)
        title = QLabel(task.title)
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 12px; color: {t.text_primary}; border: none;")
        v.addWidget(title)
        if task.estimate_md:
            est = QLabel(f"{task.estimate_md:.0f} hd")
            est.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
            v.addWidget(est)
        combo = QComboBox()
        combo.addItem(_t("Backlog"), None)
        for sid, sname in opts:
            combo.addItem(sname, sid)
        idx = combo.findData(cur_sprint_id) if cur_sprint_id is not None else 0
        combo.blockSignals(True)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)
        combo.setStyleSheet(
            f"QComboBox {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 4px; padding: 2px 6px; font-size: 11px; color: {t.text_muted}; }}"
        )
        combo.currentIndexChanged.connect(
            lambda _i, c=combo, tid=task.id: self._assign(tid, c.currentData())
        )
        v.addWidget(combo)
        return card

    # ---- Operações ----
    def _assign(self, task_id, sprint_id):
        s = get_session()
        try:
            tk = s.query(Task).get(task_id)
            if tk:
                tk.sprint_id = sprint_id
                s.commit()
        finally:
            s.close()
        self.refresh()
        self.task_changed.emit()

    def _create(self):
        name = self.name_in.text().strip()
        if not name or not self.project_id:
            return
        s = get_session()
        try:
            order = s.query(Sprint).filter(Sprint.project_id == self.project_id).count()
            s.add(Sprint(
                project_id=self.project_id, name=name,
                goal=self.goal_in.text().strip() or None,
                capacity=self.cap_in.value() or None, sort_order=order,
            ))
            s.commit()
        finally:
            s.close()
        self.name_in.clear()
        self.goal_in.clear()
        self.cap_in.setValue(0)
        self.refresh()
        self.task_changed.emit()

    def _activate(self, sprint_id):
        s = get_session()
        try:
            sp = s.query(Sprint).get(sprint_id)
            if sp:
                for other in s.query(Sprint).filter(
                    Sprint.project_id == sp.project_id, Sprint.id != sp.id, Sprint.status == "ATIVA"
                ).all():
                    other.status = "PLANEJADA"
                sp.status = "ATIVA"
                s.commit()
        finally:
            s.close()
        self.refresh()
        self.task_changed.emit()

    def _complete(self, sprint_id):
        s = get_session()
        try:
            sp = s.query(Sprint).get(sprint_id)
            if sp:
                for tk in [x for x in sp.tasks if x.deleted_at is None]:
                    if not (tk.column and tk.column.is_done):
                        tk.sprint_id = None
                sp.status = "CONCLUIDA"
                s.commit()
        finally:
            s.close()
        self.refresh()
        self.task_changed.emit()

    def _delete(self, sprint_id):
        reply = QMessageBox.question(
            self, _t("Confirmar exclusão"),
            _t("Excluir a sprint? As tarefas voltam ao backlog."),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        s = get_session()
        try:
            sp = s.query(Sprint).get(sprint_id)
            if sp:
                for tk in sp.tasks:
                    tk.sprint_id = None
                s.delete(sp)
                s.commit()
        finally:
            s.close()
        self.refresh()
        self.task_changed.emit()


# ────────────────────────────────────────────────────────────
# BoardView
# ────────────────────────────────────────────────────────────

class BoardView(QWidget):
    task_changed = Signal()
    project_opened = Signal(int)

    AUTO_REFRESH_MS = 5000

    def __init__(self):
        super().__init__()
        self.project_id = None
        self._columns: list[ColumnWidget] = []
        self._last_task_hash = None
        self._sprint_filter = None  # None=todas | "__backlog__" | sprint_id(int)
        self._sprints_cache: list[dict] = []
        self._sprint_filter_initialized = False  # já aplicou o default (sprint ativa)?

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(12)

        # -- Empty state (project selection) --
        self.empty_widget = QWidget()
        self.empty_layout = QVBoxLayout(self.empty_widget)
        self.empty_layout.setAlignment(Qt.AlignCenter)
        self.empty_layout.setSpacing(10)

        empty_title = QLabel(_t("Selecione um projeto para ver o board"))
        empty_title.setAlignment(Qt.AlignCenter)
        empty_title.setObjectName("sectionTitle")
        self.empty_layout.addWidget(empty_title)

        self.project_buttons_container = QWidget()
        self.project_buttons_layout = QVBoxLayout(self.project_buttons_container)
        self.project_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.project_buttons_layout.setSpacing(8)
        self.empty_layout.addWidget(self.project_buttons_container, 1)

        self.main_layout.addWidget(self.empty_widget)

        # -- Board view (hidden when no project) --
        self.board_widget = QWidget()
        self.board_layout = QVBoxLayout(self.board_widget)
        self.board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        self.header = QLabel("")
        self.header.setObjectName("sectionTitle")
        header_row.addWidget(self.header)
        header_row.addStretch()

        header_row.addWidget(QLabel(_t("Sprint:")))
        self.sprint_combo = QComboBox()
        self.sprint_combo.setMinimumWidth(150)
        self.sprint_combo.setMaximumWidth(220)
        self.sprint_combo.currentIndexChanged.connect(self._on_sprint_filter_changed)
        header_row.addWidget(self.sprint_combo)

        self.manage_sprints_btn = QPushButton(_t("Sprints"))
        self.manage_sprints_btn.setProperty("flat", True)
        self.manage_sprints_btn.setFixedHeight(28)
        self.manage_sprints_btn.setCursor(Qt.PointingHandCursor)
        self.manage_sprints_btn.clicked.connect(self._open_sprint_manager)
        header_row.addWidget(self.manage_sprints_btn)

        self.archived_btn = QPushButton(_t("Arquivados"))
        self.archived_btn.setProperty("flat", True)
        self.archived_btn.setFixedHeight(28)
        self.archived_btn.setCursor(Qt.PointingHandCursor)
        self.archived_btn.clicked.connect(self._open_archived)
        header_row.addWidget(self.archived_btn)

        self.refresh_btn = QPushButton(_t("Atualizar"))
        self.refresh_btn.setProperty("flat", True)
        self.refresh_btn.setFixedHeight(28)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(self.refresh_btn)

        # --- Aba "Board" (fluxo de trabalho) ---
        self.board_tab = QWidget()
        board_tab_layout = QVBoxLayout(self.board_tab)
        board_tab_layout.setContentsMargins(0, 0, 0, 0)
        board_tab_layout.setSpacing(12)
        board_tab_layout.addLayout(header_row)

        # Filter bar
        self.filter_bar = FilterBar()
        self.filter_bar.filters_changed.connect(self._apply_filters)
        board_tab_layout.addWidget(self.filter_bar)

        # Board scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        board_tab_layout.addWidget(self.scroll, 1)

        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout(self.columns_widget)
        self.columns_layout.setAlignment(Qt.AlignLeft)
        self.columns_layout.setSpacing(10)
        self.scroll.setWidget(self.columns_widget)

        # --- Aba "Planejamento de Sprints" (alocação) ---
        self.planning_view = SprintPlanningView()
        self.planning_view.task_changed.connect(self._on_change)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.board_tab, _t("Board"))
        self.tabs.addTab(self.planning_view, _t("Planejamento de Sprints"))
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.board_layout.addWidget(self.tabs)

        self.main_layout.addWidget(self.board_widget)
        self.board_widget.setVisible(False)

        # Auto-refresh timer
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._auto_refresh)
        self._auto_timer.start(self.AUTO_REFRESH_MS)

        self._load_project_list()

    def set_project(self, project_id):
        self.project_id = project_id
        # Novo projeto: re-aplica o default (sprint ativa) e volta o filtro.
        self._sprint_filter_initialized = False
        self._sprint_filter = None
        if project_id:
            self.empty_widget.setVisible(False)
            self.board_widget.setVisible(True)
        else:
            self.empty_widget.setVisible(True)
            self.board_widget.setVisible(False)
            self._load_project_list()
        # Reseta para a aba Board ao trocar de projeto. O planejamento é
        # construído sob demanda (lazy) só quando a aba é aberta.
        if hasattr(self, "tabs"):
            self.tabs.setCurrentIndex(0)
        self.planning_view.project_id = project_id
        self.refresh()

    def _on_tab_changed(self, idx):
        # Ao abrir a aba de planejamento, recarrega a alocação atual
        if self.tabs.widget(idx) is self.planning_view and self.project_id:
            self.planning_view.set_project(self.project_id)

    def _load_project_list(self):
        while self.project_buttons_layout.count():
            item = self.project_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        t = current_theme()
        s = get_session()
        try:
            projects = s.query(Project).order_by(Project.created_at.desc()).all()
            if not projects:
                empty_lbl = QLabel(_t("Nenhum projeto criado ainda.\nCrie um em Projetos."))
                empty_lbl.setAlignment(Qt.AlignCenter)
                empty_lbl.setStyleSheet(
                    f"color: {t.text_muted}; font-size: 14px; padding: 40px;"
                )
                self.project_buttons_layout.addWidget(empty_lbl)
            for p in projects:
                row = QHBoxLayout()
                row.setSpacing(10)
                name_lbl = QLabel(f"{p.key}  {p.name}")
                name_lbl.setStyleSheet(
                    f"font-size: 14px; font-weight: 600; color: {t.text_primary}; border: none;"
                )
                row.addWidget(name_lbl, 1)

                open_btn = QPushButton(_t("Abrir Board"))
                open_btn.setFixedSize(120, 32)
                open_btn.setCursor(Qt.PointingHandCursor)
                open_btn.setStyleSheet(
                    f"QPushButton {{ background: {t.accent}; color: {t.text_on_accent}; "
                    f"border-radius: 6px; font-size: 12px; font-weight: 600; }}"
                    f"QPushButton:hover {{ background: {t.accent_hover}; }}"
                )
                pid = p.id
                open_btn.clicked.connect(lambda _, _pid=pid: self._open_project(_pid))
                row.addWidget(open_btn)

                btn_widget = QWidget()
                btn_widget.setLayout(row)
                self.project_buttons_layout.addWidget(btn_widget)
        finally:
            s.close()

    def _open_project(self, project_id):
        self.project_opened.emit(project_id)

    # ---- Sprints ----
    def _populate_sprint_combo(self):
        prev = self._sprint_filter
        status_lbl = {
            "PLANEJADA": _t("Planejada"), "ATIVA": _t("Ativa"), "CONCLUIDA": _t("Concluída"),
        }
        self.sprint_combo.blockSignals(True)
        self.sprint_combo.clear()
        self.sprint_combo.addItem(_t("Todas"), None)
        self.sprint_combo.addItem(_t("Backlog"), "__backlog__")
        for sp in self._sprints_cache:
            self.sprint_combo.addItem(
                f"{sp['name']} · {status_lbl.get(sp['status'], sp['status'])}", sp["id"]
            )
        idx = self.sprint_combo.findData(prev)
        self.sprint_combo.setCurrentIndex(idx if idx >= 0 else 0)
        if idx < 0:
            self._sprint_filter = None
        self.sprint_combo.blockSignals(False)

    def _on_sprint_filter_changed(self):
        self._sprint_filter = self.sprint_combo.currentData()
        self.refresh()

    def _open_sprint_manager(self):
        if not self.project_id:
            return
        dlg = SprintManagerDialog(self.project_id, self)
        dlg.exec()
        self.refresh()

    def _auto_archive(self, s):
        """Arquiva tarefas concluídas há mais de 3 dias (backfill do done_at)."""
        from datetime import timedelta
        now = datetime.utcnow()
        cutoff = now - timedelta(days=3)
        done_ids = {
            c.id for c in s.query(BoardColumn).filter(
                BoardColumn.project_id == self.project_id, BoardColumn.is_done == True  # noqa: E712
            ).all()
        }
        if not done_ids:
            return
        tasks = s.query(Task).filter(
            Task.project_id == self.project_id,
            Task.deleted_at == None,  # noqa: E711
            Task.archived_at == None,  # noqa: E711
            Task.column_id.in_(done_ids),
        ).all()
        changed = False
        for t in tasks:
            if t.done_at is None:
                t.done_at = t.updated_at or now
                changed = True
            if t.done_at <= cutoff:
                t.archived_at = now
                changed = True
        if changed:
            s.commit()

    def _open_archived(self):
        if not self.project_id:
            return
        dlg = ArchivedDialog(self.project_id, self)
        dlg.exec()
        self.refresh()

    def refresh(self):
        if not self.project_id:
            return
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._columns.clear()

        s = get_session()
        try:
            project = s.query(Project).get(self.project_id)
            if not project:
                return
            self.header.setText(project.name)

            self._auto_archive(s)

            # Sprints do projeto (para filtro e dropdown nos cards)
            sprints = (
                s.query(Sprint)
                .filter(Sprint.project_id == self.project_id)
                .order_by(Sprint.sort_order, Sprint.id)
                .all()
            )
            self._sprints_cache = [
                {"id": sp.id, "name": sp.name, "status": sp.status} for sp in sprints
            ]
            # Default: ao abrir o projeto, o board mostra a sprint ativa.
            if not self._sprint_filter_initialized:
                self._sprint_filter_initialized = True
                active = next((sp for sp in self._sprints_cache if sp["status"] == "ATIVA"), None)
                if active:
                    self._sprint_filter = active["id"]
            self._populate_sprint_combo()

            columns = (
                s.query(BoardColumn)
                .filter(BoardColumn.project_id == self.project_id)
                .order_by(BoardColumn.order)
                .all()
            )

            for col in columns:
                tasks = (
                    s.query(Task)
                    .filter(
                        Task.column_id == col.id,
                        Task.deleted_at == None,
                        Task.archived_at == None,
                    )
                    .order_by(Task.rank)
                    .all()
                )

                col_data = {
                    "id": col.id,
                    "name": col.name,
                    "wip_limit": col.wip_limit,
                    "is_done": col.is_done,
                    "tasks": [],
                }
                for t in tasks:
                    # Filtro por sprint
                    if self._sprint_filter == "__backlog__" and t.sprint_id is not None:
                        continue
                    if isinstance(self._sprint_filter, int) and t.sprint_id != self._sprint_filter:
                        continue
                    td = {
                        "id": t.id,
                        "code": t.code,
                        "title": t.title,
                        "type": t.type or "FEATURE",
                        "priority": t.priority or "MEDIUM",
                        "labels": [
                            {"id": l.id, "name": l.name, "color": l.color}
                            for l in t.labels
                        ],
                        "checklist": [{"checked": c.checked} for c in t.checklist],
                        "blocked_by": [1 for d in t.blocked_by],
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "assignee": t.assignee,
                        "comments_count": len(t.comments),
                        "requires_human": t.requires_human or False,
                        "can_archive": col.is_done,
                    }
                    col_data["tasks"].append(td)

                cw = ColumnWidget(col_data, self.project_id)
                cw.task_changed.connect(self._on_change)
                self.columns_layout.addWidget(cw)
                self._columns.append(cw)
        finally:
            s.close()

        assignees = set()
        for cw in self._columns:
            for card in cw.get_cards():
                a = card.task_data.get("assignee")
                if a:
                    assignees.add(a)
        self.filter_bar.load_assignees(list(assignees))

        self._last_task_hash = self._compute_hash()
        self._apply_filters()

    def _apply_filters(self):
        search = self.filter_bar.get_search_text()
        type_filter = self.filter_bar.get_type_filter()
        priority_filter = self.filter_bar.get_priority_filter()
        assignee_filter = self.filter_bar.get_assignee_filter()

        total = 0
        visible = 0

        for col_widget in self._columns:
            for card in col_widget.get_cards():
                total += 1
                data = card.task_data
                show = True

                if search:
                    title_match = search in (data.get("title") or "").lower()
                    code_match = search in (data.get("code") or "").lower()
                    if not title_match and not code_match:
                        show = False

                if show and type_filter:
                    if data.get("type") != type_filter:
                        show = False

                if show and priority_filter:
                    if data.get("priority") != priority_filter:
                        show = False

                if show and assignee_filter:
                    task_assignee = data.get("assignee") or ""
                    if assignee_filter == "__none__":
                        if task_assignee:
                            show = False
                    elif task_assignee != assignee_filter:
                        show = False

                card.setVisible(show)
                if show:
                    visible += 1

        self.filter_bar.set_count(visible, total)

    def _compute_hash(self):
        if not self.project_id:
            return None
        s = get_session()
        try:
            rows = (
                s.query(Task.id, Task.column_id, Task.title, Task.updated_at)
                .filter(Task.project_id == self.project_id, Task.deleted_at == None)
                .order_by(Task.id)
                .all()
            )
            return hash(tuple((r.id, r.column_id, r.title, str(r.updated_at)) for r in rows))
        finally:
            s.close()

    def _auto_refresh(self):
        if not self.project_id or not self.isVisible():
            return
        h = self._compute_hash()
        if h != self._last_task_hash:
            self.refresh()

    def _on_change(self):
        self.refresh()
        self.task_changed.emit()
