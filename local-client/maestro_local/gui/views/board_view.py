import json
import time
from datetime import date, datetime

from PySide6.QtCore import QDate, QMimeData, QPoint, QPropertyAnimation, QRect, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
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
    QProgressBar,
    QPushButton,
    QSpinBox,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import (
    ActivityLog,
    BoardColumn,
    Comment,
    Epic,
    Goal,
    Label,
    Member,
    Project,
    ProjectDailyEntry,
    Sprint,
    Task,
    get_or_create_member,
    get_session,
    member_stats,
    project_members,
)
from maestro_local.gui.theme import (
    PRIORITY_COLORS,
    TYPE_COLORS,
    TYPE_LABELS,
    color_for_column,
    current_theme,
)
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

        # Borda esquerda pela cor do TIPO (a prioridade vira um ponto no topo).
        tipo = task_data.get("type", "FEATURE")
        left_color = TYPE_COLORS.get(tipo, "#868E96")
        priority = task_data.get("priority", "MEDIUM")
        pc = PRIORITY_COLORS.get(priority, "#4C6EF5")

        self.setStyleSheet(f"""
            TaskCard {{
                background-color: {t.bg_card};
                border: 1px solid {t.border};
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

        # -- Top row: code + assignee --
        top = QHBoxLayout()
        top.setSpacing(6)
        code = QLabel(task_data.get("code", ""))
        code.setStyleSheet(
            f"font-family: monospace; font-size: 11px; color: {t.text_muted}; border: none;"
        )
        top.addWidget(code)
        if task_data.get("is_local"):
            local_chip = QLabel(_t("LOCAL"))
            local_chip.setToolTip(_t("Tarefa local: não sincroniza com o board externo"))
            local_chip.setStyleSheet(
                "border: 1px dashed #94A3B8; color: #64748B; border-radius: 4px;"
                " padding: 0 4px; font-size: 9px; font-weight: 700;"
            )
            top.addWidget(local_chip)
        # prioridade como ponto colorido (a cor da borda agora é o tipo)
        prio_dot = QLabel("●")
        prio_dot.setStyleSheet(f"color: {pc}; font-size: 11px; border: none;")
        prio_dot.setToolTip(f"{_t('Prioridade')}: {priority}")
        top.addWidget(prio_dot)
        top.addStretch()

        assignee = task_data.get("assignee")
        if assignee:
            nome = QLabel(assignee)
            nome.setStyleSheet(
                f"color: {t.text_secondary}; font-size: 11px; font-weight: 600; border: none;"
            )
            top.addWidget(nome)
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
            avatar.setToolTip(assignee)
            top.addWidget(avatar)
        layout.addLayout(top)

        # -- Title --
        title = QLabel(task_data.get("title", ""))
        title.setWordWrap(True)
        title.setStyleSheet(
            f"font-size: 13px; color: {t.text_primary}; border: none; padding: 2px 0;"
        )
        layout.addWidget(title)

        # -- Epics --
        epics = task_data.get("epics", [])
        if epics:
            ep_row = QHBoxLayout()
            ep_row.setSpacing(4)
            for ep in epics[:2]:
                chip = QLabel(ep["name"])
                cor = ep.get("color", "#6741D9")
                chip.setStyleSheet(
                    f"background: transparent; color: {cor}; border: 1px solid {cor}; "
                    f"padding: 1px 6px; border-radius: 8px; font-size: 10px; font-weight: 600;"
                )
                ep_row.addWidget(chip)
            ep_row.addStretch()
            layout.addLayout(ep_row)

        # -- Tipo (cor igual à borda do card) --
        tipo_row = QHBoxLayout()
        tipo_row.setSpacing(4)
        tipo_chip = QLabel(TYPE_LABELS.get(tipo, tipo))
        tipo_chip.setStyleSheet(
            f"background: {left_color}; color: white; padding: 1px 6px;"
            f" border-radius: 8px; font-size: 10px; font-weight: 700; border: none;"
        )
        tipo_row.addWidget(tipo_chip)
        tipo_row.addStretch()
        layout.addLayout(tipo_row)

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

        # -- Bottom row: due_date + linked + comments --
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

        # Linked cards
        linked = task_data.get("linked_count", 0)
        if linked:
            lnk = QLabel(f"🔗 {linked}")
            lnk.setToolTip(_t("{n} card(s) vinculado(s)").format(n=linked))
            lnk.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
            bottom.addWidget(lnk)
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

    def __init__(self, column_data: dict, project_id: int, local_flag=None):
        super().__init__()
        self.column_id = column_data["id"]
        # callable que diz se o próximo card deve ser criado como local
        self._local_flag = local_flag
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
        cor_baia = color_for_column(column_data.get("order", 0), column_data.get("id"))
        header_frame.setStyleSheet(
            f"QFrame {{ background: {done_accent}; border-radius: 10px 10px 0 0; "
            f"border-top: 3px solid {cor_baia}; padding: 10px 12px; }}"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)

        name = QLabel(column_data["name"])
        name_color = t.text_on_accent if self.is_done else t.text_primary
        name.setStyleSheet(
            f"font-weight: 700; font-size: 13px; color: {name_color}; border: none; "
            f"letter-spacing: 0.3px; border-left: 8px solid {cor_baia}; padding-left: 6px;"
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
            criar_local = bool(self._local_flag and self._local_flag())
            task = Task(
                project_id=self.project_id,
                column_id=self.column_id,
                number=project.task_seq,
                title=title,
                type="CHORE" if criar_local else "FEATURE",
                is_local=criar_local,
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
        type_label.setVisible(False)
        layout.addWidget(type_label)
        self.type_combo = QComboBox()
        for _key in TYPE_FILTER_MAP.keys():
            self.type_combo.addItem(_t(_key), _key)
        self.type_combo.setMinimumWidth(96)
        self.type_combo.setVisible(False)
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

        # Epic filter
        epic_label = QLabel(_t("Épico:"))
        epic_label.setProperty("class", "sectionLabel")
        layout.addWidget(epic_label)
        self.epic_combo = QComboBox()
        self.epic_combo.addItem(_t("Todos"), None)
        self.epic_combo.setMinimumWidth(110)
        self.epic_combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(self.epic_combo)

        # Tag filter
        tag_label = QLabel(_t("Tag:"))
        tag_label.setProperty("class", "sectionLabel")
        layout.addWidget(tag_label)
        self.tag_combo = QComboBox()
        self.tag_combo.addItem(_t("Todas"), None)
        self.tag_combo.setMinimumWidth(110)
        self.tag_combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(self.tag_combo)

        # Origem: do board externo x tarefa local
        origin_label = QLabel(_t("Origem:"))
        origin_label.setProperty("class", "sectionLabel")
        layout.addWidget(origin_label)
        self.origin_combo = QComboBox()
        self.origin_combo.addItem(_t("Todas"), "all")
        self.origin_combo.addItem(_t("Do board"), "remote")
        self.origin_combo.addItem(_t("Locais"), "local")
        self.origin_combo.setMinimumWidth(100)
        self.origin_combo.setToolTip(_t("Tarefas locais não sincronizam com o board externo"))
        self.origin_combo.currentIndexChanged.connect(self._emit_changed)
        layout.addWidget(self.origin_combo)

        # Criar como local (vale para os campos "Nova tarefa..." das colunas)
        self.local_new = QCheckBox(_t("Criar como local"))
        self.local_new.setToolTip(
            _t("Novos cards criados abaixo vão existir só aqui e o sync não os toca")
        )
        layout.addWidget(self.local_new)

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
        return None

    def get_origin_filter(self) -> str:
        return self.origin_combo.currentData() or "all"

    def criar_local(self) -> bool:
        return bool(self.local_new.isChecked())

    def get_epic_filter(self):
        data = self.epic_combo.currentData()
        return data if data is not None else None

    def get_tag_filter(self):
        data = self.tag_combo.currentData()
        return data if data is not None else None

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

    def load_epics_tags(self, epics: list[dict], tags: list[str]):
        for combo, atual, todos, itens in (
            (self.epic_combo, self.epic_combo.currentData(), _t("Todos"),
             [(e["name"], e["id"]) for e in epics]),
            (self.tag_combo, self.tag_combo.currentData(), _t("Todas"),
             [(n, n) for n in tags]),
        ):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(todos, None)
            for nome, valor in itens:
                combo.addItem(nome, valor)
            idx = combo.findData(atual)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

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
        retro = QPushButton(_t("Retrospectiva"))
        retro.setCursor(Qt.PointingHandCursor)
        retro.clicked.connect(lambda _=False, sid=sp.id: self._retro(sid))
        btns.addWidget(retro)
        dele = QPushButton(_t("Excluir"))
        dele.setCursor(Qt.PointingHandCursor)
        dele.setStyleSheet(f"QPushButton {{ color: {t.danger}; }}")
        dele.clicked.connect(lambda _=False, sid=sp.id: self._delete(sid))
        btns.addWidget(dele)
        v.addLayout(btns)
        return row

    def _retro(self, sprint_id):
        import json as _json

        from maestro_local.api.app import _sprint_retro_context
        from maestro_local.triage import generate_sprint_retro
        s = get_session()
        try:
            sp = s.query(Sprint).get(sprint_id)
            if not sp:
                return
            retro = None
            if sp.retro_json:
                try:
                    retro = _json.loads(sp.retro_json)
                except ValueError:
                    retro = None
            if retro is None:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    retro = generate_sprint_retro(_sprint_retro_context(sp))
                except Exception as e:  # noqa: BLE001
                    QApplication.restoreOverrideCursor()
                    QMessageBox.warning(self, _t("Retrospectiva"), _t("Erro na retrospectiva") + f": {e}")
                    return
                finally:
                    QApplication.restoreOverrideCursor()
                sp.retro_json = _json.dumps(retro, ensure_ascii=False)
                s.commit()
            project_id = sp.project_id
            sprint_name = sp.name
        finally:
            s.close()

        parts = []
        if retro.get("well"):
            parts.append("👍 " + _t("O que foi bem") + "\n" + "\n".join(f"• {x}" for x in retro["well"]))
        if retro.get("badly"):
            parts.append("👎 " + _t("O que pode melhorar") + "\n" + "\n".join(f"• {x}" for x in retro["badly"]))
        if retro.get("actions"):
            parts.append("✅ " + _t("Ações") + "\n" + "\n".join(f"• {a['title']}" for a in retro["actions"]))
        box = QMessageBox(self)
        box.setWindowTitle(_t("Retrospectiva") + f" — {sprint_name}")
        box.setText("\n\n".join(parts) or _t("Sem conteúdo."))
        if retro.get("actions"):
            create_btn = box.addButton(_t("Criar tarefas das ações"), QMessageBox.AcceptRole)
        else:
            create_btn = None
        box.addButton(_t("Fechar"), QMessageBox.RejectRole)
        box.exec()
        if create_btn and box.clickedButton() is create_btn:
            self._create_retro_tasks(project_id, sprint_name, [a["title"] for a in retro["actions"]])

    def _create_retro_tasks(self, project_id, sprint_name, titles):
        s = get_session()
        try:
            project = s.query(Project).get(project_id)
            column = (s.query(BoardColumn)
                      .filter(BoardColumn.project_id == project_id)
                      .order_by(BoardColumn.order.asc()).first())
            created = 0
            for title in titles:
                title = str(title).strip()
                if not title:
                    continue
                project.task_seq = (project.task_seq or 0) + 1
                s.add(Task(
                    project_id=project_id,
                    column_id=column.id if column else None,
                    number=project.task_seq,
                    title=f"[Retro] {title}"[:255],
                    description=f"Ação de melhoria da retrospectiva da sprint '{sprint_name}'",
                    type="CHORE",
                    requires_human=True,
                ))
                created += 1
            s.commit()
        finally:
            s.close()
        QMessageBox.information(self, _t("Retrospectiva"), _t("Tarefas criadas") + f": {created}")
        self._load()

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
# MembersDialog
# ────────────────────────────────────────────────────────────

class MembersDialog(QDialog):
    """Lista de responsáveis do projeto: adicionar, remover e métricas.

    Os nomes daqui alimentam a atribuição dos cards, o filtro do board e as
    métricas por responsável (total, concluídos, % e vencidos em aberto).
    """

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setWindowTitle(_t("Responsáveis do projeto"))
        self.resize(520, 480)
        root = QVBoxLayout(self)
        root.setSpacing(8)

        hint = QLabel(_t(
            "Quem aparece aqui pode ser atribuído aos cards e filtrado no board."))
        hint.setWordWrap(True)
        hint.setProperty("class", "hint")
        root.addWidget(hint)

        form = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(_t("Nome do responsável..."))
        self.name_input.returnPressed.connect(self._add)
        form.addWidget(self.name_input, 1)
        add_btn = QPushButton(_t("Adicionar"))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add)
        form.addWidget(add_btn)
        root.addLayout(form)

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

    def _add(self):
        nome = self.name_input.text().strip()
        if not nome:
            return
        s = get_session()
        try:
            get_or_create_member(s, self.project_id, nome)
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()
        self.name_input.clear()
        self._load()

    def _remove(self, member_id):
        s = get_session()
        try:
            m = s.get(Member, member_id)
            if m:
                s.delete(m)   # os cards mantêm o nome em Task.assignee
                s.commit()
        finally:
            s.close()
        self._load()

    def _load(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        t = current_theme()
        s = get_session()
        try:
            dados = member_stats(s, self.project_id)
            if not dados:
                empty = QLabel(_t("Nenhum responsável ainda. Adicione acima."))
                empty.setStyleSheet(f"color: {t.text_muted}; padding: 16px;")
                empty.setAlignment(Qt.AlignCenter)
                self.list_layout.addWidget(empty)
            for st in dados:
                self.list_layout.addWidget(self._row(st, t))
            self.list_layout.addStretch()
        finally:
            s.close()

    def _row(self, st, t):
        m = st["member"]
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 8px; }}"
        )
        v = QVBoxLayout(row)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)

        top = QHBoxLayout()
        cor = m.color or t.accent
        dot = QLabel()
        dot.setFixedSize(16, 16)
        dot.setStyleSheet(f"background: {cor}; border-radius: 8px; border: none;")
        top.addWidget(dot)
        nome = QLabel(m.name)
        nome.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {t.text_primary}; border: none;")
        top.addWidget(nome, 1)
        rm = QPushButton(_t("Excluir"))
        rm.setCursor(Qt.PointingHandCursor)
        rm.setStyleSheet(f"QPushButton {{ color: {t.danger}; }}")
        mid = m.id
        rm.clicked.connect(lambda _=False, x=mid: self._remove(x))
        top.addWidget(rm)
        v.addLayout(top)

        barra = QProgressBar()
        barra.setValue(st["pct"])
        barra.setTextVisible(True)
        barra.setFormat(f"{st['pct']}%  ({st['done']}/{st['total']})")
        barra.setFixedHeight(16)
        v.addWidget(barra)

        detalhe = QLabel(
            _t("{total} tarefa(s) · {done} concluída(s)").format(
                total=st["total"], done=st["done"]))
        if st["overdue"]:
            detalhe.setText(detalhe.text() + "  ·  " + _t("{n} vencida(s)").format(n=st["overdue"]))
            detalhe.setStyleSheet(f"color: {t.danger}; font-size: 11px; border: none;")
        else:
            detalhe.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        v.addWidget(detalhe)
        return row


# ────────────────────────────────────────────────────────────
# ColumnManagerDialog — customiza colunas como Jira/Azure DevOps
# ────────────────────────────────────────────────────────────

TEMPLATE_12_RAIAS = [
    ("To do", False), ("Approved", False), ("Refinement", False), ("Ready for Dev", False),
    ("Doing", False), ("Dev Box", False), ("Dev Review", False), ("In Test", False),
    ("Rework", False), ("Verified", False), ("Accepted", False), ("Done", True),
]


class ColumnManagerDialog(QDialog):
    """Edita colunas do board: nome, ordem, WIP e coluna de conclusão."""

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.changed = False
        self.setWindowTitle(_t("Colunas do quadro"))
        self.resize(640, 520)
        root = QVBoxLayout(self)
        root.setSpacing(8)
        hint = QLabel(_t("Arraste a ordem com ↑/↓. A coluna marcada como Concluído conta como Done. WIP limita o aviso no cabeçalho."))
        hint.setWordWrap(True)
        hint.setProperty("class", "hint")
        root.addWidget(hint)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)
        btns = QHBoxLayout()
        add_btn = QPushButton(_t("+ Coluna"))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_row)
        btns.addWidget(add_btn)
        tmpl_btn = QPushButton(_t("Aplicar modelo 12 raias"))
        tmpl_btn.setProperty("flat", True)
        tmpl_btn.setCursor(Qt.PointingHandCursor)
        tmpl_btn.setToolTip(_t("Substitui as colunas pelo modelo de 12 raias (To do → Done)"))
        tmpl_btn.clicked.connect(self._apply_template)
        btns.addWidget(tmpl_btn)
        btns.addStretch()
        save_btn = QPushButton(_t("Salvar"))
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        cancel_btn = QPushButton(_t("Cancelar"))
        cancel_btn.setProperty("flat", True)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        root.addLayout(btns)
        self._rows: list[dict] = []
        self._load()

    def _load(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()
        s = get_session()
        try:
            cols = s.query(BoardColumn).filter(BoardColumn.project_id == self.project_id).order_by(BoardColumn.order).all()
            if not cols:
                for i, c in enumerate(DEFAULT_COLUMNS):
                    cols = [BoardColumn(project_id=self.project_id, name=c["name"], order=c["order"], is_done=c.get("is_done", False))]
            for col in cols:
                self._add_row_widget(col.name, col.wip_limit, col.is_done, col.id)
        finally:
            s.close()
        if not self._rows:
            self._add_row_widget("A fazer", None, False, None)
        self.list_layout.addStretch()

    def _add_row_widget(self, name, wip, is_done, col_id):
        row = QFrame()
        row.setStyleSheet(f"QFrame {{ background: {current_theme().bg_card}; border: 1px solid {current_theme().border_light}; border-radius: 8px; }}")
        h = QHBoxLayout(row)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(6)
        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText(_t("Nome da coluna"))
        h.addWidget(name_edit, 1)
        wip_spin = QSpinBox()
        wip_spin.setRange(0, 999)
        wip_spin.setSpecialValueText("∞")
        wip_spin.setValue(int(wip) if wip else 0)
        wip_spin.setFixedWidth(60)
        wip_spin.setToolTip("WIP limit (0 = sem limite)")
        h.addWidget(QLabel("WIP"))
        h.addWidget(wip_spin)
        done_chk = QCheckBox(_t("Concluído"))
        done_chk.setChecked(bool(is_done))
        h.addWidget(done_chk)
        up_btn = QPushButton("↑")
        up_btn.setFixedSize(28, 28)
        up_btn.setCursor(Qt.PointingHandCursor)
        up_btn.clicked.connect(lambda _=False, r=row: self._move(r, -1))
        h.addWidget(up_btn)
        down_btn = QPushButton("↓")
        down_btn.setFixedSize(28, 28)
        down_btn.setCursor(Qt.PointingHandCursor)
        down_btn.clicked.connect(lambda _=False, r=row: self._move(r, 1))
        h.addWidget(down_btn)
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(f"color: {current_theme().danger}; background: transparent; border: none;")
        del_btn.clicked.connect(lambda _=False, r=row: self._remove_row(r))
        h.addWidget(del_btn)
        self.list_layout.insertWidget(len(self._rows), row)
        self._rows.append({"widget": row, "name": name_edit, "wip": wip_spin, "done": done_chk, "id": col_id})

    def _add_row(self):
        self._add_row_widget("", None, False, None)

    def _remove_row(self, widget):
        for i, r in enumerate(self._rows):
            if r["widget"] is widget:
                # impede remover se for a última ou se tem cards
                if len(self._rows) <= 1:
                    QMessageBox.warning(self, _t("Colunas"), _t("O quadro precisa de ao menos uma coluna."))
                    return
                s = get_session()
                try:
                    if r["id"] is not None:
                        cnt = s.query(Task).filter(Task.column_id == r["id"], Task.deleted_at == None).count()  # noqa: E711
                        if cnt > 0:
                            QMessageBox.warning(self, _t("Colunas"), _t("Coluna com cards não pode ser removida. Mova os cards antes."))
                            return
                finally:
                    s.close()
                self.list_layout.removeWidget(widget)
                widget.deleteLater()
                self._rows.pop(i)
                break

    def _move(self, widget, delta):
        idx = next((i for i, r in enumerate(self._rows) if r["widget"] is widget), None)
        if idx is None:
            return
        nidx = idx + delta
        if 0 <= nidx < len(self._rows):
            self._rows[idx], self._rows[nidx] = self._rows[nidx], self._rows[idx]
            # rebuild visual order
            for r in self._rows:
                self.list_layout.removeWidget(r["widget"])
            for r in self._rows:
                self.list_layout.insertWidget(self._rows.index(r), r["widget"])

    def _apply_template(self):
        if self._rows and QMessageBox.question(self, _t("Aplicar modelo"), _t("Substituir as colunas atuais pelo modelo de 12 raias?"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        s = get_session()
        try:
            has_cards = s.query(Task).filter(Task.project_id == self.project_id, Task.deleted_at == None).count() > 0  # noqa: E711
            if has_cards:
                QMessageBox.warning(self, _t("Colunas"), _t("Remova/mova os cards antes de aplicar um modelo com colunas diferentes."))
                return
        finally:
            s.close()
        while self._rows:
            r = self._rows.pop()
            self.list_layout.removeWidget(r["widget"])
            r["widget"].deleteLater()
        for name, is_done in TEMPLATE_12_RAIAS:
            self._add_row_widget(name, None, is_done, None)
        # keep stretch at end
        self.list_layout.addStretch()

    def _save(self):
        names = [r["name"].text().strip() for r in self._rows]
        if any(not n for n in names):
            QMessageBox.warning(self, _t("Colunas"), _t("Toda coluna precisa de um nome."))
            return
        if len(set(n.lower() for n in names)) != len(names):
            QMessageBox.warning(self, _t("Colunas"), _t("Há colunas com nome duplicado."))
            return
        done_count = sum(1 for r in self._rows if r["done"].isChecked())
        if done_count != 1:
            QMessageBox.warning(self, _t("Colunas"), _t("Marque exatamente uma coluna como Concluído."))
            return
        s = get_session()
        try:
            existing = {c.id: c for c in s.query(BoardColumn).filter(BoardColumn.project_id == self.project_id).all()}
            # delete removed
            keep_ids = {r["id"] for r in self._rows if r["id"] is not None}
            for cid, col in list(existing.items()):
                if cid not in keep_ids:
                    s.delete(col)
            # upsert in order
            for order, r in enumerate(self._rows):
                cid = r["id"]
                if cid is not None and cid in existing:
                    col = existing[cid]
                else:
                    col = BoardColumn(project_id=self.project_id)
                    s.add(col)
                col.name = r["name"].text().strip()[:120]
                col.order = order
                col.wip_limit = r["wip"].value() or None
                col.is_done = r["done"].isChecked()
            s.commit()
            self.changed = True
            self.accept()
        except Exception as e:  # noqa: BLE001
            s.rollback()
            QMessageBox.warning(self, _t("Erro"), str(e))
        finally:
            s.close()


# ────────────────────────────────────────────────────────────
# BoardMetricsAccordion — acordeão de métricas do projeto
# ────────────────────────────────────────────────────────────

def _goal_progress(goal, s) -> tuple[int, int]:
    q = s.query(Task).filter(
        Task.project_id == goal.project_id,
        Task.deleted_at == None,  # noqa: E711
        Task.archived_at == None,  # noqa: E711
    )
    if goal.tag:
        q = q.filter(Task.labels.any(Label.name == goal.tag))
    if goal.epic_id:
        q = q.filter(Task.epics.any(Epic.id == goal.epic_id))
    if goal.sprint_id:
        q = q.filter(Task.sprint_id == goal.sprint_id)
    total = q.count()
    done = q.join(BoardColumn, Task.column_id == BoardColumn.id).filter(
        BoardColumn.is_done == True).count()  # noqa: E712
    return done, total


class PieChartWidget(QFrame):
    """Pizza simples em QPainter — sem dependência externa."""

    def __init__(self, data: list[tuple[str, int, str]], size=90, parent=None):
        super().__init__(parent)
        self._data = [(label, value, color) for label, value, color in data if value > 0]
        self._size = size
        self.setFixedSize(size, size)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        if not self._data:
            return
        total = sum(v for _, v, _ in self._data)
        if total == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        start = -90 * 16
        for _, value, color in self._data:
            span = int(360 * 16 * value / total)
            painter.setBrush(QColor(color))
            painter.setPen(QColor(current_theme().bg_card))
            painter.drawPie(rect, start, span)
            start += span
        # furo central para virar donut
        painter.setBrush(QColor(current_theme().bg_card))
        painter.setPen(QColor(current_theme().bg_card))
        r = rect.width() * 0.28
        cx, cy = rect.center().x(), rect.center().y()
        painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        # total no centro
        painter.setPen(QColor(current_theme().text_primary))
        f = painter.font()
        f.setPointSize(8)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(rect, Qt.AlignCenter, str(total))


class BoardMetricsAccordion(QFrame):
    """Acordeão no topo do kanban: alertas, prazos e objetivos do projeto."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        self._expanded = True
        t = current_theme()
        self.setStyleSheet(
            f"BoardMetricsAccordion {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 10px; }}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # — header clicável —
        header_wrap = QFrame()
        header_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
        hlay = QHBoxLayout(header_wrap)
        hlay.setContentsMargins(10, 8, 10, 8)
        hlay.setSpacing(8)
        self.chevron_btn = QPushButton("▾")
        self.chevron_btn.setFixedSize(24, 24)
        self.chevron_btn.setCursor(Qt.PointingHandCursor)
        self.chevron_btn.setFlat(True)
        self.chevron_btn.setStyleSheet(
            f"QPushButton {{ background: {t.bg_badge}; border: 1px solid {t.border_light}; border-radius: 6px; color: {t.text_muted}; font-size: 11px; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; color: {t.text_primary}; }}"
        )
        self.chevron_btn.clicked.connect(self._toggle)
        hlay.addWidget(self.chevron_btn)
        self.title_lbl = QLabel(_t("Métricas do projeto"))
        self.title_lbl.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {t.text_primary}; border: none;")
        hlay.addWidget(self.title_lbl)
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        hlay.addWidget(self.summary_lbl)
        hlay.addStretch()
        root.addWidget(header_wrap)
        self.header = header_wrap
        self.chevron = self.chevron_btn

        # — conteúdo —
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(14, 6, 14, 14)
        self.content_layout.setSpacing(12)
        root.addWidget(self.content)
        self._build_empty()

    def _build_empty(self):
        t = current_theme()
        lbl = QLabel(_t("Selecione um projeto para ver as métricas."))
        lbl.setProperty("class", "hint")
        lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; border: none;")
        self.content_layout.addWidget(lbl)

    def _toggle(self):
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        self.chevron.setText("▾" if self._expanded else "▸")

    def set_project(self, project_id):
        self.project_id = project_id
        self.refresh()

    def refresh(self):
        # limpa (detach imediato para não sobrepor até o deleteLater)
        def _clear_layout(lay):
            while lay.count():
                it = lay.takeAt(0)
                ww = it.widget()
                if ww is not None:
                    ww.hide()
                    ww.setParent(None)
                    ww.deleteLater()
                elif it.layout() is not None:
                    _clear_layout(it.layout())
        _clear_layout(self.content_layout)
        t = current_theme()
        if not self.project_id:
            self.summary_lbl.setText("")
            self._build_empty()
            return

        s = get_session()
        try:
            project = s.get(Project, self.project_id)
            if not project:
                self.summary_lbl.setText("")
                return

            # — coleta de dados —
            cols = s.query(BoardColumn).filter(BoardColumn.project_id == self.project_id).order_by(BoardColumn.order).all()
            done_col_ids = {c.id for c in cols if c.is_done}
            tasks_all = s.query(Task).filter(
                Task.project_id == self.project_id,
                Task.deleted_at == None,  # noqa: E711
                Task.archived_at == None,  # noqa: E711
            ).all()
            total = len(tasks_all)
            done = sum(1 for tk in tasks_all if tk.column_id in done_col_ids)
            pct = int(done / total * 100) if total else 0

            # WIP
            wip_alerts = []
            for col in cols:
                if col.wip_limit and col.wip_limit > 0:
                    cnt = sum(1 for tk in tasks_all if tk.column_id == col.id)
                    if cnt > col.wip_limit:
                        wip_alerts.append(f"{col.name}: {cnt}/{col.wip_limit}")

            # vencidos
            hoje = date.today()
            vencidos = [tk for tk in tasks_all if tk.due_date and tk.due_date.date() < hoje and tk.column_id not in done_col_ids]
            # parados (sem atualização há 14d, não concluídos)
            from datetime import timedelta
            limite_parado = datetime.utcnow() - timedelta(days=14)
            parados = [tk for tk in tasks_all if tk.column_id not in done_col_ids and tk.updated_at and tk.updated_at < limite_parado]

            # sprint ativa
            sprint_ativa = s.query(Sprint).filter(Sprint.project_id == self.project_id, Sprint.status == "ATIVA").first()
            goals = s.query(Goal).filter(Goal.project_id == self.project_id).order_by(Goal.due_date.is_(None), Goal.due_date).all()

            # — resumo no header —
            partes = []
            if pct < 100:
                partes.append(f"{pct}%")
            if wip_alerts:
                partes.append(f"⚠ WIP {len(wip_alerts)}")
            if vencidos:
                partes.append(f"⏰ {len(vencidos)} vencida(s)")
            if parados:
                partes.append(f"• {len(parados)} parada(s)")
            # goals atrasados
            goals_atrasados = 0
            for g in goals:
                if g.due_date and g.due_date.date() < hoje:
                    d, tot = _goal_progress(g, s)
                    if d < tot:
                        goals_atrasados += 1
            if goals_atrasados:
                partes.append(f"🎯 {goals_atrasados} objetivo(s) atrasado(s)")
            self.summary_lbl.setText("  ·  ".join(partes) if partes else _t("Tudo em dia"))

            # — linha de progresso geral —
            prog_row = QHBoxLayout()
            prog_row.setSpacing(8)
            prog_lbl = QLabel(_t("Progresso geral"))
            prog_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; font-weight: 600; border: none;")
            prog_row.addWidget(prog_lbl)
            barra = QProgressBar()
            barra.setValue(pct)
            barra.setFormat(f"{pct}%  ({done}/{total})")
            barra.setTextVisible(True)
            barra.setFixedHeight(16)
            barra.setStyleSheet(f"QProgressBar {{ background: {t.bg_badge}; }} QProgressBar::chunk {{ background: {t.success if pct==100 else t.accent}; }}")
            prog_row.addWidget(barra, 1)
            if sprint_ativa and sprint_ativa.end_date:
                dias = (sprint_ativa.end_date.date() - hoje).days
                cor = t.danger if dias < 0 else (t.warning if dias <= 3 else t.text_muted)
                sprint_lbl = QLabel(_t("Sprint {name}: {d} dias").format(name=sprint_ativa.name, d=dias) if dias >= 0 else _t("Sprint {name}: atrasada {d}d").format(name=sprint_ativa.name, d=abs(dias)))
                sprint_lbl.setStyleSheet(f"color: {cor}; font-size: 11px; font-weight: 600; border: none;")
                prog_row.addWidget(sprint_lbl)
            w_prog = QWidget()
            w_prog.setLayout(prog_row)
            self.content_layout.addWidget(w_prog)

            # — Chegaram em cada estágio (cumulativo) + corte por módulo —
            from maestro_local.stages import compute_stages

            historico_mov = (
                s.query(ActivityLog.entity_id, ActivityLog.detail)
                .filter(ActivityLog.entity_type == "task", ActivityLog.action == "moved")
                .all()
            )
            estagios = compute_stages(tasks_all, cols, historico_mov)
            if estagios["stages"]:
                est_box = self._section_box("📈 " + _t("Chegaram em cada estágio"), t)
                nota = QLabel(_t("Chegou = está no estágio ou já passou por ele (ordem das colunas + movimentações)."))
                nota.setWordWrap(True)
                nota.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                est_box["layout"].addWidget(nota)

                combo = QComboBox()
                for x in estagios["stages"]:
                    combo.addItem(f"{x['name']} · {x['reached']} " + _t("chegaram"), x["stage"])
                por_estagio = {x["stage"]: x for x in estagios["stages"]}
                padrao = "dev-box" if "dev-box" in por_estagio else estagios["stages"][0]["stage"]
                combo.setCurrentIndex([x["stage"] for x in estagios["stages"]].index(padrao))

                max_alcancado = max(x["reached"] for x in estagios["stages"]) or 1
                funil = QVBoxLayout(); funil.setSpacing(2)
                for x in estagios["stages"]:
                    linha = QHBoxLayout(); linha.setSpacing(6)
                    nome = QLabel(x["name"])
                    nome.setStyleSheet(f"color: {t.text_primary}; font-size: 11px; border: none;")
                    nome.setFixedWidth(120)
                    linha.addWidget(nome)
                    barra_alc = QProgressBar()
                    barra_alc.setValue(int(x["reached"] / max_alcancado * 100))
                    barra_alc.setFormat(f"{x['reached']} ({x['pct']}%)")
                    barra_alc.setFixedHeight(12)
                    linha.addWidget(barra_alc, 1)
                    agora = QLabel(f"{_t('agora')}: {x['current']}")
                    agora.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                    agora.setFixedWidth(80)
                    linha.addWidget(agora)
                    w_linha = QWidget(); w_linha.setLayout(linha)
                    funil.addWidget(w_linha)
                est_box["layout"].addLayout(funil)

                split_titulo = QLabel()
                split_titulo.setStyleSheet(f"color: {t.text_primary}; font-size: 11px; font-weight: 600; border: none;")
                est_box["layout"].addWidget(split_titulo)
                split_box = QVBoxLayout(); split_box.setSpacing(3)
                est_box["layout"].addLayout(split_box)

                def _preencher_split(chave_estagio):
                    while split_box.count():
                        item = split_box.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    est = por_estagio.get(chave_estagio)
                    if not est:
                        return
                    split_titulo.setText(
                        f"{est['name']} · {_t('corte por módulo')} ({est['reached']} {_t('cards')})"
                    )
                    grupos = estagios["breakdown"].get(chave_estagio, [])
                    if not grupos:
                        split_box.addWidget(self._hint(_t("Nenhum card chegou neste estágio."), t))
                        return
                    for g in grupos:
                        r = QHBoxLayout(); r.setSpacing(6)
                        lb = QLabel(_t("Sem módulo") if g["group"] == "sem-modulo" else g["label"])
                        lb.setStyleSheet(f"color: {t.text_primary}; font-size: 11px; border: none;")
                        lb.setFixedWidth(120)
                        r.addWidget(lb)
                        b = QProgressBar(); b.setValue(g["pct"]); b.setFormat(f"{g['total']} · {g['pct']}%")
                        b.setFixedHeight(12)
                        r.addWidget(b, 1)
                        wg = QWidget(); wg.setLayout(r)
                        split_box.addWidget(wg)
                    dica = QLabel(_t("Cada card entra em um grupo só — a soma fecha em 100% do estágio."))
                    dica.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                    split_box.addWidget(dica)

                combo.currentIndexChanged.connect(
                    lambda idx: _preencher_split(combo.itemData(idx))
                )
                est_box["layout"].insertWidget(1, combo)
                _preencher_split(padrao)
                self.content_layout.addWidget(est_box["box"])

            # — 3 colunas: Alertas | Prazos | Objetivos —
            cols_row = QHBoxLayout()
            cols_row.setSpacing(16)
            cols_row.setAlignment(Qt.AlignTop)

            # Alertas
            alert_box = self._section_box(_t("Alertas"), t)
            if not wip_alerts and not vencidos and not parados:
                alert_box["layout"].addWidget(self._hint(_t("Nenhum alerta — fluxo saudável."), t))
            else:
                for a in wip_alerts:
                    alert_box["layout"].addWidget(self._alert_row(f"WIP: {a}", t.danger, t))
                for tk in vencidos[:5]:
                    alert_box["layout"].addWidget(self._alert_row(f"{tk.code} vencida em {tk.due_date.date().strftime('%d/%m')}", t.danger, t))
                if len(vencidos) > 5:
                    alert_box["layout"].addWidget(self._hint(_t("+ {n} vencida(s)").format(n=len(vencidos)-5), t))
                for tk in parados[:4]:
                    dias = (datetime.utcnow() - tk.updated_at).days if tk.updated_at else 0
                    alert_box["layout"].addWidget(self._alert_row(f"{tk.code} parada há {dias}d", t.warning, t))
                if len(parados) > 4:
                    alert_box["layout"].addWidget(self._hint(_t("+ {n} parada(s)").format(n=len(parados)-4), t))
            cols_row.addWidget(alert_box["box"], 1)

            # Prazos
            prazos_box = self._section_box(_t("Prazos"), t)
            # goals com prazo
            goals_com_prazo = [g for g in goals if g.due_date]
            if sprint_ativa and sprint_ativa.end_date:
                dias = (sprint_ativa.end_date.date() - hoje).days
                cor = t.danger if dias < 0 else (t.warning if dias <= 7 else t.text_primary)
                prazos_box["layout"].addWidget(self._alert_row(f"Sprint {sprint_ativa.name}: {sprint_ativa.end_date.date().strftime('%d/%m/%Y')} ({dias}d)" if dias >= 0 else f"Sprint {sprint_ativa.name}: atrasada", cor, t))
            if goals_com_prazo:
                for g in goals_com_prazo[:5]:
                    dias = (g.due_date.date() - hoje).days
                    cor = t.danger if dias < 0 else (t.warning if dias <= 7 else t.text_primary)
                    done_g, tot_g = _goal_progress(g, s)
                    txt = f"{g.name} — {g.due_date.date().strftime('%d/%m')} ({dias}d)  {done_g}/{tot_g}"
                    prazos_box["layout"].addWidget(self._alert_row(txt, cor, t))
                if len(goals_com_prazo) > 5:
                    prazos_box["layout"].addWidget(self._hint(_t("+ {n} prazo(s)").format(n=len(goals_com_prazo)-5), t))
            elif not (sprint_ativa and sprint_ativa.end_date):
                prazos_box["layout"].addWidget(self._hint(_t("Nenhum prazo definido."), t))
            # tarefas vencidas já estão em alertas, mas mostra próximas a vencer (7d)
            proximas = [tk for tk in tasks_all if tk.due_date and 0 <= (tk.due_date.date() - hoje).days <= 7 and tk.column_id not in done_col_ids]
            if proximas:
                for tk in proximas[:3]:
                    prazos_box["layout"].addWidget(self._hint(f"{tk.code} vence {tk.due_date.date().strftime('%d/%m')}", t))
            cols_row.addWidget(prazos_box["box"], 1)

            # Objetivos
            obj_box = self._section_box(_t("Objetivos"), t)
            if not goals:
                obj_box["layout"].addWidget(self._hint(_t("Nenhum goal — crie em Goals."), t))
            else:
                for g in goals[:4]:
                    done_g, tot_g = _goal_progress(g, s)
                    pct_g = int(done_g / tot_g * 100) if tot_g else 0
                    row = QHBoxLayout()
                    row.setSpacing(6)
                    nome = QLabel(g.name)
                    nome.setStyleSheet(f"color: {t.text_primary}; font-size: 12px; font-weight: 600; border: none;")
                    nome.setWordWrap(True)
                    row.addWidget(nome, 1)
                    if g.due_date:
                        dias = (g.due_date.date() - hoje).days
                        cor = t.danger if dias < 0 else (t.warning if dias <= 3 else t.text_muted)
                        dl = QLabel(f"{dias}d" if dias >= 0 else f"{abs(dias)}d atraso")
                        dl.setStyleSheet(f"color: {cor}; font-size: 11px; font-weight: 700; border: none;")
                        row.addWidget(dl)
                    w = QWidget()
                    w.setLayout(row)
                    obj_box["layout"].addWidget(w)
                    barra = QProgressBar()
                    barra.setValue(pct_g)
                    barra.setFormat(f"{pct_g}% ({done_g}/{tot_g})")
                    barra.setFixedHeight(14)
                    obj_box["layout"].addWidget(barra)
                if len(goals) > 4:
                    obj_box["layout"].addWidget(self._hint(_t("+ {n} objetivo(s)").format(n=len(goals)-4), t))
            cols_row.addWidget(obj_box["box"], 1)

            w_cols = QWidget()
            w_cols.setLayout(cols_row)
            self.content_layout.addWidget(w_cols)

            # — Progresso por módulo / responsável / distribuição —
            mod_row = QHBoxLayout()
            mod_row.setSpacing(12)
            mod_row.setAlignment(Qt.AlignTop)

            # Por épico
            mod_box = self._section_box(_t("Por épico"), t)
            epics_all = s.query(Epic).filter(Epic.project_id == self.project_id).order_by(Epic.name).all()
            epic_data = []
            for ep in epics_all:
                q = s.query(Task).filter(Task.project_id == self.project_id, Task.deleted_at == None, Task.archived_at == None, Task.epics.any(Epic.id == ep.id))
                tot = q.count()
                if tot == 0:
                    continue
                done_e = q.join(BoardColumn, Task.column_id == BoardColumn.id).filter(BoardColumn.is_done == True).count()
                pct_e = int(done_e / tot * 100) if tot else 0
                epic_data.append((ep, done_e, tot, pct_e))
            epic_data.sort(key=lambda x: x[3])
            # Pizza por épico
            if epic_data:
                pie_epic = [(ep.name, tot, ep.color or ["#4f46e5","#06b6d4","#f59e0b","#ef4444","#10b981","#8b5cf6"][i % 6]) for i, (ep, _, tot, _) in enumerate(epic_data[:6])]
                pie_row = QHBoxLayout(); pie_row.setSpacing(8)
                pie = PieChartWidget(pie_epic, size=72)
                pie_row.addWidget(pie)
                leg = QVBoxLayout(); leg.setSpacing(2)
                for label, value, color in pie_epic[:4]:
                    leg_row = QHBoxLayout(); leg_row.setSpacing(4)
                    dot = QLabel(); dot.setFixedSize(10, 10); dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
                    leg_row.addWidget(dot)
                    leg_lbl = QLabel(f"{label} ({value})"); leg_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                    leg_row.addWidget(leg_lbl); leg_row.addStretch()
                    w = QWidget(); w.setLayout(leg_row); leg.addWidget(w)
                if len(pie_epic) > 4:
                    leg.addWidget(self._hint(f"+{len(pie_epic)-4} { _t('outros')}", t))
                w_leg = QWidget(); w_leg.setLayout(leg)
                pie_row.addWidget(w_leg, 1)
                mod_box["layout"].addLayout(pie_row)
            if not epic_data:
                mod_box["layout"].addWidget(self._hint(_t("Nenhum épico vinculado."), t))
            else:
                for ep, done_e, tot, pct_e in epic_data[:6]:
                    row = QHBoxLayout(); row.setSpacing(6)
                    nome = QLabel(ep.name)
                    nome.setStyleSheet(f"color: {ep.color or t.text_primary}; font-size: 12px; font-weight: 600; border: none; border-left: 3px solid {ep.color or t.accent}; padding-left: 6px;")
                    nome.setWordWrap(True)
                    row.addWidget(nome, 1)
                    pct_lbl = QLabel(f"{pct_e}% ({done_e}/{tot})")
                    pct_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
                    row.addWidget(pct_lbl)
                    w = QWidget(); w.setLayout(row)
                    mod_box["layout"].addWidget(w)
                    barra = QProgressBar(); barra.setValue(pct_e); barra.setFormat(f"{pct_e}%"); barra.setFixedHeight(8)
                    barra.setStyleSheet(f"QProgressBar {{ background: {t.bg_badge}; }} QProgressBar::chunk {{ background: {ep.color or t.accent}; }}")
                    mod_box["layout"].addWidget(barra)
                if len(epic_data) > 6:
                    mod_box["layout"].addWidget(self._hint(_t("+ {n} épico(s)").format(n=len(epic_data)-6), t))
            mod_row.addWidget(mod_box["box"], 1)

            # Por responsável (inclui Sem responsável para métricas corretas)
            resp_box = self._section_box(_t("Por responsável"), t)
            from collections import Counter
            assignees = [tk.assignee for tk in tasks_all if tk.assignee]
            cnt = Counter(assignees)
            resp_data = []
            for name, tot in cnt.most_common(6):
                q = [tk for tk in tasks_all if tk.assignee == name]
                done_r = sum(1 for tk in q if tk.column_id in done_col_ids)
                pct_r = int(done_r / tot * 100) if tot else 0
                resp_data.append((name, done_r, tot, pct_r, False))
            # Sem responsável
            unassigned = [tk for tk in tasks_all if not tk.assignee]
            if unassigned:
                tot_u = len(unassigned)
                done_u = sum(1 for tk in unassigned if tk.column_id in done_col_ids)
                pct_u = int(done_u / tot_u * 100) if tot_u else 0
                resp_data.append((_t("Sem responsável"), done_u, tot_u, pct_u, True))
                resp_data.sort(key=lambda x: x[2], reverse=True)
            # Pizza por responsável
            if resp_data:
                pie_data = [(n, tot, "#9ca3af" if is_u else ["#4f46e5","#06b6d4","#f59e0b","#ef4444","#10b981","#8b5cf6","#ec4899"][i % 7]) for i, (n, _, tot, _, is_u) in enumerate(resp_data[:6])]
                pie_row = QHBoxLayout(); pie_row.setSpacing(8)
                pie = PieChartWidget(pie_data, size=72)
                pie_row.addWidget(pie)
                leg = QVBoxLayout(); leg.setSpacing(2)
                for label, value, color in pie_data[:4]:
                    leg_row = QHBoxLayout(); leg_row.setSpacing(4)
                    dot = QLabel(); dot.setFixedSize(10, 10); dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
                    leg_row.addWidget(dot)
                    leg_lbl = QLabel(f"{label} ({value})"); leg_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                    leg_row.addWidget(leg_lbl); leg_row.addStretch()
                    w = QWidget(); w.setLayout(leg_row); leg.addWidget(w)
                if len(pie_data) > 4:
                    leg.addWidget(self._hint(f"+{len(pie_data)-4} { _t('outros')}", t))
                w_leg = QWidget(); w_leg.setLayout(leg)
                pie_row.addWidget(w_leg, 1)
                resp_box["layout"].addLayout(pie_row)
            if not resp_data:
                resp_box["layout"].addWidget(self._hint(_t("Nenhum responsável atribuído."), t))
            else:
                for name, done_r, tot, pct_r, is_u in resp_data[:6]:
                    row = QHBoxLayout(); row.setSpacing(6)
                    nome = QLabel(name)
                    nome.setStyleSheet(f"color: {'#9ca3af' if is_u else t.text_primary}; font-size: 12px; font-weight: 600; border: none;")
                    nome.setWordWrap(True)
                    row.addWidget(nome, 1)
                    pct_lbl = QLabel(f"{pct_r}% ({done_r}/{tot})")
                    pct_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
                    row.addWidget(pct_lbl)
                    w = QWidget(); w.setLayout(row)
                    resp_box["layout"].addWidget(w)
                    barra = QProgressBar(); barra.setValue(pct_r); barra.setFixedHeight(8)
                    if is_u:
                        barra.setStyleSheet(f"QProgressBar {{ background: {t.bg_badge}; }} QProgressBar::chunk {{ background: #9ca3af; }}")
                    resp_box["layout"].addWidget(barra)
            mod_row.addWidget(resp_box["box"], 1)

            # Distribuição por coluna (com pizza)
            dist_box = self._section_box(_t("Distribuição por coluna"), t)
            pie_col_data = [(col.name, sum(1 for tk in tasks_all if tk.column_id == col.id), ["#4f46e5","#06b6d4","#f59e0b","#ef4444","#10b981","#8b5cf6"][i % 6]) for i, col in enumerate(cols) if sum(1 for tk in tasks_all if tk.column_id == col.id) > 0]
            if pie_col_data:
                pie_row = QHBoxLayout(); pie_row.setSpacing(8)
                pie = PieChartWidget(pie_col_data, size=72)
                pie_row.addWidget(pie)
                leg = QVBoxLayout(); leg.setSpacing(2)
                for label, value, color in pie_col_data[:4]:
                    leg_row = QHBoxLayout(); leg_row.setSpacing(4)
                    dot = QLabel(); dot.setFixedSize(10, 10); dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
                    leg_row.addWidget(dot)
                    leg_lbl = QLabel(f"{label} ({value})"); leg_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                    leg_row.addWidget(leg_lbl); leg_row.addStretch()
                    w = QWidget(); w.setLayout(leg_row); leg.addWidget(w)
                w_leg = QWidget(); w_leg.setLayout(leg)
                pie_row.addWidget(w_leg, 1)
                dist_box["layout"].addLayout(pie_row)
            for col in cols:
                cnt_col = sum(1 for tk in tasks_all if tk.column_id == col.id)
                over = col.wip_limit and cnt_col > col.wip_limit
                txt = f"{col.name}: {cnt_col}{f'/{col.wip_limit}' if col.wip_limit else ''}"
                col_lbl = QLabel(f"• {txt}")
                col_lbl.setStyleSheet(f"color: {t.danger if over else t.text_primary}; font-size: 11px; font-weight: {'700' if over else '400'}; border: none;")
                dist_box["layout"].addWidget(col_lbl)
            mod_row.addWidget(dist_box["box"], 1)

            w_mod = QWidget()
            w_mod.setLayout(mod_row)
            self.content_layout.addWidget(w_mod)

            # Linha extra: Por prioridade (pizza) + Métricas de fluxo
            extra_row = QHBoxLayout(); extra_row.setSpacing(12)
            # Por prioridade
            pri_box = self._section_box(_t("Por prioridade"), t)
            from collections import Counter as _Counter2
            pri_counts = _Counter2(tk.priority for tk in tasks_all)
            pri_order = ["URGENT","HIGH","MEDIUM","LOW"]
            pri_colors = {"URGENT":"#ef4444","HIGH":"#f59e0b","MEDIUM":"#4f46e5","LOW":"#9ca3af"}
            pri_data = [(p, pri_counts[p], pri_colors[p]) for p in pri_order if pri_counts[p] > 0]
            if pri_data:
                pie_row = QHBoxLayout(); pie_row.setSpacing(8)
                pie = PieChartWidget(pri_data, size=72)
                pie_row.addWidget(pie)
                leg = QVBoxLayout(); leg.setSpacing(2)
                for label, value, color in pri_data:
                    leg_row = QHBoxLayout(); leg_row.setSpacing(4)
                    dot = QLabel(); dot.setFixedSize(10, 10); dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
                    leg_row.addWidget(dot)
                    leg_lbl = QLabel(f"{label} ({value})"); leg_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                    leg_row.addWidget(leg_lbl); leg_row.addStretch()
                    w = QWidget(); w.setLayout(leg_row); leg.addWidget(w)
                w_leg = QWidget(); w_leg.setLayout(leg)
                pie_row.addWidget(w_leg, 1)
                pri_box["layout"].addLayout(pie_row)
            else:
                pri_box["layout"].addWidget(self._hint(_t("Sem dados"), t))
            extra_row.addWidget(pri_box["box"], 1)
            # Métricas de fluxo
            flow_box = self._section_box(_t("Métricas de fluxo"), t)
            wip_total = sum(1 for tk in tasks_all if tk.column_id not in done_col_ids)
            flow_items = [
                (_t("WIP total"), f"{wip_total} { _t('em aberto')}", t.text_primary),
                (_t("Vencidas"), str(len(vencidos)), t.danger if vencidos else t.text_primary),
                (_t("Paradas 14d+"), str(len(parados)), t.warning if parados else t.text_primary),
                (_t("Sem responsável"), f"{len(unassigned)} ({int(len(unassigned)/len(tasks_all)*100) if tasks_all else 0}%)", "#9ca3af" if unassigned else t.text_primary),
                (_t("Concluídas"), f"{done}/{total} ({pct}%)", t.accent),
            ]
            for label, value, col in flow_items:
                row = QHBoxLayout(); row.setSpacing(6)
                lbl = QLabel(label); lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
                row.addWidget(lbl, 1)
                val = QLabel(value); val.setStyleSheet(f"color: {col}; font-size: 11px; font-weight: 700; border: none;")
                row.addWidget(val)
                w = QWidget(); w.setLayout(row)
                flow_box["layout"].addWidget(w)
            extra_row.addWidget(flow_box["box"], 1)
            w_extra = QWidget(); w_extra.setLayout(extra_row)
            self.content_layout.addWidget(w_extra)

            # Módulos e submódulos (classificação explícita: módulo != sprint != tag)
            from maestro_local.dimensions import aggregate_dimensions

            dims = aggregate_dimensions(tasks_all, done_col_ids)
            hier_box = self._section_box("📊 " + _t("Módulos e submódulos"), t)
            plano = dims.get("plan") or {}
            resumo = QLabel(
                f"{plano.get('modules', 0)} {_t('módulos')} · {plano.get('endpoints', 0)} {_t('endpoints no plano')}"
                f"  ·  {dims['with_module']}/{dims['cards']} {_t('cards com módulo')}"
                + (f"  ·  {dims['unlabeled']['total']} {_t('sem módulo')}" if dims['unlabeled']['total'] else "")
            )
            resumo.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
            hier_box["layout"].addWidget(resumo)

            if not dims["modules"]:
                hier_box["layout"].addWidget(self._hint(_t("Nenhum módulo identificado nas labels."), t))
            else:
                max_mod = max(m["total"] for m in dims["modules"]) or 1
                for mod in dims["modules"]:
                    cor = t.success if mod["pct"] == 100 else (t.warning if mod["pct"] > 0 else t.text_muted)
                    row = QHBoxLayout(); row.setSpacing(6)
                    ep = f" / {mod['endpoints']} {_t('endpoints')}" if mod.get("endpoints") else ""
                    nome = QLabel(f"{mod['label']} · {mod['total']} {_t('cards')}{ep}")
                    nome.setStyleSheet(f"color: {t.text_primary}; font-size: 11px; font-weight: 600; border: none;")
                    row.addWidget(nome, 1)
                    pct_lbl = QLabel(f"{mod['done']}/{mod['total']} — {mod['pct']}%")
                    pct_lbl.setStyleSheet(f"color: {cor}; font-size: 11px; font-weight: 600; border: none;")
                    row.addWidget(pct_lbl)
                    w = QWidget(); w.setLayout(row)
                    hier_box["layout"].addWidget(w)
                    bar = QProgressBar(); bar.setValue(mod["pct"]); bar.setFixedHeight(8)
                    bar.setMaximumWidth(max(80, int(320 * mod["total"] / max_mod)))
                    hier_box["layout"].addWidget(bar)

                    for sub in mod.get("submodules", []):
                        sub_row = QHBoxLayout(); sub_row.setSpacing(6)
                        ep_sub = f" · {sub['endpoints']} ep" if sub.get("endpoints") else ""
                        sub_lbl = QLabel(f"    {sub['label']} ({sub['name']}{ep_sub})")
                        sub_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                        sub_row.addWidget(sub_lbl, 1)
                        sub_pct = QLabel(f"{sub['done']}/{sub['total']} — {sub['pct']}%")
                        sub_pct.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                        sub_row.addWidget(sub_pct)
                        w2 = QWidget(); w2.setLayout(sub_row)
                        hier_box["layout"].addWidget(w2)
            self.content_layout.addWidget(hier_box["box"])

            if dims.get("discontinued"):
                fora = "  ·  ".join(
                    f"{x['label']} ({x['total']} {_t('cards')}"
                    + (f" / {x['endpoints']} ep" if x.get("endpoints") else "")
                    + f") — {x.get('reason', '')}"
                    for x in dims["discontinued"]
                )
                fora_box = self._section_box(_t("Fora de escopo"), t)
                fora_lbl = QLabel(fora)
                fora_lbl.setWordWrap(True)
                fora_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                fora_box["layout"].addWidget(fora_lbl)
                self.content_layout.addWidget(fora_box["box"])

            # Sprints / plataformas / natureza — dimensões separadas do módulo
            if dims["sprints"] or dims["platforms"] or dims["process"]:
                extra_dims = QHBoxLayout(); extra_dims.setSpacing(12)
                if dims["sprints"]:
                    sp_box = self._section_box(_t("Por sprint"), t)
                    for sp in dims["sprints"]:
                        r = QHBoxLayout(); r.setSpacing(6)
                        lb = QLabel(sp["label"]); lb.setStyleSheet(f"color: {t.text_primary}; font-size: 11px; border: none;")
                        r.addWidget(lb, 1)
                        vl = QLabel(f"{sp['done']}/{sp['total']} — {sp['pct']}%")
                        vl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                        r.addWidget(vl)
                        w = QWidget(); w.setLayout(r); sp_box["layout"].addWidget(w)
                        b = QProgressBar(); b.setValue(sp["pct"]); b.setFixedHeight(6)
                        sp_box["layout"].addWidget(b)
                    extra_dims.addWidget(sp_box["box"], 1)
                if dims["platforms"]:
                    pl_box = self._section_box(_t("Por plataforma"), t)
                    for pl in dims["platforms"]:
                        r = QHBoxLayout(); r.setSpacing(6)
                        lb = QLabel(pl["label"]); lb.setStyleSheet(f"color: {t.text_primary}; font-size: 11px; border: none;")
                        r.addWidget(lb, 1)
                        vl = QLabel(f"{pl['done']}/{pl['total']}")
                        vl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                        r.addWidget(vl)
                        w = QWidget(); w.setLayout(r); pl_box["layout"].addWidget(w)
                    pl_box["layout"].addWidget(self._hint(_t("Não entra no progresso por módulo."), t))
                    extra_dims.addWidget(pl_box["box"], 1)
                if dims["process"]:
                    pr_box = self._section_box(_t("Por natureza"), t)
                    for pr in dims["process"]:
                        r = QHBoxLayout(); r.setSpacing(6)
                        lb = QLabel(pr["label"]); lb.setStyleSheet(f"color: {t.text_primary}; font-size: 11px; border: none;")
                        r.addWidget(lb, 1)
                        vl = QLabel(f"{pr['done']}/{pr['total']} — {pr['pct']}%")
                        vl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
                        r.addWidget(vl)
                        w = QWidget(); w.setLayout(r); pr_box["layout"].addWidget(w)
                    extra_dims.addWidget(pr_box["box"], 1)
                w_dims = QWidget(); w_dims.setLayout(extra_dims)
                self.content_layout.addWidget(w_dims)

        finally:
            s.close()

    def _section_box(self, titulo, t):
        box = QFrame()
        box.setStyleSheet(f"QFrame {{ background: {t.bg_secondary}; border: 1px solid {t.border_light}; border-radius: 8px; }}")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)
        ttl = QLabel(titulo)
        ttl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; border: none;")
        lay.addWidget(ttl)
        return {"box": box, "layout": lay}

    def _alert_row(self, texto, cor, t):
        lbl = QLabel(f"• {texto}")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {cor}; font-size: 11px; border: none;")
        return lbl

    def _hint(self, texto, t):
        lbl = QLabel(texto)
        lbl.setWordWrap(True)
        lbl.setProperty("class", "hint")
        lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        return lbl


# ────────────────────────────────────────────────────────────
# ProjectDailyTab — diário/comentário diário do projeto
# ────────────────────────────────────────────────────────────

DAILY_KINDS = [
    ("WORK", "Trabalho", "#16a34a"),
    ("BLOCKER", "Bloqueio", "#dc2626"),
    ("DECISION", "Decisão", "#4f46e5"),
    ("NOTE", "Nota", "#6b7280"),
]


class ProjectDailyTab(QWidget):
    """Registro diário do projeto: cada linha é um comentário do dia.

    Serve de doc de daily: filtra por período, tipo, autor e texto; permite
    criar, editar e excluir. Os mesmos dados ficam expostos em
    `/api/projects/{id}/daily` para os agentes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        t = current_theme()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # --- resumo + ações do doc ---
        resumo_row = QHBoxLayout()
        resumo_row.setSpacing(6)
        self.summary_lbl = QLabel("")
        self.summary_lbl.setProperty("class", "hint")
        resumo_row.addWidget(self.summary_lbl, 1)
        self.export_btn = QPushButton("⬇ " + _t("Exportar .md"))
        self.export_btn.setProperty("flat", True)
        self.export_btn.setFixedHeight(26)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setToolTip(_t("Exportar o dia em markdown (formato do vault)"))
        self.export_btn.clicked.connect(self._export)
        resumo_row.addWidget(self.export_btn)
        self.import_btn = QPushButton("⬆ " + _t("Importar .md"))
        self.import_btn.setProperty("flat", True)
        self.import_btn.setFixedHeight(26)
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.setToolTip(_t("Importar um doc de daily (.md)"))
        self.import_btn.clicked.connect(self._import)
        resumo_row.addWidget(self.import_btn)
        root.addLayout(resumo_row)

        # --- formulário ---
        form = QFrame()
        form.setStyleSheet(f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 10px; }}")
        fl = QVBoxLayout(form)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(6)

        title = QLabel(_t("Novo registro do dia"))
        title.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {t.text_primary}; border: none;")
        fl.addWidget(title)

        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText(_t("O que você fez hoje neste projeto..."))
        self.body_input.setMinimumHeight(70)
        fl.addWidget(self.body_input)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(QDate.currentDate())
        row.addWidget(QLabel(_t("Dia:")))
        row.addWidget(self.date_input)

        row.addWidget(QLabel(_t("Tipo:")))
        self.kind_combo = QComboBox()
        for key, label, _color in DAILY_KINDS:
            self.kind_combo.addItem(_t(label), key)
        row.addWidget(self.kind_combo)

        self.minutes_input = QLineEdit()
        self.minutes_input.setPlaceholderText(_t("min"))
        self.minutes_input.setFixedWidth(70)
        row.addWidget(self.minutes_input)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText(_t("Card (opcional)"))
        self.task_input.setFixedWidth(140)
        row.addWidget(self.task_input)

        self.add_btn = QPushButton(_t("Registrar"))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add)
        row.addWidget(self.add_btn)
        row.addStretch()
        fl.addLayout(row)
        root.addWidget(form)

        # --- filtros ---
        filters = QHBoxLayout()
        filters.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_t("Buscar no texto..."))
        self.search_input.textChanged.connect(self.refresh)
        filters.addWidget(self.search_input, 1)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setSpecialValueText(_t("De"))
        self.from_date.setDate(self.from_date.minimumDate())
        self.from_date.dateChanged.connect(self.refresh)
        filters.addWidget(self.from_date)

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setSpecialValueText(_t("Até"))
        self.to_date.setDate(self.to_date.minimumDate())
        self.to_date.dateChanged.connect(self.refresh)
        filters.addWidget(self.to_date)

        self.kind_filter = QComboBox()
        self.kind_filter.addItem(_t("Todos os tipos"), None)
        for key, label, _color in DAILY_KINDS:
            self.kind_filter.addItem(_t(label), key)
        self.kind_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.kind_filter)

        self.author_filter = QLineEdit()
        self.author_filter.setPlaceholderText(_t("Autor"))
        self.author_filter.setFixedWidth(120)
        self.author_filter.textChanged.connect(self.refresh)
        filters.addWidget(self.author_filter)

        clear_btn = QPushButton(_t("Limpar"))
        clear_btn.setProperty("flat", True)
        clear_btn.clicked.connect(self._clear_filters)
        filters.addWidget(clear_btn)
        root.addLayout(filters)

        # --- lista ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

    # ------------------------------------------------------------------
    def set_project(self, project_id):
        self.project_id = project_id
        self.refresh()

    def _clear_filters(self):
        for w in (self.search_input, self.author_filter):
            w.blockSignals(True)
            w.clear()
            w.blockSignals(False)
        for w in (self.from_date, self.to_date):
            w.blockSignals(True)
            w.setDate(w.minimumDate())
            w.blockSignals(False)
        self.kind_filter.blockSignals(True)
        self.kind_filter.setCurrentIndex(0)
        self.kind_filter.blockSignals(False)
        self.refresh()

    def _clear_layout(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif item.layout() is not None:
                while item.layout().count():
                    c = item.layout().takeAt(0)
                    if c.widget():
                        c.widget().hide()
                        c.widget().setParent(None)
                        c.widget().deleteLater()

    def _filters(self) -> dict:
        q = self.search_input.text().strip()
        author = self.author_filter.text().strip()
        kind = self.kind_filter.currentData()
        date_from = self.from_date.date()
        date_to = self.to_date.date()
        return {
            "q": q or None,
            "author": author or None,
            "kind": kind,
            "date_from": None if date_from == self.from_date.minimumDate() else date_from.toString("yyyy-MM-dd"),
            "date_to": None if date_to == self.to_date.minimumDate() else date_to.toString("yyyy-MM-dd"),
        }

    def refresh(self):
        self._clear_layout()
        t = current_theme()
        if not self.project_id:
            self.summary_lbl.setText("")
            return

        f = self._filters()
        s = get_session()
        try:
            query = s.query(ProjectDailyEntry).filter(ProjectDailyEntry.project_id == self.project_id)
            if f["date_from"]:
                query = query.filter(ProjectDailyEntry.date >= f["date_from"])
            if f["date_to"]:
                query = query.filter(ProjectDailyEntry.date <= f["date_to"])
            if f["kind"]:
                query = query.filter(ProjectDailyEntry.kind == f["kind"])
            if f["author"]:
                query = query.filter(ProjectDailyEntry.author.ilike(f"%{f['author']}%"))
            if f["q"]:
                query = query.filter(ProjectDailyEntry.body.ilike(f"%{f['q']}%"))
            entries = (
                query.order_by(
                    ProjectDailyEntry.date.desc(),
                    ProjectDailyEntry.sort_order.asc(),
                    ProjectDailyEntry.id.asc(),
                ).limit(2000).all()
            )

            total_min = sum(e.minutes or 0 for e in entries)
            dias = len({e.date for e in entries})
            self.summary_lbl.setText(
                _t("{n} registro(s) em {d} dia(s)").format(n=len(entries), d=dias)
                + (f"  ·  {round(total_min / 60, 1)}h " + _t("registradas") if total_min else "")
            )

            if not entries:
                vazio = QLabel(_t("Nenhum registro ainda. Escreva o primeiro acima."))
                vazio.setProperty("class", "hint")
                self.list_layout.addWidget(vazio)
                self.list_layout.addStretch()
                return

            dia_atual = None
            for e in entries:
                if e.date != dia_atual:
                    dia_atual = e.date
                    header = QLabel(dia_atual)
                    header.setStyleSheet(
                        f"font-family: monospace; font-size: 12px; font-weight: 700; "
                        f"color: {t.text_muted}; border: none; padding-top: 6px;"
                    )
                    self.list_layout.addWidget(header)
                self.list_layout.addWidget(self._entry_row(e, t))
            self.list_layout.addStretch()
        finally:
            s.close()

    def _entry_row(self, entry, t):
        cor = next((c for k, _l, c in DAILY_KINDS if k == (entry.kind or "WORK")), "#6b7280")
        label = next((l for k, l, _c in DAILY_KINDS if k == (entry.kind or "WORK")), entry.kind)

        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-left: 3px solid {cor}; border-radius: 8px; }}"
        )
        v = QVBoxLayout(row)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)
        kind_lbl = QLabel(_t(label).upper())
        kind_lbl.setStyleSheet(f"color: {cor}; font-size: 10px; font-weight: 800; border: none; letter-spacing: .5px;")
        top.addWidget(kind_lbl)
        metas = [x for x in [entry.author, (f"{entry.minutes} min" if entry.minutes else None), entry.task_code] if x]
        if metas:
            meta_lbl = QLabel("  ·  ".join(metas))
            meta_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
            top.addWidget(meta_lbl)
        top.addStretch()

        hora = entry.created_at.strftime("%H:%M") if entry.created_at else ""
        hora_lbl = QLabel(hora)
        hora_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 10px; border: none;")
        top.addWidget(hora_lbl)

        editar = QPushButton(_t("Editar"))
        editar.setProperty("flat", True)
        editar.setFixedHeight(24)
        editar.setCursor(Qt.PointingHandCursor)
        editar.clicked.connect(lambda _=False, eid=entry.id: self._edit(eid))
        top.addWidget(editar)

        excluir = QPushButton("✕")
        excluir.setFixedSize(24, 24)
        excluir.setCursor(Qt.PointingHandCursor)
        excluir.setStyleSheet(f"background: transparent; color: {t.danger}; border: none;")
        excluir.clicked.connect(lambda _=False, eid=entry.id: self._delete(eid))
        top.addWidget(excluir)
        v.addLayout(top)

        corpo = QLabel(entry.body or "")
        corpo.setWordWrap(True)
        corpo.setStyleSheet(f"color: {t.text_primary}; font-size: 12px; border: none;")
        v.addWidget(corpo)
        return row

    # ------------------------------------------------------------------
    def _export(self):
        if not self.project_id:
            return
        from maestro_local.daily_doc import render_daily_markdown, suggested_filename, DailyBlock

        dia = self.date_input.date().toString("yyyy-MM-dd")
        s = get_session()
        try:
            entries = (
                s.query(ProjectDailyEntry)
                .filter(ProjectDailyEntry.project_id == self.project_id, ProjectDailyEntry.date == dia)
                .order_by(ProjectDailyEntry.sort_order, ProjectDailyEntry.id)
                .all()
            )
            if not entries:
                QMessageBox.information(self, _t("Daily"), _t("Nada para exportar em") + f" {dia}.")
                return
            blocks = [
                DailyBlock(section=e.section or "ITEMS", title=e.title or "", body=e.body or "",
                           kind=e.kind or "WORK", author=e.author, minutes=e.minutes,
                           task_code=e.task_code or "", sort_order=e.sort_order or 0)
                for e in entries
            ]
            titulo = next((e.title for e in entries if e.section == "INTRO" and e.title), "")
            if not titulo:
                titulo = next((e.title for e in entries if e.section == "ITEMS" and e.title), "")
            markdown = render_daily_markdown(dia, titulo, blocks)
            nome, _mes = suggested_filename(dia, titulo)
        finally:
            s.close()

        from PySide6.QtWidgets import QFileDialog
        destino, _ = QFileDialog.getSaveFileName(self, _t("Exportar daily"), nome, "Markdown (*.md)")
        if not destino:
            return
        try:
            from pathlib import Path
            Path(destino).write_text(markdown, encoding="utf-8")
            QMessageBox.information(self, _t("Exportar daily"), _t("Exportado:") + f"\n{destino}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, _t("Exportar daily"), str(e))

    def _import(self):
        if not self.project_id:
            return
        from PySide6.QtWidgets import QFileDialog
        origem, _ = QFileDialog.getOpenFileName(self, _t("Importar daily"), "", "Markdown (*.md)")
        if not origem:
            return
        from pathlib import Path
        from maestro_local.daily_doc import parse_daily_markdown

        try:
            day, titulo, blocks = parse_daily_markdown(Path(origem).read_text(encoding="utf-8", errors="replace"))
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, _t("Importar daily"), str(e))
            return
        if not day or not blocks:
            QMessageBox.warning(self, _t("Importar daily"), _t("Não encontrei o cabeçalho '# Daily - DD/MM/AAAA' no arquivo."))
            return

        resposta = QMessageBox.question(
            self, _t("Importar daily"),
            _t("Importar") + f" {day} ({len(blocks)} " + _t("bloco(s)") + ")?\n" + _t("Os registros do dia serão substituídos."),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return

        s = get_session()
        try:
            for old in (
                s.query(ProjectDailyEntry)
                .filter(ProjectDailyEntry.project_id == self.project_id, ProjectDailyEntry.date == day)
                .all()
            ):
                s.delete(old)
            s.flush()
            for i, b in enumerate(blocks):
                s.add(ProjectDailyEntry(
                    project_id=self.project_id,
                    date=day,
                    kind=(b.kind or "WORK")[:20],
                    section=(b.section or "ITEMS")[:20],
                    title=(b.title or "")[:200],
                    sort_order=i,
                    body=b.body or "",
                    author=(b.author or None),
                    minutes=b.minutes,
                    task_code=(b.task_code or "")[:40],
                ))
            s.commit()
        except Exception as e:  # noqa: BLE001
            s.rollback()
            QMessageBox.warning(self, _t("Importar daily"), str(e))
            return
        finally:
            s.close()

        self.date_input.setDate(QDate.fromString(day, "yyyy-MM-dd"))
        self.refresh()
        QMessageBox.information(self, _t("Importar daily"), _t("Importado") + f" {day} ({len(blocks)}).")

    def _add(self):
        texto = self.body_input.toPlainText().strip()
        if not texto or not self.project_id:
            return
        minutos = self.minutes_input.text().strip()
        s = get_session()
        try:
            s.add(ProjectDailyEntry(
                project_id=self.project_id,
                date=self.date_input.date().toString("yyyy-MM-dd"),
                kind=self.kind_combo.currentData() or "WORK",
                body=texto,
                author=None,
                minutes=int(minutos) if minutos.isdigit() else None,
                task_code=self.task_input.text().strip()[:40],
            ))
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()
        self.body_input.clear()
        self.minutes_input.clear()
        self.task_input.clear()
        self.refresh()

    def _edit(self, entry_id):
        s = get_session()
        try:
            entry = s.get(ProjectDailyEntry, entry_id)
            if not entry:
                return
            atual = {"body": entry.body, "date": entry.date, "kind": entry.kind,
                     "minutes": entry.minutes, "task_code": entry.task_code}
        finally:
            s.close()

        from PySide6.QtWidgets import QInputDialog
        texto, ok = QInputDialog.getMultiLineText(self, _t("Editar registro"), _t("Texto:"), atual["body"] or "")
        if not ok:
            return
        if not texto.strip():
            QMessageBox.warning(self, _t("Daily"), _t("O texto não pode ficar vazio."))
            return

        labels = [l for _k, l, _c in DAILY_KINDS]
        atual_label = next((l for k, l, _c in DAILY_KINDS if k == atual["kind"]), labels[0])
        lab, ok2 = QInputDialog.getItem(self, _t("Editar registro"), _t("Tipo:"), labels, labels.index(atual_label), False)
        if not ok2:
            return
        novo_kind = next((k for k, l, _c in DAILY_KINDS if l == lab), atual["kind"])

        dia, ok3 = QInputDialog.getText(self, _t("Editar registro"), _t("Dia (AAAA-MM-DD):"), text=atual["date"])
        if not ok3:
            return
        try:
            datetime.strptime(dia.strip(), "%Y-%m-%d")
        except ValueError:
            QMessageBox.warning(self, _t("Daily"), _t("Dia inválido. Use AAAA-MM-DD."))
            return

        minutos_txt, ok4 = QInputDialog.getText(
            self, _t("Editar registro"), _t("Minutos (vazio = sem registro):"),
            text=str(atual["minutes"]) if atual["minutes"] else "",
        )
        if not ok4:
            return

        s = get_session()
        try:
            entry = s.get(ProjectDailyEntry, entry_id)
            if entry:
                entry.body = texto.strip()
                entry.date = dia.strip()
                entry.kind = novo_kind
                entry.minutes = int(minutos_txt) if minutos_txt.strip().isdigit() else None
                s.commit()
        finally:
            s.close()
        self.refresh()

    def _delete(self, entry_id):
        resposta = QMessageBox.question(
            self, _t("Daily"), _t("Excluir este registro?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return
        s = get_session()
        try:
            entry = s.get(ProjectDailyEntry, entry_id)
            if entry:
                s.delete(entry)
                s.commit()
        finally:
            s.close()
        self.refresh()


# ────────────────────────────────────────────────────────────
# ArchivedDialog
# ────────────────────────────────────────────────────────────

class ProjectLinksWidget(QFrame):
    """Atalhos do projeto — links com título (PRs, docs, board externo, etc)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        t = current_theme()
        self.setStyleSheet(f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 10px; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("🔗 " + _t("Atalhos"))
        title.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {t.text_primary}; border: none;")
        head.addWidget(title)
        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        head.addWidget(self.count_lbl)
        head.addStretch()
        root.addLayout(head)

        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(6)
        root.addLayout(self.list_layout)

        form = QHBoxLayout()
        form.setSpacing(6)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(_t("Título do atalho"))
        form.addWidget(self.title_input, 1)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://...")
        form.addWidget(self.url_input, 2)
        add_btn = QPushButton(_t("+ Adicionar atalho"))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add)
        form.addWidget(add_btn)
        root.addLayout(form)

        hint = QLabel(_t("Ex.: PR da sprint, doc de migração, board externo, pipeline."))
        hint.setProperty("class", "hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._editing_id = None

    def set_project(self, project_id):
        self.project_id = project_id
        self.refresh()

    def refresh(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif item.layout():
                while item.layout().count():
                    c = item.layout().takeAt(0)
                    if c.widget():
                        c.widget().hide()
                        c.widget().setParent(None)
                        c.widget().deleteLater()
        t = current_theme()
        if not self.project_id:
            self.count_lbl.setText("")
            return
        s = get_session()
        try:
            from maestro_local.db.models import ProjectLink
            links = s.query(ProjectLink).filter(ProjectLink.project_id == self.project_id).order_by(ProjectLink.sort_order, ProjectLink.id).all()
            self.count_lbl.setText(f"{len(links)} { _t('atalho(s)')}")
            if not links:
                lbl = QLabel(_t("Nenhum atalho ainda."))
                lbl.setProperty("class", "hint")
                self.list_layout.addWidget(lbl)
            for link in links:
                row = QFrame()
                row.setStyleSheet(f"QFrame {{ background: {t.bg_secondary}; border: 1px solid {t.border_light}; border-radius: 8px; }}")
                h = QHBoxLayout(row)
                h.setContentsMargins(8, 6, 8, 6)
                h.setSpacing(6)
                title = QLabel(link.title)
                title.setStyleSheet(f"color: {t.accent}; font-size: 12px; font-weight: 600; border: none;")
                title.setWordWrap(True)
                h.addWidget(title, 1)
                open_btn = QPushButton("↗")
                open_btn.setFixedSize(28, 28)
                open_btn.setCursor(Qt.PointingHandCursor)
                open_btn.setToolTip(link.url)
                lid = link.id
                url = link.url
                open_btn.clicked.connect(lambda _, u=url: self._open(u))
                h.addWidget(open_btn)
                edit_btn = QPushButton(_t("Editar"))
                edit_btn.setProperty("flat", True)
                edit_btn.setFixedHeight(26)
                edit_btn.clicked.connect(lambda _, x=lid: self._start_edit(x))
                h.addWidget(edit_btn)
                del_btn = QPushButton("✕")
                del_btn.setFixedSize(28, 28)
                del_btn.setStyleSheet(f"color: {t.danger}; background: transparent; border: none;")
                del_btn.clicked.connect(lambda _, x=lid: self._delete(x))
                h.addWidget(del_btn)
                self.list_layout.addWidget(row)
        finally:
            s.close()

    def _open(self, url):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))

    def _add(self):
        title = self.title_input.text().strip()
        url = self.url_input.text().strip()
        if not title or not url:
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(self, _t("Atalho"), _t("URL deve começar com http:// ou https://"))
            return
        s = get_session()
        try:
            from maestro_local.db.models import ProjectLink
            order = s.query(ProjectLink).filter(ProjectLink.project_id == self.project_id).count()
            link = ProjectLink(project_id=self.project_id, title=title[:120], url=url[:500], sort_order=order)
            s.add(link)
            s.commit()
        finally:
            s.close()
        self.title_input.clear()
        self.url_input.clear()
        self.refresh()

    def _start_edit(self, link_id):
        s = get_session()
        try:
            from maestro_local.db.models import ProjectLink
            link = s.get(ProjectLink, link_id)
            if not link:
                return
            cur_title, cur_url = link.title, link.url
        finally:
            s.close()
        from PySide6.QtWidgets import QInputDialog
        title, ok1 = QInputDialog.getText(self, _t("Editar atalho"), _t("Título do atalho"), text=cur_title)
        if not ok1 or not title.strip():
            return
        url, ok2 = QInputDialog.getText(self, _t("Editar atalho"), _t("Link do atalho (cole a URL):"), text=cur_url)
        if not ok2 or not url.strip():
            return
        if not (url.strip().startswith("http://") or url.strip().startswith("https://")):
            QMessageBox.warning(self, _t("Atalho"), _t("URL deve começar com http:// ou https://"))
            return
        s = get_session()
        try:
            from maestro_local.db.models import ProjectLink
            link = s.get(ProjectLink, link_id)
            if link:
                link.title = title.strip()[:120]
                link.url = url.strip()[:500]
                s.commit()
            self.refresh()
        finally:
            s.close()

    def _delete(self, link_id):
        s = get_session()
        try:
            from maestro_local.db.models import ProjectLink
            link = s.get(ProjectLink, link_id)
            if link:
                pid = link.project_id
                s.delete(link)
                s.commit()
                remaining = s.query(ProjectLink).filter(ProjectLink.project_id == pid).order_by(ProjectLink.sort_order).all()
                for i, l in enumerate(remaining):
                    l.sort_order = i
                s.commit()
            self.refresh()
        finally:
            s.close()


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
# BoardView
# ────────────────────────────────────────────────────────────

class BoardView(QWidget):
    task_changed = Signal()
    project_opened = Signal(int)
    back_requested = Signal()

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
        self.main_layout.setContentsMargins(20, 18, 20, 20)
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
        self.back_btn = QPushButton("← " + _t("Projetos"))
        self.back_btn.setProperty("flat", True)
        self.back_btn.setFixedHeight(28)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setToolTip(_t("Voltar à lista de projetos"))
        self.back_btn.clicked.connect(lambda: self.back_requested.emit())
        header_row.addWidget(self.back_btn)
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

        self.members_btn = QPushButton(_t("Responsáveis"))
        self.members_btn.setProperty("flat", True)
        self.members_btn.setFixedHeight(28)
        self.members_btn.setCursor(Qt.PointingHandCursor)
        self.members_btn.clicked.connect(self._open_members)
        header_row.addWidget(self.members_btn)

        self.columns_btn = QPushButton(_t("Colunas"))
        self.columns_btn.setProperty("flat", True)
        self.columns_btn.setFixedHeight(28)
        self.columns_btn.setCursor(Qt.PointingHandCursor)
        self.columns_btn.setToolTip(_t("Personalizar colunas do quadro"))
        self.columns_btn.clicked.connect(self._open_columns)
        header_row.addWidget(self.columns_btn)

        self.archived_btn = QPushButton(_t("Arquivados"))
        self.archived_btn.setProperty("flat", True)
        self.archived_btn.setFixedHeight(28)
        self.archived_btn.setCursor(Qt.PointingHandCursor)
        self.archived_btn.clicked.connect(self._open_archived)
        header_row.addWidget(self.archived_btn)

        self.board_link_btn = QPushButton("🔗 Board")
        self.board_link_btn.setFixedHeight(28)
        self.board_link_btn.setCursor(Qt.PointingHandCursor)
        self.board_link_btn.setToolTip(_t("Abrir board externo"))
        self.board_link_btn.clicked.connect(self._open_board_link)
        self.board_link_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self.board_link_btn.customContextMenuRequested.connect(lambda _: self._edit_board_link())
        header_row.addWidget(self.board_link_btn)

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

        # Atalhos do projeto
        self.links_widget = ProjectLinksWidget()
        board_tab_layout.addWidget(self.links_widget)

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

        # --- Aba "Métricas" (ao lado do kanban) ---
        self.metrics_tab = QWidget()
        metrics_layout = QVBoxLayout(self.metrics_tab)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(12)
        acoes_metrics = QHBoxLayout()
        acoes_metrics.addStretch()
        self.export_metrics_btn = QPushButton("⬇ " + _t("Exportar PDF"))
        self.export_metrics_btn.setProperty("flat", True)
        self.export_metrics_btn.setFixedHeight(28)
        self.export_metrics_btn.setCursor(Qt.PointingHandCursor)
        self.export_metrics_btn.setToolTip(_t("Exportar as métricas em PDF"))
        self.export_metrics_btn.clicked.connect(self._export_metrics_pdf)
        acoes_metrics.addWidget(self.export_metrics_btn)
        metrics_layout.addLayout(acoes_metrics)

        self.metrics_accordion = BoardMetricsAccordion()
        # Métricas em aba tem scroll próprio
        metrics_scroll = QScrollArea()
        metrics_scroll.setWidgetResizable(True)
        metrics_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        metrics_container = QWidget()
        metrics_container_layout = QVBoxLayout(metrics_container)
        metrics_container_layout.setContentsMargins(0, 0, 0, 0)
        metrics_container_layout.setSpacing(12)
        metrics_container_layout.addWidget(self.metrics_accordion)
        metrics_scroll.setWidget(metrics_container)
        metrics_layout.addWidget(metrics_scroll)

        # --- Aba "Daily" (registro diário do projeto) ---
        self.daily_tab = QWidget()
        daily_layout = QVBoxLayout(self.daily_tab)
        daily_layout.setContentsMargins(0, 0, 0, 0)
        daily_layout.setSpacing(10)
        self.daily_view = ProjectDailyTab()
        daily_layout.addWidget(self.daily_view)

        # --- Abas ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self.board_tab, _t("Board"))
        self.tabs.addTab(self.metrics_tab, _t("Métricas"))
        self.tabs.addTab(self.daily_tab, "📝 " + _t("Daily"))
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
        if hasattr(self, "metrics_accordion"):
            self.metrics_accordion.set_project(project_id)
        if hasattr(self, "links_widget"):
            self.links_widget.set_project(project_id)
        if hasattr(self, "daily_view"):
            self.daily_view.set_project(project_id)
        # Novo projeto: re-aplica o default (sprint ativa) e volta o filtro.
        self._sprint_filter_initialized = False
        self._sprint_filter = None
        if hasattr(self, "back_btn"):
            self.back_btn.setVisible(bool(project_id))
        if hasattr(self, "board_link_btn"):
            self._update_board_link_button()
        if project_id:
            self.empty_widget.setVisible(False)
            self.board_widget.setVisible(True)
        else:
            self.empty_widget.setVisible(True)
            self.board_widget.setVisible(False)
            self._load_project_list()
        # Reseta para a aba Board ao trocar de projeto.
        if hasattr(self, "tabs"):
            self.tabs.setCurrentIndex(0)
        self.refresh()

    def _on_tab_changed(self, idx):
        pass

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

    def _open_members(self):
        if not self.project_id:
            return
        dlg = MembersDialog(self.project_id, self)
        dlg.exec()
        self.refresh()
        self.task_changed.emit()

    def _open_columns(self):
        if not self.project_id:
            return
        dlg = ColumnManagerDialog(self.project_id, self)
        if dlg.exec() == QDialog.Accepted and dlg.changed:
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

    def _export_metrics_pdf(self):
        """Gera o relatório de métricas do projeto em PDF."""
        if not self.project_id:
            return
        from maestro_local.metrics_pdf import build_metrics_pdf, metrics_pdf_filename

        s = get_session()
        try:
            project = s.get(Project, self.project_id)
            if not project:
                return
            nome = metrics_pdf_filename(project)
            try:
                pdf = build_metrics_pdf(s, project)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self, _t("Exportar PDF"), str(e))
                return
        finally:
            s.close()

        from PySide6.QtWidgets import QFileDialog
        destino, _ = QFileDialog.getSaveFileName(self, _t("Exportar PDF"), nome, "PDF (*.pdf)")
        if not destino:
            return
        try:
            from pathlib import Path
            Path(destino).write_bytes(pdf)
            QMessageBox.information(self, _t("Exportar PDF"), _t("Exportado:") + f"\n{destino}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, _t("Exportar PDF"), str(e))

    def _open_archived(self):
        if not self.project_id:
            return
        dlg = ArchivedDialog(self.project_id, self)
        dlg.exec()
        self.refresh()

    def _open_board_link(self):
        if not self.project_id:
            return
        s = get_session()
        try:
            p = s.get(Project, self.project_id)
            url = (getattr(p, "board_url", "") or "").strip() if p else ""
        finally:
            s.close()
        if url:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(url))
        else:
            self._edit_board_link()

    def _edit_board_link(self):
        if not self.project_id:
            return
        s = get_session()
        try:
            p = s.get(Project, self.project_id)
            cur = (getattr(p, "board_url", "") or "") if p else ""
        finally:
            s.close()
        from PySide6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(self, _t("Link do Board"), _t("Link do board externo (cole a URL):"), text=cur)
        if not ok:
            return
        s = get_session()
        try:
            p = s.get(Project, self.project_id)
            if p is not None:
                p.board_url = url.strip()
                s.commit()
            self._update_board_link_button()
        finally:
            s.close()

    def _update_board_link_button(self):
        if not hasattr(self, "board_link_btn"):
            return
        s = get_session()
        try:
            p = s.get(Project, self.project_id) if self.project_id else None
            url = (getattr(p, "board_url", "") or "").strip() if p else ""
        finally:
            s.close()
        t = current_theme()
        if url:
            self.board_link_btn.setText("🔗 Board")
            self.board_link_btn.setToolTip(url)
            self.board_link_btn.setStyleSheet(f"QPushButton {{ background: #0078d4; color: #fff; border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: 600; border: none; }} QPushButton:hover {{ background: #106ebe; }}")
            self.board_link_btn.setProperty("flat", False)
        else:
            self.board_link_btn.setText(_t("Definir link do Board"))
            self.board_link_btn.setToolTip(_t("Cadastrar link do board externo"))
            self.board_link_btn.setStyleSheet("")
            self.board_link_btn.setProperty("flat", True)
        self.board_link_btn.setVisible(bool(self.project_id))

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
            self._update_board_link_button()

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
                    "order": col.order,
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
                        "is_local": bool(t.is_local),
                        "labels": [
                            {"id": l.id, "name": l.name, "color": l.color}
                            for l in t.labels
                        ],
                        "epics": [
                            {"id": e.id, "name": e.name, "color": e.color}
                            for e in t.epics
                        ],
                        "linked_count": len(t.blocked_by),
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "assignee": t.assignee,
                        "comments_count": len(t.comments),
                        "can_archive": col.is_done,
                    }
                    col_data["tasks"].append(td)

                cw = ColumnWidget(col_data, self.project_id, local_flag=self.filter_bar.criar_local)
                cw.task_changed.connect(self._on_change)
                self.columns_layout.addWidget(cw)
                self._columns.append(cw)

                membros = [m.name for m in project_members(s, self.project_id)]
        finally:
            s.close()

        assignees = set(membros)
        epics: dict[int, str] = {}
        tags: set[str] = set()
        for cw in self._columns:
            for card in cw.get_cards():
                d = card.task_data
                a = d.get("assignee")
                if a:
                    assignees.add(a)
                for e in d.get("epics", []):
                    epics[e["id"]] = e["name"]
                for lbl in d.get("labels", []):
                    tags.add(lbl["name"])
        self.filter_bar.load_assignees(list(assignees))
        self.filter_bar.load_epics_tags(
            [{"id": i, "name": n} for i, n in epics.items()], sorted(tags))

        self._last_task_hash = self._compute_hash()
        self._apply_filters()
        # atualiza métricas (alertas/prazos/objetivos) sem recriar colunas
        if hasattr(self, "metrics_accordion"):
            self.metrics_accordion.refresh()
        if hasattr(self, "links_widget"):
            self.links_widget.refresh()

    def _apply_filters(self):
        search = self.filter_bar.get_search_text()
        priority_filter = self.filter_bar.get_priority_filter()
        assignee_filter = self.filter_bar.get_assignee_filter()
        epic_filter = self.filter_bar.get_epic_filter()
        tag_filter = self.filter_bar.get_tag_filter()
        origin_filter = self.filter_bar.get_origin_filter()

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

                if show and priority_filter:
                    if data.get("priority") != priority_filter:
                        show = False

                if show and epic_filter is not None:
                    if all(e.get("id") != epic_filter for e in data.get("epics", [])):
                        show = False

                if show and tag_filter is not None:
                    if all(l.get("name") != tag_filter for l in data.get("labels", [])):
                        show = False

                if show:
                    if origin_filter == "local" and not data.get("is_local"):
                        show = False
                    elif origin_filter == "remote" and data.get("is_local"):
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
