"""Transcrições: grava reuniões/estudos, transcreve e resume com IA."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import (
    get_active_ai_provider,
    get_active_workspace_id,
    list_workspaces,
    load_config,
    set_active_workspace,
)
from maestro_local.transcricoes import audio as audio_backend
from maestro_local.transcricoes.constants import (
    LIVE_AI_MIN_SECONDS,
    LIVE_AI_MIN_WORDS,
    LIVE_DEFAULT_MODEL,
    WHISPER_DEFAULT_LANGUAGE,
    WHISPER_DEFAULT_MODEL,
)
from maestro_local.db.models import (
    DATA_DIR,
    BoardColumn,
    Project,
    Recording,
    Task,
    get_session,
)
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t


def _whisper_settings():
    cfg = load_config().get("settings", {}).get("transcricoes", {})
    return (
        cfg.get("whisper_model", WHISPER_DEFAULT_MODEL),
        cfg.get("whisper_language", WHISPER_DEFAULT_LANGUAGE),
    )


def _recordings_dir() -> Path:
    return DATA_DIR / "workspaces" / get_active_workspace_id() / "recordings"


class AnalyzeWorker(QThread):
    done = Signal(object)   # (markdown, summary_dict, title, tags, duration, language)
    failed = Signal(str)

    def __init__(self, kind, transcript, topic, duration, language):
        super().__init__()
        self.kind = kind
        self.transcript = transcript
        self.topic = topic
        self.duration = duration
        self.language = language

    def run(self):
        try:
            from maestro_local.transcricoes import assistants, markdown_gen
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            if self.kind == "study":
                notes = assistants.analyze_study(self.transcript, self.topic, self.duration)
                md = markdown_gen.study_to_markdown(notes, date_str)
                summary = {
                    "topic": notes.topic, "summary": notes.summary,
                    "key_concepts": [c.__dict__ for c in notes.key_concepts],
                    "exercises": [e.__dict__ for e in notes.practical_exercises],
                }
                self.done.emit((md, summary, notes.topic or t("Estudo"), notes.tags, self.duration, self.language))
            else:
                s = assistants.analyze_meeting(self.transcript, self.duration, self.language)
                md = markdown_gen.meeting_to_markdown(s, date_str)
                summary = {
                    "title": s.title, "key_points": s.key_points,
                    "decisions": s.decisions,
                    "action_items": [a.__dict__ for a in s.action_items],
                }
                self.done.emit((md, summary, s.title or t("Reunião"), s.tags, self.duration, self.language))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class _QACard(QFrame):
    """Card de pergunta+resposta da reunião. Duplo-clique alterna resolvida."""
    toggled = Signal(int)

    def __init__(self, index: int, question: str, answer: str, resolved: bool, theme):
        super().__init__()
        self._index = index
        self.setToolTip(t("Duplo-clique para marcar como resolvida / reabrir."))
        border = theme.success if resolved else theme.border
        self.setStyleSheet(
            f"_QACard {{ background: {theme.bg_card}; border: 1px solid {border}; "
            f"border-left: 4px solid {theme.success if resolved else theme.accent}; "
            f"border-radius: 8px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        q = QLabel(("✅ " if resolved else "❓ ") + question)
        q.setWordWrap(True)
        q.setStyleSheet(
            f"font-weight: 700; font-size: 13px; color: {theme.text_primary}; "
            f"border: none; background: transparent;")
        lay.addWidget(q)

        if answer:
            a = QLabel("↳ " + answer)
            a.setWordWrap(True)
            a.setTextInteractionFlags(Qt.TextSelectableByMouse)
            a.setStyleSheet(
                f"color: {theme.text_secondary}; font-size: 12px; border: none; "
                f"background: {theme.bg_badge}; border-radius: 6px; padding: 6px 8px;")
            lay.addWidget(a)
        elif not resolved:
            pend = QLabel(t("(aguardando resposta)"))
            pend.setStyleSheet(
                f"color: {theme.text_muted}; font-size: 11px; font-style: italic; "
                f"border: none; background: transparent;")
            lay.addWidget(pend)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self.toggled.emit(self._index)
        super().mouseDoubleClickEvent(event)


class TranscricoesView(QWidget):
    # Emitido quando o usuário troca o workspace pela própria tela de reuniões;
    # a janela principal faz a troca de banco + refresh geral.
    workspace_change_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self._session = None
        self._loading_ws = False
        self._transcriber = None
        self._analyzer = None
        self._elapsed = 0
        self._current = {"transcript": "", "duration": 0.0, "language": "", "audio_path": ""}

        # Estado do assistente ao vivo
        self._live_transcriber = None
        self._live_extractor = None
        self._live_asker = None
        self._analyze_extractor = None
        self._live_transcript = ""       # transcrição ao vivo acumulada
        self._live_pending = ""          # texto novo ainda não enviado à IA
        self._live_secs_since = 0        # segundos desde a última extração
        self._live_state = {"action_items": [], "decisions": [], "questions": [],
                            "plan": [], "tips": []}

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(0)
        # Splitter horizontal: histórico (esq) x conteúdo (dir), arrastável.
        self._main_split = QSplitter(Qt.Horizontal)
        self._main_split.setChildrenCollapsible(False)
        self._main_split.setHandleWidth(10)
        root.addWidget(self._main_split)

        # ---- Coluna esquerda: histórico ----
        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 8, 0)
        left.setSpacing(6)
        htitle = QLabel(t("Histórico"))
        htitle.setProperty("class", "cardTitle")
        left.addWidget(htitle)
        self.search = QLineEdit()
        self.search.setPlaceholderText(t("Buscar nas gravações..."))
        self.search.textChanged.connect(self._load_history)
        left.addWidget(self.search)
        self.history = QListWidget()
        self.history.setStyleSheet(
            "QListWidget::item { padding: 8px 6px; min-height: 34px; "
            "border-bottom: 1px solid rgba(128,128,128,0.15); }"
        )
        self.history.itemClicked.connect(self._open_recording)
        left.addWidget(self.history, 1)
        left_widget.setMinimumWidth(200)
        left_widget.setMaximumWidth(420)
        self._main_split.addWidget(left_widget)

        # ---- Coluna direita: gravação + transcrição ----
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(8, 0, 0, 0)
        right.setSpacing(10)

        title = QLabel(t("Reuniões"))
        title.setObjectName("sectionTitle")
        right.addWidget(title)

        subtitle = QLabel(
            t("Grave reuniões e estudos, transcreva localmente com Whisper e gere "
              "resumos estruturados com IA.")
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")
        right.addWidget(subtitle)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setVisible(False)
        right.addWidget(self.banner)

        # Controles de gravação
        ctrl = QFrame()
        ctrl.setProperty("class", "card")
        cl = QVBoxLayout(ctrl)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(QLabel(t("Tipo:")))
        self.kind_combo = QComboBox()
        self.kind_combo.addItem(t("Reunião"), "meeting")
        self.kind_combo.addItem(t("Estudo"), "study")
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        row1.addWidget(self.kind_combo)
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText(t("Tópico do estudo"))
        self.topic_input.setVisible(False)
        row1.addWidget(self.topic_input, 1)
        cl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(QLabel(t("Microfone:")))
        self.mic_combo = QComboBox()
        row2.addWidget(self.mic_combo, 1)
        cl.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(8)
        row3.addWidget(QLabel(t("Áudio do sistema:")))
        self.monitor_combo = QComboBox()
        row3.addWidget(self.monitor_combo, 1)
        cl.addLayout(row3)

        row4 = QHBoxLayout()
        row4.setSpacing(8)
        self.record_btn = QPushButton(t("● Gravar e transcrever"))
        self.record_btn.setFixedHeight(34)
        self.record_btn.setCursor(Qt.PointingHandCursor)
        self.record_btn.clicked.connect(self._toggle_record)
        row4.addWidget(self.record_btn)
        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-family: monospace; font-size: 16px;")
        row4.addWidget(self.timer_label)
        row4.addStretch()
        self.live_check = QCheckBox(t("Assistente ao vivo"))
        self.live_check.setToolTip(
            t("Transcreve e extrai ações/decisões durante a gravação (mais uso de CPU/IA). "
              "Pode ser ligado/desligado a qualquer momento, inclusive no meio da gravação.")
        )
        self.live_check.toggled.connect(self._on_live_toggled)
        row4.addWidget(self.live_check)
        cl.addLayout(row4)

        right.addWidget(ctrl)

        # ---- Painel do assistente ao vivo (visível só durante gravação ao vivo) ----
        self.live_box = self._build_live_box()
        self.live_box.setVisible(False)
        right.addWidget(self.live_box, 6)

        # Progresso de transcrição
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        right.addWidget(self.status_label)

        # Transcrição
        self.transcript_label = QLabel(t("Transcrição:"))
        right.addWidget(self.transcript_label)
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText(t("A transcrição aparecerá aqui..."))
        right.addWidget(self.transcript_edit, 1)

        # Ações — linha 1: documento da reunião
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.analyze_btn = QPushButton(t("Analisar com IA"))
        self.analyze_btn.setFixedHeight(32)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._analyze)
        actions.addWidget(self.analyze_btn)
        self.save_day_btn = QPushButton(t("Salvar no Meu Dia"))
        self.save_day_btn.setProperty("flat", "true")
        self.save_day_btn.setFixedHeight(32)
        self.save_day_btn.setCursor(Qt.PointingHandCursor)
        self.save_day_btn.clicked.connect(self._save_to_day)
        self.save_day_btn.setEnabled(False)
        actions.addWidget(self.save_day_btn)
        self.export_btn = QPushButton(t("Exportar (.md)"))
        self.export_btn.setProperty("flat", "true")
        self.export_btn.setFixedHeight(32)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setToolTip(t("Exporta um markdown único com todos os itens de todas as abas + transcrição."))
        self.export_btn.clicked.connect(self._export_markdown)
        actions.addWidget(self.export_btn)
        self.copy_btn = QPushButton(t("Copiar (.md)"))
        self.copy_btn.setProperty("flat", "true")
        self.copy_btn.setFixedHeight(32)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setToolTip(t("Copia o markdown completo da reunião para a área de transferência."))
        self.copy_btn.clicked.connect(self._copy_markdown)
        actions.addWidget(self.copy_btn)
        actions.addStretch()
        right.addLayout(actions)

        # Ações — linha 2: ponte para o board
        actions2 = QHBoxLayout()
        actions2.setSpacing(8)
        actions2.addStretch()
        actions2.addWidget(QLabel(t("Workspace:")))
        self.ws_combo = QComboBox()
        self.ws_combo.setMinimumWidth(140)
        self.ws_combo.setToolTip(
            t("Workspace de destino da reunião. Troque aqui caso esteja gravando para o workspace errado.")
        )
        self.ws_combo.currentIndexChanged.connect(self._on_ws_combo_changed)
        actions2.addWidget(self.ws_combo)
        actions2.addWidget(QLabel(t("Projeto:")))
        self.proj_combo = QComboBox()
        self.proj_combo.setMinimumWidth(160)
        actions2.addWidget(self.proj_combo)
        self.tasks_btn = QPushButton(t("Criar tarefas das ações"))
        self.tasks_btn.setFixedHeight(32)
        self.tasks_btn.setCursor(Qt.PointingHandCursor)
        self.tasks_btn.clicked.connect(self._actions_to_tasks)
        actions2.addWidget(self.tasks_btn)
        right.addLayout(actions2)

        # Resultado markdown
        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText(t("O resumo estruturado aparecerá aqui após a análise."))
        self.result_edit.setVisible(False)
        right.addWidget(self.result_edit, 1)

        self._main_split.addWidget(right_widget)
        self._main_split.setStretchFactor(0, 0)
        self._main_split.setStretchFactor(1, 1)
        self._main_split.setSizes([260, 900])

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        self._populate_devices()
        self._populate_workspaces()
        self._populate_projects()
        self._load_history()
        self._check_provider()

    def _populate_workspaces(self):
        """Preenche o seletor de workspace com o ativo selecionado (sem disparar troca)."""
        self._loading_ws = True
        try:
            self.ws_combo.clear()
            active = get_active_workspace_id()
            for ws in list_workspaces():
                self.ws_combo.addItem(ws.get("name", ws["id"]), ws["id"])
            idx = self.ws_combo.findData(active)
            if idx >= 0:
                self.ws_combo.setCurrentIndex(idx)
        finally:
            self._loading_ws = False

    def _on_ws_combo_changed(self):
        """Troca o workspace de destino da reunião a partir da própria tela.

        Move a gravação atual (se já existir) para o workspace escolhido, evitando
        que a reunião fique salva no workspace errado.
        """
        if self._loading_ws:
            return
        ws_id = self.ws_combo.currentData()
        if not ws_id or ws_id == get_active_workspace_id():
            return
        transcript = self.transcript_edit.toPlainText().strip()
        # Remove a gravação do workspace atual — será recriada no destino.
        old_rec_id = self._current.get("rec_id")
        if old_rec_id and transcript:
            s = get_session()
            try:
                rec = s.query(Recording).get(old_rec_id)
                if rec is not None:
                    s.delete(rec)
                    s.commit()
            finally:
                s.close()
        self._current["rec_id"] = None
        set_active_workspace(ws_id)
        # A janela principal troca o banco ativo e faz o refresh geral (síncrono).
        self.workspace_change_requested.emit(ws_id)
        if transcript:
            self._persist_recording()  # recria a reunião no workspace de destino
            self.status_label.setText(t("Reunião movida para o workspace selecionado."))
            self._load_history()

    def _populate_projects(self):
        current = self.proj_combo.currentData()
        self.proj_combo.clear()
        s = get_session()
        try:
            for p in s.query(Project).order_by(Project.name).all():
                self.proj_combo.addItem(f"{p.key} · {p.name}", p.id)
        finally:
            s.close()
        if self.proj_combo.count() == 0:
            self.proj_combo.addItem(t("(nenhum projeto)"), None)
        elif current is not None:
            idx = self.proj_combo.findData(current)
            if idx >= 0:
                self.proj_combo.setCurrentIndex(idx)

    def _check_provider(self):
        provider = get_active_ai_provider()
        theme = current_theme()
        msgs = []
        if not audio_backend.parec_available():
            msgs.append(t("⚠ parec/pactl não encontrados — gravação indisponível (instale pulseaudio-utils)."))
        if not provider or not provider.get("model"):
            msgs.append(t("⚠ Provedor de IA não configurado — a análise com IA ficará indisponível (Configurações → Provedores de IA)."))
        if msgs:
            self.banner.setText("\n".join(msgs))
            self.banner.setStyleSheet(
                f"background: {theme.bg_badge}; color: {theme.text_secondary}; border: 1px solid {theme.border}; "
                f"border-radius: 8px; padding: 8px 12px; font-size: 12px;"
            )
            self.banner.setVisible(True)
        else:
            self.banner.setVisible(False)
        # Botão sempre habilitado: ao clicar sem modelo, mostra orientação clara
        self.analyze_btn.setEnabled(True)

    def _populate_devices(self):
        self.mic_combo.clear()
        self.monitor_combo.clear()
        self.monitor_combo.addItem(t("Nenhum"), None)
        sources = audio_backend.list_sources()
        for s in sources:
            if s.is_monitor:
                self.monitor_combo.addItem(s.description, s.name)
            else:
                self.mic_combo.addItem(s.description, s.name)
        if self.mic_combo.count() == 0:
            self.mic_combo.addItem(t("Nenhum microfone"), None)
        # Seleciona o dispositivo de áudio do sistema padrão (monitor), em vez de
        # deixar "Nenhum", quando houver algum disponível.
        default_mon = audio_backend.default_monitor()
        if default_mon is not None:
            idx = self.monitor_combo.findData(default_mon.name)
            if idx >= 0:
                self.monitor_combo.setCurrentIndex(idx)
        default_mic = audio_backend.default_mic()
        if default_mic is not None:
            idx = self.mic_combo.findData(default_mic.name)
            if idx >= 0:
                self.mic_combo.setCurrentIndex(idx)

    def _on_kind_changed(self):
        self.topic_input.setVisible(self.kind_combo.currentData() == "study")

    # ------------------------- Painel ao vivo -------------------------
    def _make_live_list(self) -> QListWidget:
        """Lista das abas ao vivo: itens com quebra de linha, espaçados e legíveis."""
        lst = QListWidget()
        lst.setWordWrap(True)
        lst.setSpacing(4)
        lst.setUniformItemSizes(False)
        lst.setStyleSheet(
            "QListWidget { border: none; font-size: 13px; } "
            "QListWidget::item { padding: 10px 10px; min-height: 30px; "
            "border-bottom: 1px solid rgba(128,128,128,0.18); }"
        )
        return lst

    def _build_questions_panel(self) -> QWidget:
        """Painel de perguntas & respostas (cards), em vez de lista simples."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._questions_container = QWidget()
        self._questions_layout = QVBoxLayout(self._questions_container)
        self._questions_layout.setContentsMargins(6, 6, 6, 6)
        self._questions_layout.setSpacing(8)
        self._questions_empty = QLabel(t("As perguntas levantadas na reunião aparecerão aqui — com a resposta assim que forem respondidas."))
        self._questions_empty.setWordWrap(True)
        self._questions_empty.setObjectName("subtitle")
        self._questions_layout.addWidget(self._questions_empty)
        self._questions_layout.addStretch()
        scroll.setWidget(self._questions_container)
        return scroll

    def _render_questions(self, questions: list):
        """Redesenha os cards de perguntas a partir do estado."""
        # limpa tudo menos o placeholder (idx 0) e o stretch (último)
        while self._questions_layout.count() > 2:
            item = self._questions_layout.takeAt(1)
            w = item.widget()
            if w:
                w.setParent(None)  # remove da tela imediatamente
                w.deleteLater()
        theme = current_theme()
        has_any = bool(questions)
        self._questions_empty.setVisible(not has_any)
        for i, q in enumerate(questions):
            if isinstance(q, dict):
                question = str(q.get("question") or "").strip()
                answer = str(q.get("answer") or "").strip()
                resolved = bool(q.get("resolved"))
            else:  # tolera string simples (compatibilidade)
                question, answer, resolved = str(q), "", False
            if not question:
                continue
            card = _QACard(i, question, answer, resolved, theme)
            card.toggled.connect(self._toggle_question_resolved)
            self._questions_layout.insertWidget(self._questions_layout.count() - 1, card)

    def _build_live_box(self) -> QFrame:
        box = QFrame()
        box.setProperty("class", "card")
        v = QVBoxLayout(box)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel(t("● Ao vivo"))
        title.setProperty("class", "cardTitle")
        head.addWidget(title)
        head.addStretch()
        self.live_status = QLabel("")
        self.live_status.setObjectName("subtitle")
        head.addWidget(self.live_status)
        v.addLayout(head)

        # Splitter vertical: transcrição ao vivo (topo) x abas do assistente
        # (embaixo). O usuário pode arrastar para ampliar as abas.
        split = QSplitter(Qt.Vertical)
        split.setChildrenCollapsible(False)

        trans_pane = QWidget()
        tp = QVBoxLayout(trans_pane)
        tp.setContentsMargins(0, 0, 0, 0)
        tp.setSpacing(4)
        tp.addWidget(QLabel(t("Transcrição ao vivo")))
        self.live_transcript_edit = QTextEdit()
        self.live_transcript_edit.setReadOnly(True)
        self.live_transcript_edit.setPlaceholderText(t("A transcrição aparecerá aqui em tempo real..."))
        tp.addWidget(self.live_transcript_edit)
        trans_pane.setMinimumHeight(80)
        split.addWidget(trans_pane)

        # Abas do assistente (as 5) — ampliadas e com quebra de linha nos itens
        self.live_tabs = QTabWidget()
        self.live_tabs.setMinimumHeight(320)
        self.live_plan_list = self._make_live_list()
        self.live_tips_list = self._make_live_list()
        self.live_actions_list = self._make_live_list()
        self.live_decisions_list = self._make_live_list()
        self.live_tabs.addTab(self.live_plan_list, "🗺 " + t("Plano"))
        self.live_tabs.addTab(self.live_tips_list, "💡 " + t("Dicas"))
        self.live_tabs.addTab(self.live_actions_list, "✅ " + t("Ações"))
        self.live_tabs.addTab(self.live_decisions_list, "📌 " + t("Decisões"))
        self.live_tabs.addTab(self._build_questions_panel(), "❓ " + t("Perguntas"))
        split.addWidget(self.live_tabs)

        # Prioriza as abas: transcrição menor, abas bem maiores
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 4)
        split.setSizes([120, 480])
        v.addWidget(split, 1)

        # Perguntar à reunião
        ask = QHBoxLayout()
        ask.setSpacing(8)
        self.ask_input = QLineEdit()
        self.ask_input.setPlaceholderText(t("Perguntar à reunião (ex.: o que ficou decidido sobre X?)"))
        self.ask_input.returnPressed.connect(self._ask_meeting)
        ask.addWidget(self.ask_input, 1)
        self.ask_btn = QPushButton(t("Perguntar"))
        self.ask_btn.setCursor(Qt.PointingHandCursor)
        self.ask_btn.clicked.connect(self._ask_meeting)
        ask.addWidget(self.ask_btn)
        v.addLayout(ask)

        self.ask_answer = QLabel("")
        self.ask_answer.setWordWrap(True)
        self.ask_answer.setObjectName("subtitle")
        self.ask_answer.setVisible(False)
        v.addWidget(self.ask_answer)

        return box

    # ------------------------- Gravação -------------------------
    def is_recording(self) -> bool:
        return bool(self._session and self._session.is_recording)

    def elapsed_seconds(self) -> int:
        return self._elapsed

    def toggle_record_external(self):
        """Chamado por atalho global ou pelo widget rápido (thread-safe)."""
        QTimer.singleShot(0, self._toggle_record)

    def _toggle_record(self):
        if self._session and self._session.is_recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self):
        if not audio_backend.parec_available():
            self.status_label.setText(t("parec indisponível — não é possível gravar."))
            return
        mic_name = self.mic_combo.currentData()
        mon_name = self.monitor_combo.currentData()
        mic = next((s for s in audio_backend.list_sources() if s.name == mic_name), None) if mic_name else None
        mon = next((s for s in audio_backend.list_sources() if s.name == mon_name), None) if mon_name else None
        if not mic and not mon:
            self.status_label.setText(t("Selecione ao menos uma fonte de áudio."))
            return
        try:
            self._session = audio_backend.RecordingSession(mic, mon)
            self._session.start()
        except Exception as e:  # noqa: BLE001
            self.status_label.setText(t("Erro ao iniciar gravação: {error}").format(error=e))
            self._session = None
            return
        # Nova gravação: zera o estado para criar um novo registro
        self._current = {"transcript": "", "duration": 0.0, "language": "", "audio_path": ""}
        self.result_edit.clear()
        self.result_edit.setVisible(False)
        self.save_day_btn.setEnabled(False)
        self._elapsed = 0
        self.timer_label.setText("00:00")
        self._tick.start()
        self.record_btn.setText(t("■ Parar"))
        self.status_label.setText(t("Gravando..."))
        if self.live_check.isChecked():
            self._start_live()

    def _stop_record(self):
        self._tick.stop()
        self.record_btn.setText(t("● Gravar e transcrever"))
        self._stop_live()
        if not self._session:
            return
        out = _recordings_dir() / f"rec-{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
        try:
            path, duration = self._session.stop_and_save(out)
        except Exception as e:  # noqa: BLE001
            self.status_label.setText(t("Erro ao salvar áudio: {error}").format(error=e))
            self._session = None
            return
        self._session = None
        self._current["audio_path"] = str(path)
        self._current["duration"] = duration
        self.status_label.setText(t("Gravação salva ({seconds:.0f}s). Transcrevendo...").format(seconds=duration))
        self._transcribe(path)

    def _on_tick(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self.timer_label.setText(f"{m:02d}:{s:02d}")
        if self._live_transcriber is not None:
            self._live_secs_since += 1
            self._maybe_extract_live()

    # ------------------------- Assistente ao vivo -------------------------
    def _provider_ready(self) -> bool:
        p = get_active_ai_provider()
        return bool(p and p.get("model"))

    def _on_live_toggled(self, on: bool):
        """Liga/desliga o assistente ao vivo a qualquer momento. Se já está
        gravando, ativa/desativa na hora; senão, é só preferência para a
        próxima gravação."""
        if not self.is_recording():
            return
        if on:
            if self._live_transcriber is None:
                self._start_live()
        else:
            self._stop_live()
            self.live_box.setVisible(False)

    def _start_live(self):
        from maestro_local.transcricoes.transcriber import LiveTranscriber
        _, lang = _whisper_settings()
        # Reseta o estado ao vivo
        self._live_transcript = ""
        self._live_pending = ""
        self._live_secs_since = 0
        self._live_state = {
            "action_items": [], "decisions": [], "questions": [], "plan": [], "tips": [],
        }
        self._live_context = self._meeting_context()
        self.live_transcript_edit.clear()
        self.live_plan_list.clear()
        self.live_tips_list.clear()
        self.live_actions_list.clear()
        self.live_decisions_list.clear()
        self._render_questions([])
        self.ask_answer.setVisible(False)
        self.live_box.setVisible(True)
        # Dá o palco ao painel ao vivo: esconde transcrição estática e resumo
        # (que só interessam depois da gravação).
        self.transcript_label.setVisible(False)
        self.transcript_edit.setVisible(False)
        self.result_edit.setVisible(False)
        ai_ok = self._provider_ready()
        self.ask_input.setEnabled(ai_ok)
        self.ask_btn.setEnabled(ai_ok)
        self.live_status.setText(
            t("Transcrevendo ao vivo...") if ai_ok
            else t("Transcrevendo ao vivo (sem IA — configure um provedor para extrair ações).")
        )
        self._live_transcriber = LiveTranscriber(self._session, LIVE_DEFAULT_MODEL, lang)
        self._live_transcriber.partial.connect(self._on_live_partial)
        self._live_transcriber.status.connect(self.live_status.setText)
        self._live_transcriber.start()

    def _stop_live(self):
        if self._live_transcriber is not None:
            self._live_transcriber.stop()
            self._live_transcriber.wait(3000)
            self._live_transcriber = None
        # Restaura a transcrição estática para revisar/analisar o resultado final.
        self.transcript_label.setVisible(True)
        self.transcript_edit.setVisible(True)
        if self.live_box.isVisible():
            self.live_status.setText(t("Sessão ao vivo encerrada."))

    def _on_live_partial(self, text: str):
        text = text.strip()
        if not text:
            return
        self._live_transcript = (self._live_transcript + " " + text).strip()
        self._live_pending = (self._live_pending + " " + text).strip()
        self.live_transcript_edit.append(text)
        sb = self.live_transcript_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _maybe_extract_live(self):
        if self._live_extractor is not None:  # já tem uma extração em curso
            return
        if not self._live_pending.strip() or not self._provider_ready():
            return
        words = len(self._live_pending.split())
        if words < LIVE_AI_MIN_WORDS and self._live_secs_since < LIVE_AI_MIN_SECONDS:
            return
        self._start_live_extract()

    def _start_live_extract(self):
        from maestro_local.transcricoes.live_assistant import LiveExtractWorker
        new_text = self._live_pending
        self._live_pending = ""
        self._live_secs_since = 0
        self._live_extractor = LiveExtractWorker(
            dict(self._live_state), new_text, context=getattr(self, "_live_context", ""),
        )
        self._live_extractor.done.connect(self._on_live_extracted)
        self._live_extractor.failed.connect(self._on_live_extract_error)
        self._live_extractor.start()

    def _on_live_extracted(self, state: dict):
        self._live_extractor = None
        self._live_state = state
        self._refresh_live_panels()
        if self._live_transcriber is not None:
            self.live_status.setText(t("Transcrevendo ao vivo..."))

    def _on_live_extract_error(self, err: str):
        self._live_extractor = None
        self.live_status.setText(t("IA ao vivo indisponível: {error}").format(error=err))

    def _refresh_live_panels(self):
        self.live_plan_list.clear()
        for i, step in enumerate(self._live_state.get("plan", []), 1):
            self.live_plan_list.addItem(f"{i}. {step}")
        self.live_tips_list.clear()
        for tip in self._live_state.get("tips", []):
            self.live_tips_list.addItem(f"💡 {tip}")
        self.live_actions_list.clear()
        for a in self._live_state.get("action_items", []):
            desc = a.get("description", "") if isinstance(a, dict) else str(a)
            who = a.get("assignee") if isinstance(a, dict) else None
            self.live_actions_list.addItem(f"• {desc}" + (f"  — {who}" if who else ""))
        self.live_decisions_list.clear()
        for d in self._live_state.get("decisions", []):
            self.live_decisions_list.addItem(f"✓ {d}")
        questions = self._live_state.get("questions", [])
        self._render_questions(questions)
        open_count = sum(
            1 for q in questions
            if not (q.get("resolved") if isinstance(q, dict) else False))

        def _tab(idx, label, n):
            self.live_tabs.setTabText(idx, t(label) + (f" ({n})" if n else ""))

        _tab(0, "🗺 Plano", self.live_plan_list.count())
        _tab(1, "💡 Dicas", self.live_tips_list.count())
        _tab(2, "✅ Ações", self.live_actions_list.count())
        _tab(3, "📌 Decisões", self.live_decisions_list.count())
        # Perguntas: conta só as em aberto (as resolvidas mostram a resposta)
        _tab(4, "❓ Perguntas", open_count)

    def _toggle_question_resolved(self, index):
        """Alterna a pergunta de índice `index` entre resolvida e em aberto."""
        questions = self._live_state.get("questions", [])
        if not (0 <= index < len(questions)):
            return
        q = questions[index]
        if isinstance(q, dict):
            q["resolved"] = not q.get("resolved")
        else:  # normaliza string para dict
            questions[index] = {"question": str(q), "answer": "", "resolved": True}
        self._refresh_live_panels()

    def _ask_meeting(self):
        question = self.ask_input.text().strip()
        if not question:
            return
        if not self._provider_ready():
            self.ask_answer.setVisible(True)
            self.ask_answer.setText(t("Configure um provedor de IA para perguntar à reunião."))
            return
        if not self._live_transcript.strip():
            self.ask_answer.setVisible(True)
            self.ask_answer.setText(t("Ainda não há transcrição suficiente."))
            return
        from maestro_local.transcricoes.live_assistant import LiveAskWorker
        self.ask_btn.setEnabled(False)
        self.ask_answer.setVisible(True)
        self.ask_answer.setText(t("Pensando..."))
        self._live_asker = LiveAskWorker(
            self._live_transcript, question, context=getattr(self, "_live_context", "") or self._meeting_context(),
        )
        self._live_asker.answered.connect(self._on_ask_answered)
        self._live_asker.failed.connect(self._on_ask_error)
        self._live_asker.start()

    def _on_ask_answered(self, answer: str):
        self._live_asker = None
        self.ask_btn.setEnabled(True)
        self.ask_answer.setText(answer)

    def _on_ask_error(self, err: str):
        self._live_asker = None
        self.ask_btn.setEnabled(True)
        self.ask_answer.setText(t("Erro: {error}").format(error=err))

    def _meeting_context(self) -> str:
        """Monta o contexto do workspace + projeto selecionado para o copiloto.

        Usa o projeto escolhido no seletor (o mesmo de "Criar tarefas das ações")
        e resume seus tópicos e tarefas em aberto, para o assistente alinhar plano
        e dicas ao trabalho atual.
        """
        parts = []
        try:
            from maestro_local.config import get_active_workspace_id, list_workspaces
            wid = get_active_workspace_id()
            ws = next((w for w in list_workspaces() if w.get("id") == wid), None)
            if ws and ws.get("name"):
                parts.append(t("Workspace: {name}").format(name=ws["name"]))
        except Exception:  # noqa: BLE001
            pass
        project_id = self.proj_combo.currentData()
        if project_id:
            s = get_session()
            try:
                p = s.query(Project).get(project_id)
                if p:
                    parts.append(t("Projeto atual: {name}").format(name=p.name))
                    if p.description:
                        parts.append(t("Descrição: {desc}").format(desc=p.description[:400]))
                    open_tasks = (
                        s.query(Task)
                        .filter(
                            Task.project_id == p.id,
                            Task.deleted_at == None,  # noqa: E711
                            Task.archived_at == None,  # noqa: E711
                        )
                        .order_by(Task.created_at.desc())
                        .limit(15)
                        .all()
                    )
                    titles = [f"- {tk.code} {tk.title}" for tk in open_tasks
                              if not (tk.column and tk.column.is_done)]
                    if titles:
                        parts.append(t("Tarefas em aberto:") + "\n" + "\n".join(titles[:12]))
            finally:
                s.close()
        return "\n".join(parts).strip()

    # ------------------------- Ações → tarefas -------------------------
    def _collect_action_items(self) -> list[dict]:
        """Ações do assistente ao vivo; se vazio, cai para o resumo de IA."""
        items = list(self._live_state.get("action_items", []))
        if items:
            return [i if isinstance(i, dict) else {"description": str(i)} for i in items]
        summary_json = self._current.get("summary_json")
        if summary_json:
            try:
                data = json.loads(summary_json)
                return [
                    i if isinstance(i, dict) else {"description": str(i)}
                    for i in data.get("action_items", [])
                ]
            except Exception:  # noqa: BLE001
                pass
        return []

    def _actions_to_tasks(self):
        project_id = self.proj_combo.currentData()
        if not project_id:
            self.status_label.setText(t("Selecione um projeto para criar as tarefas."))
            return
        actions = self._collect_action_items()
        if not actions:
            self.status_label.setText(t("Nenhuma ação encontrada — grave/analise ou use o assistente ao vivo."))
            return
        s = get_session()
        try:
            project = s.query(Project).get(project_id)
            if not project:
                self.status_label.setText(t("Projeto não encontrado."))
                return
            first_col = (
                s.query(BoardColumn)
                .filter(BoardColumn.project_id == project.id)
                .order_by(BoardColumn.order)
                .first()
            )
            if not first_col:
                self.status_label.setText(t("O projeto não tem colunas."))
                return
            created = 0
            src = self.topic_input.text().strip() or self._current.get("title") or t("Reunião")
            for a in actions:
                desc = (a.get("description") or "").strip()
                if not desc:
                    continue
                project.task_seq = (project.task_seq or 0) + 1
                task = Task(
                    project_id=project.id,
                    column_id=first_col.id,
                    number=project.task_seq,
                    title=desc[:255],
                    description=t("Ação de: {src}").format(src=src),
                    type="CHORE",
                    priority="MEDIUM",
                    assignee=(a.get("assignee") or None),
                    requires_human=True,
                )
                s.add(task)
                created += 1
            s.commit()
        finally:
            s.close()
        self.status_label.setText(
            t("{count} tarefa(s) criada(s) em {project}.").format(
                count=created, project=self.proj_combo.currentText()
            )
        )

    # ------------------------- Transcrição -------------------------
    def _transcribe(self, audio_path: Path):
        from maestro_local.transcricoes.transcriber import TranscriberWorker
        model, lang = _whisper_settings()
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.transcript_edit.clear()
        self._transcriber = TranscriberWorker(audio_path, model, lang)
        self._transcriber.progress.connect(self.progress.setValue)
        self._transcriber.finished_ok.connect(self._on_transcribed)
        self._transcriber.finished_error.connect(self._on_transcribe_error)
        self._transcriber.start()

    def _on_transcribed(self, result):
        self.progress.setVisible(False)
        self._current["transcript"] = result.text
        self._current["language"] = result.language
        self._current["duration"] = result.duration or self._current["duration"]
        self.transcript_edit.setPlainText(result.text)
        # Permite salvar/enviar ao Meu Dia mesmo sem análise de IA
        self.save_day_btn.setEnabled(bool(result.text.strip()))
        self._persist_recording()
        self.status_label.setText(
            t("Transcrição concluída ({language}, {count} segmentos). Salva no histórico.").format(
                language=result.language, count=len(result.segments)
            )
        )
        self._load_history()

    def _persist_recording(self):
        """Cria/atualiza o Recording atual no banco (transcrição e, se houver, resumo)."""
        s = get_session()
        try:
            rec_id = self._current.get("rec_id")
            rec = s.query(Recording).get(rec_id) if rec_id else None
            if rec is None:
                rec = Recording()
                s.add(rec)
            rec.kind = self.kind_combo.currentData()
            rec.title = self._current.get("title") or rec.title or ""
            rec.topic = self.topic_input.text().strip()
            rec.transcript = self.transcript_edit.toPlainText().strip()
            rec.summary_json = self._current.get("summary_json", rec.summary_json or "")
            rec.markdown = self._current.get("markdown", rec.markdown or "")
            rec.duration = self._current.get("duration", 0.0)
            rec.language = self._current.get("language", "")
            rec.audio_path = self._current.get("audio_path", "")
            rec.tags = json.dumps(self._current.get("tags", []), ensure_ascii=False)
            s.commit()
            self._current["rec_id"] = rec.id
        finally:
            s.close()

    def _on_transcribe_error(self, err):
        self.progress.setVisible(False)
        self.status_label.setText(t("Erro na transcrição: {error}").format(error=err))

    # ------------------------- Análise IA -------------------------
    def _analyze(self):
        transcript = self.transcript_edit.toPlainText().strip()
        if not transcript:
            self.status_label.setText(t("Sem transcrição para analisar."))
            return
        provider = get_active_ai_provider()
        if not provider or not provider.get("model"):
            name = provider.get("name") if provider else t("nenhum")
            self.status_label.setText(
                t("O provedor de IA ativo ({name}) está sem modelo definido. "
                  "Configure em Configurações → Provedores de IA (Base URL, API Key e Modelo).").format(name=name)
            )
            return
        kind = self.kind_combo.currentData()
        self.analyze_btn.setEnabled(False)
        self.status_label.setText(t("Analisando com IA..."))
        self._analyzer = AnalyzeWorker(
            kind, transcript, self.topic_input.text().strip(),
            self._current.get("duration", 0.0), self._current.get("language", ""),
        )
        self._analyzer.done.connect(self._on_analyzed)
        self._analyzer.failed.connect(self._on_analyze_error)
        self._analyzer.start()

        # Se o assistente ao vivo NÃO foi usado (abas vazias), gera as tabelas de
        # itens (plano, dicas, ações, decisões, perguntas) a partir da transcrição
        # completa — a mesma extração do ao vivo.
        has_live = any(self._live_state.get(k) for k in
                       ("plan", "tips", "action_items", "decisions", "questions"))
        if not has_live:
            self._start_analyze_extract(transcript)

    def _start_analyze_extract(self, transcript):
        from maestro_local.transcricoes.live_assistant import EMPTY_STATE, LiveExtractWorker
        self._live_state = dict(EMPTY_STATE)
        self._refresh_live_panels()
        self._live_transcript = transcript
        self.live_transcript_edit.setPlainText(transcript)
        self.live_box.setVisible(True)
        ai_ok = self._provider_ready()
        self.ask_input.setEnabled(ai_ok)
        self.ask_btn.setEnabled(ai_ok)
        self.live_status.setText(t("Gerando itens (plano, ações, decisões, perguntas)..."))
        self._analyze_extractor = LiveExtractWorker(
            dict(EMPTY_STATE), transcript, context=self._meeting_context())
        self._analyze_extractor.done.connect(self._on_analyze_extracted)
        self._analyze_extractor.failed.connect(self._on_analyze_extract_error)
        self._analyze_extractor.start()

    def _on_analyze_extracted(self, state: dict):
        self._analyze_extractor = None
        self._live_state = state
        self._refresh_live_panels()
        self.live_status.setText(t("Itens gerados a partir da transcrição."))

    def _on_analyze_extract_error(self, err: str):
        self._analyze_extractor = None
        self.live_status.setText(t("Erro ao gerar itens: {error}").format(error=err))

    def _on_analyzed(self, payload):
        md, summary, title, tags, duration, language = payload
        self.analyze_btn.setEnabled(True)
        self.result_edit.setVisible(True)
        self.result_edit.setPlainText(md)
        self.save_day_btn.setEnabled(True)
        self._current.update({
            "markdown": md, "title": title, "tags": tags,
            "summary_json": json.dumps(summary, ensure_ascii=False),
            "duration": duration, "language": language,
        })
        self._persist_recording()  # atualiza o registro já criado na transcrição
        self.status_label.setText(t("Análise concluída e salva no histórico."))
        self._load_history()

    def _on_analyze_error(self, err):
        self.analyze_btn.setEnabled(True)
        self.status_label.setText(t("Erro na análise: {error}").format(error=err))

    # ------------------------- Meu Dia -------------------------
    def _save_to_day(self):
        # Usa o resumo de IA se houver; senão, salva a própria transcrição
        md = self.result_edit.toPlainText().strip()
        if not md:
            transcript = self.transcript_edit.toPlainText().strip()
            if not transcript:
                self.status_label.setText(t("Nada para salvar — grave e transcreva primeiro."))
                return
            kind_label = t("Estudo") if self.kind_combo.currentData() == "study" else t("Reunião")
            topic = self.topic_input.text().strip()
            header = f"## {kind_label}" + (f": {topic}" if topic else "")
            hora = datetime.now().strftime("%H:%M")
            md = f"{header} ({hora})\n\n{transcript}"
        from maestro_local.db.models import DailyNote
        today = datetime.now().strftime("%Y-%m-%d")
        s = get_session()
        try:
            note = s.query(DailyNote).filter(DailyNote.date == today).first()
            if not note:
                note = DailyNote(date=today, body="", report="")
                s.add(note)
            note.report = (note.report or "") + "\n\n" + md
            s.commit()
        finally:
            s.close()
        self.status_label.setText(t("Resumo adicionado ao relatório do Meu Dia."))

    def _build_meeting_markdown(self):
        """Monta o markdown completo da reunião (ou None se não há nada)."""
        from maestro_local.transcricoes import markdown_gen
        transcript = (self._current.get("transcript") or self._live_transcript
                      or self.transcript_edit.toPlainText() or "").strip()
        summary_md = (self._current.get("markdown") or self.result_edit.toPlainText() or "").strip()
        has_live = any(self._live_state.get(k) for k in
                       ("plan", "tips", "action_items", "decisions",
                        "questions"))
        if not (has_live or transcript or summary_md):
            return None
        kind = self.kind_combo.currentData()
        topic = self.topic_input.text().strip() if kind == "study" else ""
        return markdown_gen.live_meeting_to_markdown(
            title=self._current.get("title", ""), kind=kind,
            date_str=datetime.now().strftime("%d/%m/%Y %H:%M"),
            duration=self._current.get("duration") or float(self._elapsed),
            topic=topic, state=self._live_state,
            transcript=transcript, summary_md=summary_md,
        )

    def _export_markdown(self):
        """Exporta um markdown único e estruturado com todos os itens de todas
        as abas do assistente ao vivo + (opcional) resumo da IA + transcrição."""
        md = self._build_meeting_markdown()
        if md is None:
            self.status_label.setText(t("Nada para exportar ainda — grave/analise uma reunião primeiro."))
            return
        kind = self.kind_combo.currentData()
        default_name = ("estudo" if kind == "study" else "reuniao") + \
            "-" + datetime.now().strftime("%Y%m%d-%H%M") + ".md"
        path, _ = QFileDialog.getSaveFileName(
            self, t("Exportar reunião"), default_name, "Markdown (*.md)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(md)
        except OSError as e:  # noqa: BLE001
            self.status_label.setText(t("Erro ao salvar: {error}").format(error=e))
            return
        self.status_label.setText(t("Exportado: {path}").format(path=path))

    def _copy_markdown(self):
        md = self._build_meeting_markdown()
        if md is None:
            self.status_label.setText(t("Nada para exportar ainda — grave/analise uma reunião primeiro."))
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(md)
        self.status_label.setText(t("Markdown copiado para a área de transferência."))

    # ------------------------- Histórico -------------------------
    def _load_history(self):
        self.history.clear()
        query = self.search.text().strip().lower()
        s = get_session()
        try:
            recs = s.query(Recording).order_by(Recording.created_at.desc()).limit(100).all()
            for r in recs:
                hay = f"{r.title} {r.topic} {r.transcript}".lower()
                if query and query not in hay:
                    continue
                icon = "📓" if r.kind == "study" else "🗣"
                when = r.created_at.strftime("%d/%m %H:%M") if r.created_at else ""
                item = QListWidgetItem(f"{icon}  {r.title or t('(sem título)')}\n{when}")
                item.setData(Qt.UserRole, r.id)
                self.history.addItem(item)
        finally:
            s.close()

    def _open_recording(self, item):
        rec_id = item.data(Qt.UserRole)
        s = get_session()
        try:
            r = s.query(Recording).get(rec_id)
            if not r:
                return
            self.transcript_edit.setPlainText(r.transcript or "")
            self.result_edit.setVisible(True)
            self.result_edit.setPlainText(r.markdown or "")
            self.save_day_btn.setEnabled(bool(r.markdown))
            self._current["markdown"] = r.markdown or ""
            idx = self.kind_combo.findData(r.kind)
            if idx >= 0:
                self.kind_combo.setCurrentIndex(idx)
            self.status_label.setText(t("Gravação de {when}").format(when=r.created_at.strftime('%d/%m/%Y %H:%M') if r.created_at else ''))
        finally:
            s.close()
