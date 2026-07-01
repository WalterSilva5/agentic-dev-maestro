"""Study module GUI — list plans, plan detail with topics, create/edit."""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import get_active_ai_provider
from maestro_local.db.models import StudyPlan, StudyTopic, get_session
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t

CATEGORIES = [
    ("LINGUAGEM", _t("Linguagem")),
    ("FRAMEWORK", _t("Framework")),
    ("CERTIFICACAO", _t("Certificação")),
    ("CONCEITO", _t("Conceito")),
    ("CURSO", _t("Curso")),
    ("LIVRO", _t("Livro")),
]

PLAN_STATUSES = [
    ("PLANEJADO", _t("Planejado")),
    ("EM_ANDAMENTO", _t("Em andamento")),
    ("PAUSADO", _t("Pausado")),
    ("CONCLUIDO", _t("Concluído")),
    ("ABANDONADO", _t("Abandonado")),
]

TOPIC_STATUSES = [
    ("PENDENTE", _t("Pendente")),
    ("ESTUDANDO", _t("Estudando")),
    ("REVISAO", _t("Revisão")),
    ("CONCLUIDO", _t("Concluído")),
    ("PULADO", _t("Pulado")),
]


class PlanTopicsWorker(QThread):
    """Extrai texto de vários arquivos e gera os tópicos do plano com IA (QThread)."""

    done = Signal(object)   # list[{title, estimate_hours}]
    failed = Signal(str)

    def __init__(self, paths, title="", category="", description="", parent=None):
        super().__init__(parent)
        self.paths = list(paths)
        self.title = title
        self.category = category
        self.description = description

    def run(self):
        try:
            import os
            from maestro_local.study.assistant import topics_from_material
            from maestro_local.study.ingest import extract_text
            chunks = []
            for path in self.paths:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                text = extract_text(data, os.path.basename(path))
                if text.strip():
                    chunks.append(f"### {os.path.basename(path)}\n{text}")
            material = "\n\n".join(chunks)
            self.done.emit(topics_from_material(
                material, title=self.title, category=self.category, description=self.description,
            ))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


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
        content.setContentsMargins(10, 8, 10, 8)
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
        pct_lbl = QLabel(_t("{progress}%  ({done}/{total})").format(progress=progress, done=done, total=total))
        pct_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        bottom.addWidget(pct_lbl)
        bottom.addStretch()

        open_btn = QPushButton(_t("Abrir"))
        open_btn.setFixedHeight(28)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(
            f"QPushButton {{ background: {t.accent}; color: {t.text_on_accent}; "
            f"border-radius: 6px; padding: 4px 14px; font-size: 12px; font-weight: 600; border: none; }}"
            f"QPushButton:hover {{ background: {t.accent_hover}; }}"
        )
        open_btn.clicked.connect(lambda: self.open_clicked.emit(plan_id))
        bottom.addWidget(open_btn)

        del_btn = QPushButton(_t("Excluir"))
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
            hrs_lbl = QLabel(_t("{logged}/{estimate}h").format(logged=f"{logged_hours:.1f}", estimate=f"{estimate_hours:.0f}"))
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
        self._assist_worker = None
        self._assist_plan_title = ""
        self._suggested_topics = []
        self._file_worker = None
        self._attached_files = []
        self._pending_plan_id = None
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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title = QLabel(_t("Estudos"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        form = QFrame()
        form.setProperty("class", "card")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(10, 8, 10, 8)
        form_layout.setSpacing(10)
        form_title = QLabel(_t("Novo Plano"))
        form_title.setProperty("class", "cardTitle")
        form_layout.addWidget(form_title)

        inputs = QFormLayout()
        inputs.setSpacing(8)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(_t("Ex: Aprender Rust"))
        inputs.addRow(_t("Título:"), self.title_input)
        self.category_combo = QComboBox()
        for val, label in CATEGORIES:
            self.category_combo.addItem(label, val)
        inputs.addRow(_t("Categoria:"), self.category_combo)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText(_t("Descrição breve (opcional)"))
        inputs.addRow(_t("Descrição:"), self.desc_input)
        form_layout.addLayout(inputs)

        btn_row = QHBoxLayout()
        self.attach_label = QLabel("")
        self.attach_label.setProperty("class", "hint")
        self.attach_label.setWordWrap(True)
        btn_row.addWidget(self.attach_label, 1)
        self.attach_btn = QPushButton(_t("📎 Anexar arquivos"))
        self.attach_btn.setProperty("flat", True)
        self.attach_btn.setCursor(Qt.PointingHandCursor)
        self.attach_btn.setToolTip(_t("Anexar ebooks/documentos (txt, pdf, docx, epub) usados como contexto"))
        self.attach_btn.clicked.connect(self._attach_files)
        btn_row.addWidget(self.attach_btn)
        self.create_btn = QPushButton(_t("+ Criar Plano"))
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self._create_plan)
        btn_row.addWidget(self.create_btn)
        form_layout.addLayout(btn_row)
        layout.addWidget(form)

        self.stats_label = QLabel("")
        self.stats_label.setProperty("class", "hint")
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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        back_btn = QPushButton(_t("< Voltar"))
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
        status_row.addWidget(QLabel(_t("Status do plano:")))
        self.plan_status_combo = QComboBox()
        for val, label in PLAN_STATUSES:
            self.plan_status_combo.addItem(label, val)
        self.plan_status_combo.currentIndexChanged.connect(self._update_plan_status)
        status_row.addWidget(self.plan_status_combo)
        status_row.addStretch()
        layout.addLayout(status_row)

        # Corpo em duas colunas: tópicos (esquerda) + assistente (direita)
        body = QHBoxLayout()
        body.setSpacing(14)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)
        topics_title = QLabel(_t("Tópicos"))
        topics_title.setStyleSheet("font-size: 16px; font-weight: 600; margin-top: 12px;")
        left_col.addWidget(topics_title)

        add_form = QHBoxLayout()
        add_form.setSpacing(8)
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText(_t("Título do tópico..."))
        self.topic_input.returnPressed.connect(self._add_topic)
        add_form.addWidget(self.topic_input, 1)
        self.topic_weight = QSpinBox()
        self.topic_weight.setRange(1, 10)
        self.topic_weight.setValue(1)
        self.topic_weight.setFixedWidth(60)
        self.topic_weight.setToolTip(_t("Peso"))
        add_form.addWidget(self.topic_weight)
        self.topic_hours = QSpinBox()
        self.topic_hours.setRange(0, 500)
        self.topic_hours.setValue(0)
        self.topic_hours.setFixedWidth(70)
        self.topic_hours.setSuffix("h")
        add_form.addWidget(self.topic_hours)
        add_btn = QPushButton(_t("+ Adicionar"))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_topic)
        add_form.addWidget(add_btn)
        left_col.addLayout(add_form)

        self.topics_scroll = QScrollArea()
        self.topics_scroll.setWidgetResizable(True)
        self.topics_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.topics_container = QWidget()
        self.topics_layout = QVBoxLayout(self.topics_container)
        self.topics_layout.setContentsMargins(0, 0, 0, 0)
        self.topics_layout.setSpacing(8)
        self.topics_scroll.setWidget(self.topics_container)
        left_col.addWidget(self.topics_scroll, 1)
        body.addLayout(left_col, 3)

        body.addWidget(self._build_assistant_panel(), 2)
        layout.addLayout(body, 1)
        return page

    # ---- Painel do assistente de estudo ----
    def _build_assistant_panel(self):
        panel = QFrame()
        panel.setProperty("class", "card")
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(8)

        title = QLabel(_t("Assistente de estudo"))
        title.setProperty("class", "cardTitle")
        v.addWidget(title)

        self.assist_hint = QLabel(_t("Escolha um tópico e clique numa ação. A IA gera sob demanda."))
        self.assist_hint.setWordWrap(True)
        self.assist_hint.setProperty("class", "hint")
        v.addWidget(self.assist_hint)

        topic_row = QHBoxLayout()
        topic_row.setSpacing(6)
        topic_row.addWidget(QLabel(_t("Tópico:")))
        self.assist_topic_combo = QComboBox()
        topic_row.addWidget(self.assist_topic_combo, 1)
        v.addLayout(topic_row)

        # Botões de ação
        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.assist_buttons = {}
        for action, label in [
            ("explain", _t("Explicar")),
            ("exercises", _t("Exercícios")),
            ("quiz", _t("Quiz")),
            ("flashcards", _t("Flashcards")),
        ]:
            b = QPushButton(label)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, a=action: self._run_assist(a))
            btns.addWidget(b)
            self.assist_buttons[action] = b
        v.addLayout(btns)

        suggest_row = QHBoxLayout()
        suggest_row.setSpacing(6)
        self.suggest_btn = QPushButton(_t("Sugerir tópicos (roadmap)"))
        self.suggest_btn.setCursor(Qt.PointingHandCursor)
        self.suggest_btn.clicked.connect(lambda: self._run_assist("suggest_topics"))
        self.assist_buttons["suggest_topics"] = self.suggest_btn
        suggest_row.addWidget(self.suggest_btn)
        self.add_suggested_btn = QPushButton(_t("+ Adicionar ao plano"))
        self.add_suggested_btn.setCursor(Qt.PointingHandCursor)
        self.add_suggested_btn.clicked.connect(self._add_suggested_topics)
        self.add_suggested_btn.setVisible(False)
        suggest_row.addWidget(self.add_suggested_btn)
        v.addLayout(suggest_row)

        # Tirar dúvida (chat livre)
        ask_row = QHBoxLayout()
        ask_row.setSpacing(6)
        self.assist_ask = QLineEdit()
        self.assist_ask.setPlaceholderText(_t("Tirar dúvida sobre o tópico..."))
        self.assist_ask.returnPressed.connect(lambda: self._run_assist("ask"))
        ask_row.addWidget(self.assist_ask, 1)
        self.assist_ask_btn = QPushButton(_t("Perguntar"))
        self.assist_ask_btn.setCursor(Qt.PointingHandCursor)
        self.assist_ask_btn.clicked.connect(lambda: self._run_assist("ask"))
        self.assist_buttons["ask"] = self.assist_ask_btn
        ask_row.addWidget(self.assist_ask_btn)
        v.addLayout(ask_row)

        self.assist_status = QLabel("")
        self.assist_status.setProperty("class", "hint")
        v.addWidget(self.assist_status)

        self.assist_output = QTextEdit()
        self.assist_output.setReadOnly(True)
        self.assist_output.setPlaceholderText(_t("A resposta da IA aparecerá aqui."))
        v.addWidget(self.assist_output, 1)

        return panel

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
                empty = QLabel(_t("Nenhum plano de estudo criado.\nCrie seu primeiro plano acima."))
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
            self.plan_progress_lbl.setText(_t("{progress}%  ({done}/{total} tópicos)").format(progress=progress, done=done_count, total=not_skipped))
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
            # Assistente: título do plano + combo de tópicos
            self._assist_plan_title = p.title
            self._populate_assist_topics([tp.title for tp in topics])
        finally:
            s.close()
        self._update_assist_enabled()

    def _populate_assist_topics(self, topic_titles):
        prev = self.assist_topic_combo.currentText() if self.assist_topic_combo.count() else ""
        self.assist_topic_combo.clear()
        self.assist_topic_combo.addItem(_t("— Plano inteiro —"), "")
        for title in topic_titles:
            self.assist_topic_combo.addItem(title, title)
        idx = self.assist_topic_combo.findText(prev)
        if idx >= 0:
            self.assist_topic_combo.setCurrentIndex(idx)

    def _update_assist_enabled(self):
        p = get_active_ai_provider()
        ready = bool(p and p.get("model"))
        for b in self.assist_buttons.values():
            b.setEnabled(ready)
        self.assist_ask.setEnabled(ready)
        if not ready:
            self.assist_hint.setText(
                _t("Configure um provedor de IA (Configurações → Provedores de IA) para usar o assistente.")
            )
        else:
            self.assist_hint.setText(_t("Escolha um tópico e clique numa ação. A IA gera sob demanda."))

    def _create_plan(self):
        title = self.title_input.text().strip()
        if not title or self._file_worker is not None:
            return
        category = self.category_combo.currentData()
        description = self.desc_input.text().strip()
        files = list(self._attached_files)

        # Cria o plano com os campos do usuário
        new_id = None
        s = get_session()
        try:
            p = StudyPlan(title=title, category=category, description=description or None)
            s.add(p)
            s.commit()
            new_id = p.id
        except Exception:
            s.rollback()
        finally:
            s.close()
        if not new_id:
            return

        # Limpa o formulário
        self.title_input.clear()
        self.desc_input.clear()
        self._attached_files = []
        self._refresh_attach_label()

        if files:
            p = get_active_ai_provider()
            if not (p and p.get("model")):
                self.stats_label.setText(
                    _t("Plano criado. Configure um provedor de IA para gerar os tópicos dos anexos.")
                )
                self._open_plan(new_id)
                return
            self._pending_plan_id = new_id
            self.stats_label.setText(
                _t("Lendo os arquivos e montando os tópicos com IA — pode levar alguns segundos.")
            )
            self.create_btn.setEnabled(False)
            self._file_worker = PlanTopicsWorker(files, title=title, category=category, description=description)
            self._file_worker.done.connect(self._on_topics)
            self._file_worker.failed.connect(self._on_topics_error)
            self._file_worker.finished.connect(
                lambda: (setattr(self, "_file_worker", None), self.create_btn.setEnabled(True))
            )
            self._file_worker.start()
            self._open_plan(new_id)
        else:
            self.refresh()

    # ---- Anexos (contexto na criação) ----
    def _attach_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, _t("Anexar ebooks/documentos"), "",
            _t("Documentos (*.txt *.md *.markdown *.pdf *.docx *.epub);;Todos (*)"),
        )
        if paths:
            self._attached_files.extend(paths)
            self._refresh_attach_label()

    def _refresh_attach_label(self):
        import os
        if not self._attached_files:
            self.attach_label.setText("")
            return
        names = ", ".join(os.path.basename(p) for p in self._attached_files)
        self.attach_label.setText(_t("Anexos ({n}): {names}").format(
            n=len(self._attached_files), names=names,
        ))

    def _on_topics(self, topics):
        topics = topics or []
        pid = self._pending_plan_id
        self._pending_plan_id = None
        if pid:
            s = get_session()
            try:
                for i, tp in enumerate(topics):
                    hours = tp.get("estimate_hours")
                    try:
                        hours = float(hours) if hours else None
                    except (TypeError, ValueError):
                        hours = None
                    s.add(StudyTopic(
                        plan_id=pid, title=(tp.get("title") or "").strip()[:200] or _t("Tópico"),
                        sort_order=i, weight=1.0, estimate_hours=hours,
                    ))
                s.commit()
            except Exception:
                s.rollback()
            finally:
                s.close()
        self.stats_label.setText(_t("Plano criado com {n} tópico(s) a partir dos anexos.").format(n=len(topics)))
        if self.current_plan_id:
            self._load_detail()
        else:
            self.refresh()

    def _on_topics_error(self, err):
        self.stats_label.setText(
            _t("Plano criado, mas falhou gerar tópicos: {error}").format(error=err)
        )

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
            self, _t("Confirmar exclusão"),
            _t("Tem certeza? Todos os tópicos e sessões serão excluídos."),
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

    # ---- Assistente de estudo ----
    def _run_assist(self, action):
        if self._assist_worker is not None:
            return  # já há uma ação em andamento
        topic = self.assist_topic_combo.currentData() or ""
        question = self.assist_ask.text().strip()
        if action == "ask" and not question:
            return
        if action in ("explain", "exercises", "quiz", "flashcards") and not topic:
            self.assist_status.setText(_t("Selecione um tópico específico para esta ação."))
            return
        from maestro_local.study.assistant import StudyAIWorker
        existing = [self.assist_topic_combo.itemData(i)
                    for i in range(1, self.assist_topic_combo.count())]
        self.add_suggested_btn.setVisible(False)
        self._set_assist_busy(True)
        labels = {
            "explain": _t("Explicando..."), "exercises": _t("Gerando exercícios..."),
            "quiz": _t("Montando quiz..."), "flashcards": _t("Gerando flashcards..."),
            "suggest_topics": _t("Sugerindo tópicos..."), "ask": _t("Pensando..."),
        }
        self.assist_status.setText(labels.get(action, _t("Processando...")))
        self._assist_worker = StudyAIWorker(
            action, topic=topic, plan=self._assist_plan_title,
            question=question, existing=[e for e in existing if e],
        )
        self._assist_worker.result.connect(self._on_assist_result)
        self._assist_worker.failed.connect(self._on_assist_error)
        self._assist_worker.finished.connect(self._on_assist_finished)
        self._assist_worker.start()

    def _on_assist_result(self, action, payload):
        if action == "suggest_topics":
            topics = payload or []
            self._suggested_topics = topics
            if not topics:
                self.assist_output.setPlainText(_t("Nenhum tópico sugerido."))
                return
            lines = [_t("Tópicos sugeridos ({n}):").format(n=len(topics)), ""]
            for tp in topics:
                h = tp.get("estimate_hours")
                lines.append(f"• {tp['title']}" + (f"  (~{h}h)" if h else ""))
            self.assist_output.setPlainText("\n".join(lines))
            self.add_suggested_btn.setVisible(True)
        else:
            self.assist_output.setMarkdown(payload or "")
        self.assist_status.setText("")

    def _on_assist_error(self, action, err):
        self.assist_status.setText(_t("Erro: {error}").format(error=err))

    def _on_assist_finished(self):
        self._assist_worker = None
        self._set_assist_busy(False)

    def _set_assist_busy(self, busy):
        ready = bool(get_active_ai_provider() and get_active_ai_provider().get("model"))
        for b in self.assist_buttons.values():
            b.setEnabled(ready and not busy)
        self.assist_ask.setEnabled(ready and not busy)

    def _add_suggested_topics(self):
        if not self._suggested_topics or not self.current_plan_id:
            return
        s = get_session()
        added = 0
        try:
            existing = {
                (t2.title or "").strip().lower()
                for t2 in s.query(StudyTopic).filter(
                    StudyTopic.plan_id == self.current_plan_id,
                    StudyTopic.parent_id.is_(None),
                ).all()
            }
            base_order = s.query(StudyTopic).filter(
                StudyTopic.plan_id == self.current_plan_id,
                StudyTopic.parent_id.is_(None),
            ).count()
            for tp in self._suggested_topics:
                title = (tp.get("title") or "").strip()
                if not title or title.lower() in existing:
                    continue
                hours = tp.get("estimate_hours")
                try:
                    hours = float(hours) if hours else None
                except (TypeError, ValueError):
                    hours = None
                s.add(StudyTopic(
                    plan_id=self.current_plan_id, title=title,
                    sort_order=base_order + added, weight=1.0, estimate_hours=hours,
                ))
                existing.add(title.lower())
                added += 1
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()
        self._suggested_topics = []
        self.add_suggested_btn.setVisible(False)
        self.assist_status.setText(_t("{n} tópico(s) adicionado(s) ao plano.").format(n=added))
        self._load_detail()

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
