from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import BoardColumn, Project, Task, get_session
from maestro_local.gui.theme import (
    PRIORITY_COLORS,
    PRIORITY_LABELS,
    TYPE_COLORS,
    TYPE_LABELS,
    current_theme,
)
from maestro_local.i18n import t as _t


class MetricCard(QFrame):
    def __init__(self, title, value, subtitle=""):
        super().__init__()
        t = current_theme()
        self.setMinimumWidth(130)
        self.setStyleSheet(
            f"background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 8px; padding: 12px;"
        )
        layout = QVBoxLayout(self)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {t.text_muted}; font-size: 10px; text-transform: uppercase; font-weight: 600;"
        )
        layout.addWidget(lbl_title)

        lbl_value = QLabel(str(value))
        lbl_value.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {t.text_primary}; letter-spacing: -0.5px;")
        layout.addWidget(lbl_value)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet(f"color: {t.text_muted}; font-size: 11px;")
            layout.addWidget(lbl_sub)


def _section_header(text, theme):
    """Create a styled section header with bottom border."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 8, 0, 0)
    layout.setSpacing(4)

    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-weight: 600; font-size: 14px; color: {theme.text_primary};"
    )
    layout.addWidget(lbl)

    separator = QFrame()
    separator.setFixedHeight(1)
    separator.setStyleSheet(f"background: {theme.border_light};")
    layout.addWidget(separator)

    return container


class MetricsView(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(10)

        title = QLabel(_t("Métricas"))
        title.setObjectName("sectionTitle")
        self.main_layout.addWidget(title)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        scroll.setWidget(self.content)
        self.main_layout.addWidget(scroll, 1)

        self.refresh()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def refresh(self):
        self._clear_layout(self.content_layout)

        t = current_theme()
        s = get_session()
        try:
            now = datetime.utcnow()
            seven_ago = now - timedelta(days=7)
            thirty_ago = now - timedelta(days=30)

            tasks = s.query(Task).filter(Task.deleted_at == None).all()  # noqa: E711
            total = len(tasks)

            # Empty state
            if total == 0:
                empty_w = QWidget()
                empty_l = QVBoxLayout(empty_w)
                empty_l.setAlignment(Qt.AlignCenter)
                empty_l.setSpacing(8)

                empty_title = QLabel(_t("Nenhuma tarefa encontrada"))
                empty_title.setAlignment(Qt.AlignCenter)
                empty_title.setStyleSheet(
                    f"color: {t.text_muted}; font-size: 16px; font-weight: 600;"
                )
                empty_l.addWidget(empty_title)

                empty_sub = QLabel(_t("Crie tarefas nos seus projetos para ver métricas"))
                empty_sub.setAlignment(Qt.AlignCenter)
                empty_sub.setStyleSheet(f"color: {t.text_muted}; font-size: 13px;")
                empty_l.addWidget(empty_sub)

                self.content_layout.addWidget(empty_w, 1)
                return

            done_tasks = []
            for task in tasks:
                col = s.query(BoardColumn).get(task.column_id)
                if col and col.is_done:
                    done_tasks.append(task)

            done = len(done_tasks)
            last_7d = sum(
                1 for task in done_tasks if task.updated_at and task.updated_at >= seven_ago
            )
            last_30d = sum(
                1 for task in done_tasks if task.updated_at and task.updated_at >= thirty_ago
            )

            # Lead time
            lead_times = []
            for task in done_tasks:
                if task.updated_at and task.updated_at >= thirty_ago:
                    hours = (task.updated_at - task.created_at).total_seconds() / 3600
                    lead_times.append(hours)
            avg_lead = round(sum(lead_times) / len(lead_times), 1) if lead_times else None

            # Cycle time (same approximation as lead time for now)
            avg_cycle = avg_lead

            # Overdue tasks
            overdue = sum(
                1 for task in tasks
                if task.due_date and task.due_date < now and task not in done_tasks
            )

            def fmt_hours(h):
                if h is None:
                    return "--"
                if h < 1:
                    return _t("{value} min").format(value=int(h * 60))
                if h < 24:
                    return _t("{value} h").format(value=round(h, 1))
                return _t("{value} dias").format(value=round(h / 24, 1))

            # ---- Summary section ----
            self.content_layout.addWidget(_section_header(_t("Resumo"), t))

            cards_scroll = QScrollArea()
            cards_scroll.setWidgetResizable(False)
            cards_scroll.setFixedHeight(110)
            cards_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            cards_widget = QWidget()
            cards_row = QHBoxLayout(cards_widget)
            cards_row.setContentsMargins(0, 0, 0, 0)
            cards_row.setSpacing(8)
            cards_row.addWidget(MetricCard(_t("Total de Tarefas"), total, _t("{done} concluídas").format(done=done)))
            cards_row.addWidget(MetricCard(_t("Últimos 7 dias"), last_7d, _t("tarefas concluídas")))
            cards_row.addWidget(
                MetricCard(_t("Lead Time Médio"), fmt_hours(avg_lead), _t("criação -> conclusão"))
            )
            cards_row.addWidget(MetricCard(_t("Últimos 30 dias"), last_30d, _t("tarefas concluídas")))
            cards_row.addWidget(
                MetricCard(_t("Cycle Time"), fmt_hours(avg_cycle), _t("início -> conclusão"))
            )
            cards_widget.adjustSize()
            cards_scroll.setWidget(cards_widget)
            self.content_layout.addWidget(cards_scroll)

            # Overdue card (only if there are overdue tasks)
            if overdue > 0:
                overdue_card = QFrame()
                overdue_card.setStyleSheet(
                    f"background: {t.bg_card}; border: 1px solid {t.danger}; "
                    f"border-radius: 6px; padding: 12px 16px;"
                )
                oc_layout = QHBoxLayout(overdue_card)
                oc_layout.setSpacing(12)

                oc_icon = QLabel("!")
                oc_icon.setFixedSize(28, 28)
                oc_icon.setAlignment(Qt.AlignCenter)
                oc_icon.setStyleSheet(
                    f"background: {t.danger}; color: {t.text_on_accent}; "
                    f"border-radius: 14px; font-weight: bold; font-size: 14px;"
                )
                oc_layout.addWidget(oc_icon)

                oc_text = QLabel(
                    _t("{count} tarefas com prazo vencido").format(count=overdue)
                    if overdue != 1
                    else _t("{count} tarefa com prazo vencido").format(count=overdue)
                )
                oc_text.setStyleSheet(f"color: {t.danger}; font-weight: 600; font-size: 13px;")
                oc_layout.addWidget(oc_text, 1)

                self.content_layout.addWidget(overdue_card)

            # ---- Weekly Throughput section ----
            self.content_layout.addWidget(_section_header(_t("Throughput Semanal"), t))

            throughput_frame = QFrame()
            card_style = (
                f"background: {t.bg_card}; border: 1px solid {t.border_light}; "
                f"border-radius: 10px; padding: 18px;"
            )
            throughput_frame.setStyleSheet(card_style)
            throughput_layout = QVBoxLayout(throughput_frame)
            throughput_layout.setSpacing(6)

            weeks = []
            for i in range(7, -1, -1):
                week_start = now - timedelta(days=now.weekday() + 7 * i)
                week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                week_end = week_start + timedelta(days=7)
                count = sum(
                    1 for task in done_tasks
                    if task.updated_at and week_start <= task.updated_at < week_end
                )
                weeks.append((week_start, count))

            max_val = max((w[1] for w in weeks), default=1) or 1
            for week_start, count in weeks:
                row = QHBoxLayout()
                row.setSpacing(8)

                date_lbl = QLabel(week_start.strftime("%d/%m"))
                date_lbl.setFixedWidth(50)
                date_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px;")
                row.addWidget(date_lbl)

                bar = QProgressBar()
                bar.setMaximum(max_val)
                bar.setValue(count)
                bar.setTextVisible(False)
                bar.setFixedHeight(16)
                row.addWidget(bar, 1)

                count_lbl = QLabel(str(count))
                count_lbl.setFixedWidth(30)
                count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                count_lbl.setStyleSheet(f"color: {t.text_secondary}; font-weight: 600;")
                row.addWidget(count_lbl)

                throughput_layout.addLayout(row)

            self.content_layout.addWidget(throughput_frame)

            # ---- By Type section ----
            self.content_layout.addWidget(_section_header(_t("Por Tipo"), t))

            type_group = QFrame()
            type_group.setStyleSheet(card_style)
            tg_layout = QVBoxLayout(type_group)
            tg_layout.setSpacing(6)

            by_type = {}
            for task in tasks:
                tp = task.type or "FEATURE"
                if tp not in by_type:
                    by_type[tp] = {"total": 0, "done": 0}
                by_type[tp]["total"] += 1
                if task in done_tasks:
                    by_type[tp]["done"] += 1

            for tp, data in by_type.items():
                row = QHBoxLayout()
                row.setSpacing(8)
                dot = QLabel()
                dot.setFixedSize(12, 12)
                dot.setStyleSheet(
                    f"background: {TYPE_COLORS.get(tp, '#868E96')}; border-radius: 6px;"
                )
                row.addWidget(dot)
                type_lbl = QLabel(TYPE_LABELS.get(tp, tp))
                type_lbl.setStyleSheet(f"color: {t.text_primary};")
                row.addWidget(type_lbl, 1)
                stats = QLabel(f"{data['done']}/{data['total']}")
                stats.setStyleSheet(f"color: {t.text_muted};")
                row.addWidget(stats)
                pct = int(data["done"] / data["total"] * 100) if data["total"] else 0
                pct_lbl = QLabel(f"{pct}%")
                pct_lbl.setStyleSheet(f"color: {t.text_secondary}; font-weight: 600;")
                row.addWidget(pct_lbl)
                tg_layout.addLayout(row)

            self.content_layout.addWidget(type_group)

            # ---- By Priority section ----
            self.content_layout.addWidget(_section_header(_t("Por Prioridade"), t))

            prio_group = QFrame()
            prio_group.setStyleSheet(card_style)
            prio_layout = QVBoxLayout(prio_group)
            prio_layout.setSpacing(6)

            by_priority = {}
            for task in tasks:
                pr = task.priority or "MEDIUM"
                if pr not in by_priority:
                    by_priority[pr] = {"total": 0, "done": 0}
                by_priority[pr]["total"] += 1
                if task in done_tasks:
                    by_priority[pr]["done"] += 1

            # Display in defined order
            prio_order = ["URGENT", "HIGH", "MEDIUM", "LOW"]
            for pr in prio_order:
                if pr not in by_priority:
                    continue
                data = by_priority[pr]
                row = QHBoxLayout()
                row.setSpacing(8)
                dot = QLabel()
                dot.setFixedSize(12, 12)
                dot.setStyleSheet(
                    f"background: {PRIORITY_COLORS.get(pr, '#868E96')}; border-radius: 6px;"
                )
                row.addWidget(dot)
                prio_lbl = QLabel(PRIORITY_LABELS.get(pr, pr))
                prio_lbl.setStyleSheet(f"color: {t.text_primary};")
                row.addWidget(prio_lbl, 1)
                stats = QLabel(f"{data['done']}/{data['total']}")
                stats.setStyleSheet(f"color: {t.text_muted};")
                row.addWidget(stats)
                pct = int(data["done"] / data["total"] * 100) if data["total"] else 0
                pct_lbl = QLabel(f"{pct}%")
                pct_lbl.setStyleSheet(f"color: {t.text_secondary}; font-weight: 600;")
                row.addWidget(pct_lbl)
                prio_layout.addLayout(row)

            self.content_layout.addWidget(prio_group)

            # ---- By Project section ----
            self.content_layout.addWidget(_section_header(_t("Por Projeto"), t))

            proj_group = QFrame()
            proj_group.setStyleSheet(card_style)
            pg_layout = QVBoxLayout(proj_group)
            pg_layout.setSpacing(6)

            projects = s.query(Project).order_by(Project.name).all()
            for p in projects:
                ptasks = [task for task in tasks if task.project_id == p.id]
                pdone = [task for task in ptasks if task in done_tasks]
                ptotal = len(ptasks)
                pct = int(len(pdone) / ptotal * 100) if ptotal else 0

                row = QHBoxLayout()
                row.setSpacing(8)
                key = QLabel(p.key)
                key.setStyleSheet(
                    f"background: {t.bg_badge}; color: {t.text_secondary}; "
                    f"padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 11px;"
                )
                key.setFixedWidth(50)
                row.addWidget(key)
                name_lbl = QLabel(p.name)
                name_lbl.setStyleSheet(f"color: {t.text_primary};")
                row.addWidget(name_lbl, 1)
                count_lbl = QLabel(f"{len(pdone)}/{ptotal}")
                count_lbl.setStyleSheet(f"color: {t.text_muted};")
                row.addWidget(count_lbl)

                bar = QProgressBar()
                bar.setValue(pct)
                bar.setTextVisible(False)
                bar.setFixedHeight(6)
                bar.setFixedWidth(100)
                row.addWidget(bar)

                pg_layout.addLayout(row)

            self.content_layout.addWidget(proj_group)
            self.content_layout.addStretch()
        finally:
            s.close()
