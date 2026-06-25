import json
import time
from datetime import date, datetime

from PySide6.QtCore import QMimeData, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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
from maestro_local.gui.theme import PRIORITY_COLORS, TYPE_COLORS, TYPE_LABELS, current_theme

MIME_TYPE = "application/x-maestro-task"

PRIORITY_FILTER_MAP = {
    "Todas": None,
    "Baixa": "LOW",
    "Media": "MEDIUM",
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
                border: 1px solid {t.border};
                border-left: 3px solid {left_color};
                border-radius: 6px;
            }}
            TaskCard:hover {{
                border-color: {t.accent};
                border-left: 3px solid {left_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # -- Blocked indicator (prominent) --
        if blocked:
            blocked_bar = QFrame()
            blocked_bar.setFixedHeight(20)
            blocked_bar.setStyleSheet(
                f"background: {t.danger}; border-radius: 3px;"
            )
            blocked_label = QLabel("BLOQUEADA")
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
            cl_lbl = QLabel(f"[ok] {done}/{total}")
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
            human_badge = QLabel("DEV")
            human_badge.setStyleSheet(
                f"background: {t.warning}; color: white; padding: 1px 6px; "
                f"border-radius: 3px; font-size: 9px; font-weight: 700; border: none;"
            )
            human_badge.setToolTip("Requer desenvolvedor")
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
        self.setFixedWidth(290)
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
            f"QFrame {{ background: {done_accent}; border-radius: 8px 8px 0 0; "
            f"padding: 8px 10px; }}"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        name = QLabel(column_data["name"])
        name_color = t.text_on_accent if self.is_done else t.text_primary
        name.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {name_color}; border: none;"
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
            f"QScrollArea {{ border: none; background: {t.bg_secondary}; "
            f"border-radius: 0 0 8px 8px; }}"
        )
        scroll.setAcceptDrops(True)

        cards_widget = QWidget()
        cards_widget.setAcceptDrops(True)
        cards_widget.setStyleSheet(f"background: {t.bg_secondary}; border: none;")
        self.cards_layout = QVBoxLayout(cards_widget)
        self.cards_layout.setContentsMargins(6, 6, 6, 6)
        self.cards_layout.setSpacing(6)

        for task in column_data.get("tasks", []):
            card = TaskCard(task)
            card.clicked.connect(self._open_task)
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
            f"QFrame {{ background: {t.bg_secondary}; border-radius: 0 0 8px 8px; "
            f"padding: 4px 6px; }}"
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
        self.add_input.setPlaceholderText("Nova tarefa...")
        self.add_input.setStyleSheet(
            f"QLineEdit {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px; color: {t.text_primary}; }}"
            f"QLineEdit:focus {{ border-color: {t.accent}; }}"
        )
        self.add_input.returnPressed.connect(self._add_task)
        add_row.addWidget(self.add_input)
        layout.addWidget(add_frame)

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
        t = current_theme()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("\U0001f50d Buscar por titulo ou codigo...")
        self.search_input.setFixedWidth(260)
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 4px; padding: 5px 10px; font-size: 12px; color: {t.text_primary}; }}"
            f"QLineEdit:focus {{ border-color: {t.accent}; }}"
        )
        self.search_input.textChanged.connect(self._emit_changed)
        layout.addWidget(self.search_input)

        # Type filter
        type_label = QLabel("Tipo:")
        type_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px;")
        layout.addWidget(type_label)
        self.type_combo = QComboBox()
        self.type_combo.addItems(list(TYPE_FILTER_MAP.keys()))
        self.type_combo.setFixedWidth(110)
        self.type_combo.setStyleSheet(self._combo_style(t))
        self.type_combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(self.type_combo)

        # Priority filter
        pri_label = QLabel("Prioridade:")
        pri_label.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px;")
        layout.addWidget(pri_label)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(list(PRIORITY_FILTER_MAP.keys()))
        self.priority_combo.setFixedWidth(100)
        self.priority_combo.setStyleSheet(self._combo_style(t))
        self.priority_combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(self.priority_combo)

        layout.addStretch()

        # Task count
        self.count_label = QLabel("0 tarefas")
        self.count_label.setStyleSheet(
            f"color: {t.text_muted}; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(self.count_label)

    @staticmethod
    def _combo_style(t) -> str:
        return (
            f"QComboBox {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px; color: {t.text_primary}; }}"
            f"QComboBox:focus {{ border-color: {t.accent}; }}"
            f"QComboBox::drop-down {{ border: none; }}"
        )

    def _emit_changed(self):
        self.filters_changed.emit()

    def get_search_text(self) -> str:
        return self.search_input.text().strip().lower()

    def get_type_filter(self):
        return TYPE_FILTER_MAP.get(self.type_combo.currentText())

    def get_priority_filter(self):
        return PRIORITY_FILTER_MAP.get(self.priority_combo.currentText())

    def set_count(self, visible: int, total: int):
        if visible == total:
            self.count_label.setText(f"{total} tarefas")
        else:
            self.count_label.setText(f"{visible}/{total} tarefas")


# ────────────────────────────────────────────────────────────
# BoardView
# ────────────────────────────────────────────────────────────

class BoardView(QWidget):
    task_changed = Signal()

    AUTO_REFRESH_MS = 5000

    def __init__(self):
        super().__init__()
        self.project_id = None
        self._columns: list[ColumnWidget] = []
        self._last_task_hash = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(12)

        header_row = QHBoxLayout()
        self.header = QLabel("Selecione um projeto")
        self.header.setObjectName("sectionTitle")
        header_row.addWidget(self.header)
        header_row.addStretch()

        t = current_theme()
        self.refresh_btn = QPushButton("Atualizar")
        self.refresh_btn.setProperty("flat", True)
        self.refresh_btn.setFixedHeight(28)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(self.refresh_btn)

        self.main_layout.addLayout(header_row)

        # Filter bar
        self.filter_bar = FilterBar()
        self.filter_bar.filters_changed.connect(self._apply_filters)
        self.main_layout.addWidget(self.filter_bar)

        # Auto-refresh timer
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._auto_refresh)
        self._auto_timer.start(self.AUTO_REFRESH_MS)

        # Board scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.main_layout.addWidget(self.scroll, 1)

        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout(self.columns_widget)
        self.columns_layout.setAlignment(Qt.AlignLeft)
        self.columns_layout.setSpacing(16)
        self.scroll.setWidget(self.columns_widget)

    def set_project(self, project_id):
        self.project_id = project_id
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
            self.header.setText(f"Board — {project.name}")

            columns = (
                s.query(BoardColumn)
                .filter(BoardColumn.project_id == self.project_id)
                .order_by(BoardColumn.order)
                .all()
            )

            for col in columns:
                tasks = (
                    s.query(Task)
                    .filter(Task.column_id == col.id, Task.deleted_at == None)
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
                    }
                    col_data["tasks"].append(td)

                cw = ColumnWidget(col_data, self.project_id)
                cw.task_changed.connect(self._on_change)
                self.columns_layout.addWidget(cw)
                self._columns.append(cw)
        finally:
            s.close()

        self._last_task_hash = self._compute_hash()
        self._apply_filters()

    def _apply_filters(self):
        search = self.filter_bar.get_search_text()
        type_filter = self.filter_bar.get_type_filter()
        priority_filter = self.filter_bar.get_priority_filter()

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
