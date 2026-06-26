"""Study module GUI — list plans, plan detail with topics, create/edit."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import StudyPlan, StudyTopic, get_session
from maestro_local.gui.theme import current_theme

CATEGORIES = [
    ("LINGUAGEM", "Linguagem"),
    ("FRAMEWORK", "Framework"),
    ("CERTIFICACAO", "Certificacao"),
    ("CONCEITO", "Conceito"),
    ("CURSO", "Curso"),
    ("LIVRO", "Livro"),
]

PLAN_STATUSES = [
    ("PLANEJADO", "Planejado"),
    ("EM_ANDAMENTO", "Em andamento"),
    ("PAUSADO", "Pausado"),
    ("CONCLUIDO", "Concluido"),
    ("ABANDONADO", "Abandonado"),
]

TOPIC_STATUSES = [
    ("PENDENTE", "Pendente"),
    ("ESTUDANDO", "Estudando"),
    ("REVISAO", "Revisao"),
    ("CONCLUIDO", "Concluido"),
    ("PULADO", "Pulado"),
]


def _status_color(status, t):
    colors = {
        "PLANEJADO": t.text_muted, "EM_ANDAMENTO": t.accent,
        "PAUSADO": t.warning, "CONCLUIDO": t.success, "ABANDONADO": t.text_muted,
        "PENDENTE": t.text_muted, "ESTUDANDO": t.accent,
        "REVISAO": t.warning, "CONCLUIDO": t.success, "PULADO": t.text_muted,
    }
    return colors.get(status, t.text_muted)


def _label_for(value, options):
    for v, label in options:
        if v == value:
            return label
    return value


class StudyPlanCard(QFrame):
    open_clicked = Signal(int)
    delete_clicked = Signal(int)

    def __init__(self, plan_id, title, category, status, progress, done, total, theme):
        super().__init__()
        t = theme
        self.setStyleSheet(
            f"StudyPlanCard {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-radius: 10px; }}"
            f"StudyPlanCard:hover {{ border-color: {t.accent}; }}"
        )
        self.setMinimumHeight(80)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"background: {_status_color(status, t)}; border-radius: 4px 0 0 4px;")
        outer.addWidget(accent)

        content = QVBoxLayout()
        content.setContentsMargins(16, 12, 16, 12)
        content.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)
        name_lbl = QLabel(title)
        name_lbl.setStyleSheet(f"font-weight: 700; font-size: 15px; color: {t.text_primary}; border: none;")
        top.addWidget(name_lbl, 1)
        status_lbl = QLabel(_label_for(status, PLAN_STATUSES))
        sc = _status_color(status, t)
        status_lbl.setStyleSheet(
            f"background: {t.bg_badge}; color: {sc}; padding: 2px 8px; "
            f"border-radius: 4px; font-size: 11px; font-weight: 600; border: none;"
        )
        top.addWidget(status_lbl)
        content.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        cat_lbl = QLabel(_label_for(category, CATEGORIES))
        cat_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; border: none;")
        bottom.addWidget(cat_lbl)
        bar = QProgressBar()
        bar.setValue(progress)
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        bar.setMaximumWidth(100)
        bottom.addWidget(bar)
        pct_lbl = QLabel(f"{progress}%  ({done}/{total})")
        pct_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        bottom.addWidget(pct_lbl)
        bottom.addStretch()

        open_btn = QPushButton("Abrir")
        open_btn.setFixedHeight(28)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(
            f"QPushButton {{ background: {t.accent}; color: {t.text_on_accent}; "
            f"border-radius: 6px; padding: 4px 14px; font-size: 12px; font-weight: 600; border: none; }}"
            f"QPushButton:hover {{ background: {t.accent_hover}; }}"
        )
        open_btn.clicked.connect(lambda: self.open_clicked.emit(plan_id))
        bottom.addWidget(open_btn)

        del_btn = QPushButton("Excluir")
        del_btn.setFixedHeight(28)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {t.danger}; "
            f"border: none; padding: 4px 10px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; }}"
        )
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(plan_id))
        bottom.addWidget(del_btn)
        content.addLayout(bottom)
        outer.addLayout(content, 1)


class TopicRow(QFrame):
    status_changed = Signal(int, str)
    delete_clicked = Signal(int)

    def __init__(self, topic_id, title, status, weight, estimate_hours, logged_hours, theme):
        super().__init__()
        t = theme
        self.topic_id = topic_id
        self.setStyleSheet(
            f"TopicRow {{ background: {t.bg_input}; border: 1px solid {t.border_light}; "
            f"border-radius: 8px; }}"
        )
        self.setMinimumHeight(50)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.status_combo = QComboBox()
        for val, label in TOPIC_STATUSES:
            self.status_combo.addItem(label, val)
        idx = self.status_combo.findData(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.status_combo.setFixedWidth(110)
        self.status_combo.currentIndexChanged.connect(self._on_status_change)
        layout.addWidget(self.status_combo)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 13px; color: {t.text_primary}; border: none;")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl, 1)

        if estimate_hours:
            hrs_lbl = QLabel(f"{logged_hours:.1f}/{estimate_hours:.0f}h")
            hrs_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
            layout.addWidget(hrs_lbl)

        del_btn = QPushButton("x")
        del_btn.setFixedSize(24, 24)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {t.danger}; "
            f"border: none; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {t.bg_hover}; border-radius: 4px; }}"
        )
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.topic_id))
        layout.addWidget(del_btn)

    def _on_status_change(self):
        self.status_changed.emit(self.topic_id, self.status_combo.currentData())


class StudyView(QWidget):
    def __init__(self):
        super().__init__()
        self.current_plan_id = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.stack = QStackedWidget()
        self.list_page = self._build_list_page()
        self.stack.addWidget(self.list_page)
        self.detail_page = self._build_detail_page()
        self.stack.addWidget(self.detail_page)
        outer.addWidget(self.stack)
        self.refresh()

    def _build_list_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Estudos")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        t = current_theme()
        form = QFrame()
        form.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 10px; }}"
        )
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(16, 12, 16, 12)
        form_layout.setSpacing(10)
        form_title = QLabel("Novo Plano")
        form_title.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {t.text_primary};")
        form_layout.addWidget(form_title)

        inputs = QFormLayout()
        inputs.setSpacing(8)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Ex: Aprender Rust")
        inputs.addRow("Titulo:", self.title_input)
        self.category_combo = QComboBox()
        for val, label in CATEGORIES:
            self.category_combo.addItem(label, val)
        inputs.addRow("Categoria:", self.category_combo)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Descricao breve (opcional)")
        inputs.addRow("Descricao:", self.desc_input)
        form_layout.addLayout(inputs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        create_btn = QPushButton("+ Criar Plano")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.clicked.connect(self._create_plan)
        btn_row.addWidget(create_btn)
        form_layout.addLayout(btn_row)
        layout.addWidget(form)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(f"color: {t.text_muted}; font-size: 12px;")
        layout.addWidget(self.stats_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll, 1)
        return page

    def _build_detail_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        back_btn = QPushButton("< Voltar")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self._back_to_list)
        header_row.addWidget(back_btn)
        header_row.addStretch()
        layout.addLayout(header_row)

        self.plan_title_lbl = QLabel("")
        self.plan_title_lbl.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(self.plan_title_lbl)

        prog_row = QHBoxLayout()
        prog_row.setSpacing(10)
        self.plan_progress_bar = QProgressBar()
        self.plan_progress_bar.setTextVisible(False)
        self.plan_progress_bar.setFixedHeight(8)
        prog_row.addWidget(self.plan_progress_bar, 1)
        self.plan_progress_lbl = QLabel("")
        self.plan_progress_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
        prog_row.addWidget(self.plan_progress_lbl)
        layout.addLayout(prog_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addWidget(QLabel("Status do plano:"))
        self.plan_status_combo = QComboBox()
        for val, label in PLAN_STATUSES:
            self.plan_status_combo.addItem(label, val)
        self.plan_status_combo.currentIndexChanged.connect(self._update_plan_status)
        status_row.addWidget(self.plan_status_combo)
        status_row.addStretch()
        layout.addLayout(status_row)

        topics_title = QLabel("Topicos")
        topics_title.setStyleSheet("font-size: 16px; font-weight: 600; margin-top: 12px;")
        layout.addWidget(topics_title)

        add_form = QHBoxLayout()
        add_form.setSpacing(8)
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("Titulo do topico...")
        self.topic_input.returnPressed.connect(self._add_topic)
        add_form.addWidget(self.topic_input, 1)
        self.topic_weight = QSpinBox()
        self.topic_weight.setRange(1, 10)
        self.topic_weight.setValue(1)
        self.topic_weight.setFixedWidth(60)
        self.topic_weight.setToolTip("Peso")
        add_form.addWidget(self.topic_weight)
        self.topic_hours = QSpinBox()
        self.topic_hours.setRange(0, 500)
        self.topic_hours.setValue(0)
        self.topic_hours.setFixedWidth(70)
        self.topic_hours.setSuffix("h")
        add_form.addWidget(self.topic_hours)
        add_btn = QPushButton("+ Adicionar")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_topic)
        add_form.addWidget(add_btn)
        layout.addLayout(add_form)

        self.topics_scroll = QScrollArea()
        self.topics_scroll.setWidgetResizable(True)
        self.topics_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.topics_container = QWidget()
        self.topics_layout = QVBoxLayout(self.topics_container)
        self.topics_layout.setContentsMargins(0, 0, 0, 0)
        self.topics_layout.setSpacing(8)
        self.topics_scroll.setWidget(self.topics_container)
        layout.addWidget(self.topics_scroll, 1)
        return page

    # ---- Actions ----

    def refresh(self):
        if self.current_plan_id:
            self._load_detail()
        else:
            self._load_list()

    def _load_list(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        t = current_theme()
        s = get_session()
        try:
            plans = s.query(StudyPlan).order_by(StudyPlan.updated_at.desc()).all()
            if not plans:
                empty = QLabel("Nenhum plano de estudo criado.\nCrie seu primeiro plano acima.")
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet(f"color: {t.text_muted}; font-size: 14px; padding: 40px;")
                self.cards_layout.addWidget(empty, 1)
                return
            for p in plans:
                total_w = sum(t2.weight or 1 for t2 in p.topics if t2.status != "PULADO" and t2.parent_id is None)
                done_w = sum(t2.weight or 1 for t2 in p.topics if t2.status == "CONCLUIDO" and t2.parent_id is None)
                progress = round((done_w / total_w) * 100) if total_w > 0 else 0
                not_skipped = len([t2 for t2 in p.topics if t2.status != "PULADO" and t2.parent_id is None])
                done_count = len([t2 for t2 in p.topics if t2.status == "CONCLUIDO" and t2.parent_id is None])
                card = StudyPlanCard(p.id, p.title, p.category, p.status, progress, done_count, not_skipped, t)
                card.open_clicked.connect(self._open_plan)
                card.delete_clicked.connect(self._delete_plan)
                self.cards_layout.addWidget(card)
            self.cards_layout.addStretch()
        finally:
            s.close()

    def _load_detail(self):
        if not self.current_plan_id:
            return
        s = get_session()
        try:
            p = s.query(StudyPlan).filter(StudyPlan.id == self.current_plan_id).first()
            if not p:
                self._back_to_list()
                return
            self.plan_title_lbl.setText(p.title)
            total_w = sum(t.weight or 1 for t in p.topics if t.status != "PULADO" and t.parent_id is None)
            done_w = sum(t.weight or 1 for t in p.topics if t.status == "CONCLUIDO" and t.parent_id is None)
            progress = round((done_w / total_w) * 100) if total_w > 0 else 0
            self.plan_progress_bar.setValue(progress)
            not_skipped = len([t for t in p.topics if t.status != "PULADO" and t.parent_id is None])
            done_count = len([t for t in p.topics if t.status == "CONCLUIDO" and t.parent_id is None])
            self.plan_progress_lbl.setText(f"{progress}%  ({done_count}/{not_skipped} topicos)")
            idx = self.plan_status_combo.findData(p.status)
            if idx >= 0:
                self.plan_status_combo.blockSignals(True)
                self.plan_status_combo.setCurrentIndex(idx)
                self.plan_status_combo.blockSignals(False)
            # Topics
            while self.topics_layout.count():
                item = self.topics_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            t = current_theme()
            topics = [t2 for t2 in p.topics if t2.parent_id is None]
            topics.sort(key=lambda x: x.sort_order)
            for topic in topics:
                row = TopicRow(topic.id, topic.title, topic.status, topic.weight,
                               topic.estimate_hours, topic.logged_hours, t)
                row.status_changed.connect(self._update_topic_status)
                row.delete_clicked.connect(self._delete_topic)
                self.topics_layout.addWidget(row)
            self.topics_layout.addStretch()
        finally:
            s.close()

    def _create_plan(self):
        title = self.title_input.text().strip()
        if not title:
            return
        s = get_session()
        try:
            p = StudyPlan(
                title=title,
                category=self.category_combo.currentData(),
                description=self.desc_input.text().strip() or None,
            )
            s.add(p)
            s.commit()
            self.title_input.clear()
            self.desc_input.clear()
            self.refresh()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _open_plan(self, plan_id):
        self.current_plan_id = plan_id
        self.stack.setCurrentIndex(1)
        self._load_detail()

    def _back_to_list(self):
        self.current_plan_id = None
        self.stack.setCurrentIndex(0)
        self._load_list()

    def _delete_plan(self, plan_id):
        reply = QMessageBox.question(
            self, "Confirmar exclusao",
            "Tem certeza? Todos os topicos e sessoes serao excluidos.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        s = get_session()
        try:
            p = s.query(StudyPlan).get(plan_id)
            if p:
                s.delete(p)
                s.commit()
            self.refresh()
        finally:
            s.close()

    def _add_topic(self):
        title = self.topic_input.text().strip()
        if not title or not self.current_plan_id:
            return
        s = get_session()
        try:
            max_order = s.query(StudyTopic).filter(
                StudyTopic.plan_id == self.current_plan_id,
                StudyTopic.parent_id.is_(None),
            ).count()
            topic = StudyTopic(
                plan_id=self.current_plan_id,
                title=title,
                sort_order=max_order,
                weight=float(self.topic_weight.value()),
                estimate_hours=float(self.topic_hours.value()) if self.topic_hours.value() > 0 else None,
            )
            s.add(topic)
            s.commit()
            self.topic_input.clear()
            self.topic_weight.setValue(1)
            self.topic_hours.setValue(0)
            self._load_detail()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _update_topic_status(self, topic_id, status):
        s = get_session()
        try:
            t = s.query(StudyTopic).get(topic_id)
            if t:
                t.status = status
                s.commit()
            self._load_detail()
        finally:
            s.close()

    def _delete_topic(self, topic_id):
        s = get_session()
        try:
            t = s.query(StudyTopic).get(topic_id)
            if t:
                s.delete(t)
                s.commit()
            self._load_detail()
        finally:
            s.close()

    def _update_plan_status(self):
        if not self.current_plan_id:
            return
        status = self.plan_status_combo.currentData()
        s = get_session()
        try:
            p = s.query(StudyPlan).get(self.current_plan_id)
            if p:
                p.status = status
                s.commit()
        finally:
            s.close()
