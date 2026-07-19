"""Transcrições: grava reuniões/estudos, transcreve e resume com IA."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QMessageBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QToolButton,
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
from maestro_local.transcricoes import repository
from maestro_local.transcricoes.agent_service import MeetingAgentService
from maestro_local.transcricoes.session import MeetingSession, empty_live_state
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
    Task,
    get_session,
)
from maestro_local.gui.meetings import (
    DestinationBar,
    HistoryPanel,
    LiveAssistantPanel,
    PreparationCard,
    RecordingCard,
    ResultCard,
    SectionCard,
)
from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# Intervalo entre capturas quando o "assistente vê a tela" está ligado (segundos).
SCREEN_WATCH_SECONDS = 40


def _whisper_settings():
    cfg = load_config().get("settings", {}).get("transcricoes", {})
    return (
        cfg.get("whisper_model", WHISPER_DEFAULT_MODEL),
        cfg.get("whisper_language", WHISPER_DEFAULT_LANGUAGE),
    )


def _recordings_dir() -> Path:
    return DATA_DIR / "workspaces" / get_active_workspace_id() / "recordings"


class _QACard(QFrame):
    """Card de pergunta+resposta da reunião. Duplo-clique (no card) alterna
    resolvida; o campo de resposta é editável — o agente preenche e o usuário
    pode adicionar/corrigir respostas manualmente."""
    toggled = Signal(int)
    answered = Signal(int, str)   # (índice, texto da resposta editada)

    def __init__(self, index: int, question: str, answer: str, resolved: bool, theme):
        super().__init__()
        self._index = index
        self._orig_answer = (answer or "").strip()
        self.setToolTip(t("Duplo-clique no card para marcar como resolvida / reabrir."))
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

        # Campo de resposta editável (agente preenche; usuário pode adicionar/editar).
        self._answer_edit = QLineEdit(answer or "")
        self._answer_edit.setPlaceholderText(t("Adicionar resposta…"))
        self._answer_edit.setStyleSheet(
            f"QLineEdit {{ color: {theme.text_secondary}; font-size: 12px; "
            f"background: {theme.bg_badge}; border: 1px solid {theme.border}; "
            f"border-radius: 6px; padding: 5px 8px; }}")
        self._answer_edit.returnPressed.connect(self._emit_answer)
        self._answer_edit.editingFinished.connect(self._emit_answer)
        lay.addWidget(self._answer_edit)

    def _emit_answer(self):
        txt = self._answer_edit.text().strip()
        if txt != self._orig_answer:
            self._orig_answer = txt   # evita reemitir o mesmo valor
            self.answered.emit(self._index, txt)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self.toggled.emit(self._index)
        super().mouseDoubleClickEvent(event)


class TranscricoesView(QWidget):
    # Emitido quando o usuário troca o workspace pela própria tela de reuniões;
    # a janela principal faz a troca de banco + refresh geral.
    workspace_change_requested = Signal(str)
    # Projeto ativo alterado pela tela de reuniões (sidebar sincroniza).
    project_changed = Signal(object)

    def __init__(self):
        super().__init__()
        self._session = None
        self._loading_ws = False
        self._loading_proj = False
        # Todos os trabalhos de IA (transcrever, analisar, extrair, perguntar,
        # ler imagem) passam pelo serviço: ele é dono dos threads.
        self.agent = MeetingAgentService(self)
        self._elapsed = 0
        # Estado da reunião em edição (entradas x saídas) — fonte única de
        # verdade; `_live_state` abaixo é só um atalho para session.live_state.
        self._meeting = MeetingSession()
        self._current = {"transcript": "", "duration": 0.0, "language": "", "audio_path": ""}
        # Visualização do resumo Markdown: fonte editável x preview renderizado.
        self._md_preview = False
        self._md_source = ""
        # Edição da transcrição: revisa os itens depois que o usuário para de
        # digitar (debounce), sem disparar a IA a cada tecla.
        self._setting_transcript = False
        self._transcript_review = QTimer(self)
        self._transcript_review.setSingleShot(True)
        self._transcript_review.setInterval(2500)
        self._transcript_review.timeout.connect(self._review_after_edit)
        # Contexto extra da reunião (arquivos/imagens/tela) → alimenta o copiloto.
        self._context_items: list[dict] = []   # {label, text}
        # Observador de tela ao vivo (o agente "vê" um monitor durante a reunião)
        self._screen_timer = None
        self._screen_watch_text = ""            # última leitura da tela observada

        # Estado do assistente ao vivo
        self._live_transcriber = None

        self._live_transcript = ""       # transcrição ao vivo acumulada
        self._live_pending = ""          # texto novo ainda não enviado à IA
        self._live_secs_since = 0        # segundos desde a última extração

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
        self.history_panel = HistoryPanel()
        self.history_panel.new_meeting_requested.connect(self._new_meeting)
        self.history_panel.filters_changed.connect(self._load_history)
        self.history_panel.item_opened.connect(self._open_recording)
        self.history_panel.context_menu_requested.connect(self._history_context_menu)
        self.history_panel.order_changed.connect(self._persist_history_order)
        # Aliases: o resto da view (e os testes) seguem usando estes nomes.
        self.new_meeting_btn = self.history_panel.new_meeting_btn
        self.search = self.history_panel.search
        self.show_archived_check = self.history_panel.show_archived_check
        self.history = self.history_panel.history
        self.history_empty = self.history_panel.history_empty
        self._left_widget = self.history_panel
        self._main_split.addWidget(self.history_panel)

        # ---- Coluna direita: gravação + transcrição ----
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(8, 0, 0, 0)
        right.setSpacing(10)

        title_row = QHBoxLayout()
        # Botão de histórico — aparece só quando a tela é estreita (histórico colapsa)
        self.history_toggle = QPushButton(t("☰ Histórico"))
        self.history_toggle.setProperty("flat", "true")
        self.history_toggle.setFixedHeight(32)
        self.history_toggle.setCursor(Qt.PointingHandCursor)
        self.history_toggle.setToolTip(t("Mostrar/ocultar o histórico de gravações"))
        self.history_toggle.clicked.connect(self._toggle_history_panel)
        self.history_toggle.setVisible(False)
        title_row.addWidget(self.history_toggle)
        title = QLabel(t("Reuniões"))
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.import_btn = QPushButton(t("📄 Importar arquivo"))
        self.import_btn.setProperty("flat", "true")
        self.import_btn.setFixedHeight(32)
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.setToolTip(
            t("Cria uma reunião a partir de uma transcrição externa (Meet, Teams, "
              "arquivo de texto/VTT/SRT/PDF/DOCX) e roda a mesma análise (plano, "
              "ações, decisões, perguntas)."))
        self.import_btn.clicked.connect(self._import_meeting_from_file)
        title_row.addWidget(self.import_btn)
        self.tips_btn = QPushButton(t("💡 Dicas"))
        self.tips_btn.setProperty("flat", "true")
        self.tips_btn.setFixedHeight(32)
        self.tips_btn.setCursor(Qt.PointingHandCursor)
        self.tips_btn.setToolTip(t("Como aproveitar melhor as reuniões"))
        self.tips_btn.clicked.connect(self._show_tips)
        title_row.addWidget(self.tips_btn)
        right.addLayout(title_row)

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

        # ---- Destino da reunião (workspace + projeto) — sempre visível no topo ----
        self.destination = DestinationBar()
        self.destination.workspace_index_changed.connect(self._on_ws_combo_changed)
        self.destination.project_index_changed.connect(self._on_proj_combo_changed)
        self.ws_combo = self.destination.ws_combo      # aliases (ver HistoryPanel)
        self.proj_combo = self.destination.proj_combo
        right.addWidget(self.destination)

        # ---- 1. Preparar ----
        self.preparation = PreparationCard()
        self.preparation.kind_changed.connect(self._on_kind_changed)
        self.preparation.add_file_requested.connect(self._add_context_file)
        self.preparation.capture_screen_requested.connect(self._capture_screen_context)
        # Aliases (migração incremental — ver HistoryPanel)
        self.kind_combo = self.preparation.kind_combo
        self.topic_input = self.preparation.topic_input
        self.prep_edit = self.preparation.prep_edit
        self.context_btn = self.preparation.context_btn
        self.context_summary = self.preparation.context_summary
        self.context_container = self.preparation.context_container
        self._context_layout = self.preparation.context_layout
        right.addWidget(self.preparation)

        # ---- 2. Gravar ----
        self.recording = RecordingCard()
        self.recording.record_toggled.connect(self._toggle_record)
        self.recording.live_toggled.connect(self._on_live_toggled)
        self.recording.screen_watch_toggled.connect(self._on_screen_watch_toggled)
        self.recording.audio_selection_changed.connect(self._update_audio_summary)
        self.audio_toggle = self.recording.audio_toggle
        self.audio_summary = self.recording.audio_summary
        self.audio_box = self.recording.audio_box
        self.mic_combo = self.recording.mic_combo
        self.monitor_combo = self.recording.monitor_combo
        self.screen_watch_check = self.recording.screen_watch_check
        self.screen_combo = self.recording.screen_combo
        self.screen_watch_status = self.recording.screen_watch_status
        self.record_btn = self.recording.record_btn
        self.timer_label = self.recording.timer_label
        self.live_check = self.recording.live_check
        right.addWidget(self.recording)

        # ---- Painel do assistente ao vivo (visível só durante gravação ao vivo) ----
        self.live = LiveAssistantPanel()
        self.live.ask_requested.connect(self._ask_meeting)
        self.live_box = self.live
        self.live_status = self.live.live_status
        self.live_transcript_edit = self.live.live_transcript_edit
        self.live_tabs = self.live.live_tabs
        self.live_plan_list = self.live.live_plan_list
        self.live_tips_list = self.live.live_tips_list
        self.live_actions_list = self.live.live_actions_list
        self.live_decisions_list = self.live.live_decisions_list
        self.ask_input = self.live.ask_input
        self.ask_btn = self.live.ask_btn
        self.ask_answer = self.live.ask_answer
        self._questions_layout = self.live.questions_layout
        self._questions_container = self.live.questions_container
        self._questions_empty = self.live.questions_empty
        self.live_box.setVisible(False)
        right.addWidget(self.live_box, 6)

        # Progresso de transcrição
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        right.addWidget(self.status_label)

        # ---- 3. Resultado: transcrição + resumo + ações agrupadas ----
        self.result = ResultCard()
        self.result.transcript_edited.connect(self._on_transcript_edited)
        self.result.md_view_toggled.connect(self._toggle_md_view)
        self.result.analyze_requested.connect(self._analyze)
        self.result.export_requested.connect(self._export_markdown)
        self.result.copy_requested.connect(self._copy_markdown)
        self.result.tasks_requested.connect(self._actions_to_tasks)
        self.result.save_day_requested.connect(self._save_to_day)
        self.transcript_label = self.result.transcript_label
        self.transcript_edit = self.result.transcript_edit
        self.summary_label = self.result.summary_label
        self.md_view_btn = self.result.md_view_btn
        self.result_edit = self.result.result_edit
        self.analyze_btn = self.result.analyze_btn
        self.export_btn = self.result.export_btn
        self.copy_btn = self.result.copy_btn
        self.tasks_btn = self.result.tasks_btn
        self.save_day_btn = self.result.save_day_btn
        right.addWidget(self.result)

        # A coluna direita rola quando o conteúdo (controles + painel ao vivo)
        # não cabe na altura da janela — evita widgets sobrepostos.
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setWidget(right_widget)
        right_widget.setMinimumWidth(340)

        self._main_split.addWidget(right_scroll)
        self._main_split.setStretchFactor(0, 0)
        self._main_split.setStretchFactor(1, 1)
        self._main_split.setSizes([260, 900])

        # Resultados dos trabalhos de IA (o serviço é dono dos threads).
        self.agent.transcribe_progress.connect(self.progress.setValue)
        self.agent.transcribed.connect(self._on_transcribed)
        self.agent.transcribe_failed.connect(self._on_transcribe_error)
        self.agent.analyzed.connect(self._on_analyzed)
        self.agent.analyze_failed.connect(self._on_analyze_error)
        self.agent.live_extracted.connect(self._on_live_extracted)
        self.agent.live_extract_failed.connect(self._on_live_extract_error)
        self.agent.extracted.connect(self._on_analyze_extracted)
        self.agent.extract_failed.connect(self._on_analyze_extract_error)
        self.agent.answered.connect(self._on_ask_answered)
        self.agent.ask_failed.connect(self._on_ask_error)
        self.agent.vision_done.connect(self._on_vision_done)
        self.agent.vision_failed.connect(self._on_vision_failed)
        self.agent.screen_read.connect(self._on_screen_watch_captured)
        self.agent.screen_failed.connect(self._on_screen_watch_failed)

        self.refresh()

    # ------------------------- UI helpers -------------------------
    def _section_card(self, number: str, title_text: str, help_text: str = ""):
        """Card de etapa numerada (deixa o fluxo da tela explícito)."""
        card = SectionCard(number, title_text, help_text)
        return card, card.body

    def _update_audio_summary(self):
        """Resumo das fontes de áudio — a lógica vive no RecordingCard."""
        if hasattr(self, "recording"):
            self.recording.update_audio_summary()

    # ------------------------------------------------------------------
    def resizeEvent(self, event):
        """Responsivo: abaixo de um breakpoint, colapsa o histórico para o
        conteúdo ocupar a largura toda; oferece um botão para reexibi-lo."""
        super().resizeEvent(event)
        narrow = self.width() < 820
        if narrow != getattr(self, "_narrow", None):
            self._narrow = narrow
            self.history_toggle.setVisible(narrow)
            self._left_widget.setVisible(not narrow)

    def _toggle_history_panel(self):
        self._left_widget.setVisible(not self._left_widget.isVisible())

    def refresh(self):
        self._populate_devices()
        self._populate_screens()
        self._populate_workspaces()
        self._populate_projects()
        self._load_history()
        self._check_provider()

    def _populate_screens(self):
        """Lista os monitores disponíveis para o observador de tela."""
        current = self.screen_combo.currentIndex()
        self.screen_combo.blockSignals(True)
        self.screen_combo.clear()
        for i, s in enumerate(QApplication.screens()):
            geo = s.geometry()
            name = s.name() or t("Monitor {n}").format(n=i + 1)
            self.screen_combo.addItem(
                t("Monitor {n} — {name} ({w}×{h})").format(
                    n=i + 1, name=name, w=geo.width(), h=geo.height()), i)
        if 0 <= current < self.screen_combo.count():
            self.screen_combo.setCurrentIndex(current)
        self.screen_combo.blockSignals(False)

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
        from maestro_local.gui.confirm_switch import confirm_workspace_switch
        if not confirm_workspace_switch(self, ws_id):
            self._populate_workspaces()  # volta o combo para o workspace atual
            return
        transcript = self.transcript_edit.toPlainText().strip()
        # Remove a gravação do workspace atual — será recriada no destino.
        old_rec_id = self._current.get("rec_id")
        if old_rec_id and transcript:
            repository.delete(old_rec_id)
        self._current["rec_id"] = None
        set_active_workspace(ws_id)
        # A janela principal troca o banco ativo e faz o refresh geral (síncrono).
        self.workspace_change_requested.emit(ws_id)
        if transcript:
            self._persist_recording()  # recria a reunião no workspace de destino
            self.status_label.setText(t("Reunião movida para o workspace selecionado."))
            self._load_history()

    def _populate_projects(self):
        """Lista os projetos, seguindo o projeto ativo (seletor da sidebar)."""
        from maestro_local.config import get_active_project_id
        self._loading_proj = True
        try:
            current = self.proj_combo.currentData() or get_active_project_id()
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
        finally:
            self._loading_proj = False

    def _on_proj_combo_changed(self):
        """Trocar o projeto aqui também define o projeto ativo (sidebar)."""
        if getattr(self, "_loading_proj", False):
            return
        from maestro_local.config import get_active_project_id, set_active_project_id
        pid = self.proj_combo.currentData()
        if pid is not None and pid != get_active_project_id():
            set_active_project_id(pid)
            self.project_changed.emit(pid)

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
        self.preparation.set_study_mode(self.preparation.kind() == "study")

    # ------------------------- Painel ao vivo -------------------------
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
            card.answered.connect(self._set_question_answer)
            self._questions_layout.insertWidget(self._questions_layout.count() - 1, card)

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
        # Nova gravação: zera o estado e as saídas da reunião anterior (mantém a
        # preparação/contexto já preenchidos para ESTA reunião).
        self._current = {"transcript": "", "duration": 0.0, "language": "", "audio_path": ""}
        self._reset_outputs()
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
        # Encerra o observador de tela junto com a gravação (para de consumir IA).
        if self.screen_watch_check.isChecked():
            self.screen_watch_check.setChecked(False)
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
        if self.agent.is_extracting_live():  # já tem uma extração em curso
            return
        if not self._live_pending.strip() or not self._provider_ready():
            return
        words = len(self._live_pending.split())
        if words < LIVE_AI_MIN_WORDS and self._live_secs_since < LIVE_AI_MIN_SECONDS:
            return
        self._start_live_extract()

    def _start_live_extract(self):
        new_text = self._live_pending
        self._live_pending = ""
        self._live_secs_since = 0
        # Recalcula o contexto a cada extração para captar edições de preparação
        # ou novos anexos feitos durante a reunião.
        self._live_context = self._meeting_context()
        self.agent.extract_live(self._live_state, new_text, context=self._live_context)

    # Estado dos itens do assistente vive no MeetingSession; a property mantém
    # `self._live_state` funcionando como antes em toda a view.
    @property
    def _live_state(self) -> dict:
        return self._meeting.live_state

    @_live_state.setter
    def _live_state(self, value: dict):
        self._meeting.live_state = value

    def _preserve_answers(self, new_state: dict) -> dict:
        """Mantém respostas já dadas (manuais ou do agente) quando o agente
        reemite as perguntas sem a resposta — evita perder edições manuais."""
        return self._meeting.merge_live_state(new_state)

    def _autosave_live_state(self):
        """Salva os itens do assistente assim que mudam (só se já há gravação)."""
        if self._current.get("rec_id") or self.transcript_edit.toPlainText().strip() \
                or self._live_transcript.strip():
            self._persist_recording()

    def _on_live_extracted(self, state: dict):
        self._live_state = self._preserve_answers(state)
        self._autosave_live_state()
        self._refresh_live_panels()
        if self._live_transcriber is not None:
            self.live_status.setText(t("Transcrevendo ao vivo..."))

    def _on_live_extract_error(self, err: str):
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
        if not self._meeting.toggle_resolved(index):
            return
        self._autosave_live_state()
        self._refresh_live_panels()

    def _set_question_answer(self, index, text):
        """Define/edita manualmente a resposta de uma pergunta gerada pelo agente."""
        if not self._meeting.set_answer(index, text):
            return
        self._autosave_live_state()
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
        self.ask_btn.setEnabled(False)
        self.ask_answer.setVisible(True)
        self.ask_answer.setText(t("Pensando..."))
        self.agent.ask(
            self._live_transcript, question,
            context=getattr(self, "_live_context", "") or self._meeting_context())

    def _on_ask_answered(self, answer: str):
        self.ask_btn.setEnabled(True)
        self.ask_answer.setText(answer)

    def _on_ask_error(self, err: str):
        self.ask_btn.setEnabled(True)
        self.ask_answer.setText(t("Erro: {error}").format(error=err))

    # ----------------------- Contexto adicional -----------------------
    def _add_context_file(self):
        """Anexa arquivos (imagem/PDF/texto…) como contexto da reunião."""
        exts = "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.pdf *.txt *.md *.log *.json *.csv *.docx *.epub"
        paths, _ = QFileDialog.getOpenFileNames(
            self, t("Adicionar contexto"), "",
            t("Contexto (imagem, PDF, texto)") + f" ({exts});;" + t("Todos os arquivos") + " (*)",
        )
        for path in paths or []:
            self._ingest_context_path(path)

    def _ingest_context_path(self, path: str):
        p = Path(path)
        ext = p.suffix.lower()
        try:
            data = p.read_bytes()
        except Exception as e:  # noqa: BLE001
            self.status_label.setText(t("Erro ao ler arquivo: {error}").format(error=e))
            return
        if ext in IMAGE_EXTS:
            mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
            self._run_vision(p.name, data, mime)
            return
        from maestro_local.study.ingest import extract_text
        text = extract_text(data, p.name)
        if not text:
            self.status_label.setText(t("Não foi possível extrair texto de {name}.").format(name=p.name))
            return
        self._add_context_item(p.name, text)
        self.status_label.setText(t("Contexto adicionado: {label}").format(label=p.name))

    def _capture_screen_context(self):
        """Minimiza a janela, captura a tela e usa como contexto (via visão da IA)."""
        win = self.window()
        win.showMinimized()
        # Pequeno atraso para a janela sair da frente antes do print.
        QTimer.singleShot(400, self._do_grab_screen)

    def _do_grab_screen(self):
        win = self.window()
        pix = None
        try:
            screen = QApplication.primaryScreen()
            if screen is not None:
                pix = screen.grabWindow(0)
        finally:
            win.showNormal()
            win.raise_()
            win.activateWindow()
        if pix is None or pix.isNull():
            self.status_label.setText(t("Não foi possível capturar a tela."))
            return
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        pix.save(buf, "PNG")
        buf.close()
        n = sum(1 for it in self._context_items if it["label"].startswith("Captura de tela")) + 1
        self._run_vision(f"Captura de tela {n}", bytes(ba.data()), "image/png")

    def _run_vision(self, label: str, image_bytes: bytes, mime: str):
        if not self._provider_ready():
            self.status_label.setText(t("Configure um provedor de IA para ler imagens/telas."))
            return
        self.status_label.setText(t("Lendo imagem com IA: {label}…").format(label=label))
        self.agent.read_image(label, image_bytes, mime)

    def _on_vision_done(self, label: str, text: str):
        if not text:
            self.status_label.setText(t("A imagem não retornou texto útil."))
            return
        self._add_context_item(label, text)
        self.status_label.setText(t("Contexto adicionado: {label}").format(label=label))

    def _on_vision_failed(self, label: str, err: str):
        self.status_label.setText(
            t("Falha ao ler imagem ({label}): {err}").format(label=label, err=err)
        )

    def _add_context_item(self, label: str, text: str):
        self._context_items.append({"label": label, "text": text})
        self._render_context()
        self._refresh_live_context()

    def _remove_context_item(self, idx: int):
        if 0 <= idx < len(self._context_items):
            self._context_items.pop(idx)
            self._render_context()
            self._refresh_live_context()

    def _render_context(self):
        while self._context_layout.count():
            item = self._context_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for i, it in enumerate(self._context_items):
            chip = QFrame()
            chip.setProperty("card", "true")
            h = QHBoxLayout(chip)
            h.setContentsMargins(8, 4, 8, 4)
            h.setSpacing(6)
            preview = " ".join(it["text"].split())
            if len(preview) > 70:
                preview = preview[:70] + "…"
            lbl = QLabel(f"📎 {it['label']} — {preview}")
            lbl.setToolTip(it["text"][:2000])
            h.addWidget(lbl, 1)
            rm = QToolButton()
            rm.setText("×")
            rm.setCursor(Qt.PointingHandCursor)
            rm.setToolTip(t("Remover contexto"))
            rm.clicked.connect(lambda _=False, idx=i: self._remove_context_item(idx))
            h.addWidget(rm)
            self._context_layout.addWidget(chip)
        n = len(self._context_items)
        self.context_container.setVisible(n > 0)
        self.context_summary.setText(
            t("Nenhum contexto adicionado") if n == 0
            else t("{n} item(ns) de contexto anexado(s)").format(n=n)
        )

    def _refresh_live_context(self):
        """Atualiza o contexto do copiloto ao vivo quando o usuário anexa/remove itens."""
        if self._live_transcriber is not None:
            self._live_context = self._meeting_context()

    # -------------------- Observador de tela ao vivo ------------------
    def _on_screen_watch_toggled(self, on: bool):
        if on:
            if not self._provider_ready():
                self.screen_watch_check.setChecked(False)
                self.status_label.setText(
                    t("Configure um provedor de IA (com visão) para o assistente ver a tela."))
                return
            self._start_screen_watch()
        else:
            self._stop_screen_watch()

    def _start_screen_watch(self):
        if self._screen_timer is None:
            self._screen_timer = QTimer(self)
            self._screen_timer.timeout.connect(self._capture_watched_screen)
        self._screen_timer.start(SCREEN_WATCH_SECONDS * 1000)
        self.screen_watch_status.setVisible(True)
        self.screen_watch_status.setText(t("👁 Observando a tela… (captura a cada {s}s)")
                                         .format(s=SCREEN_WATCH_SECONDS))
        self._capture_watched_screen()  # primeira leitura imediata

    def _stop_screen_watch(self):
        if self._screen_timer is not None:
            self._screen_timer.stop()
        # Para de "ver" a tela: descarta a última leitura para não vazar contexto antigo.
        self._screen_watch_text = ""
        self.screen_watch_status.setVisible(False)
        self._refresh_live_context()

    def _capture_watched_screen(self):
        if self.agent.is_reading_screen():
            return  # leitura anterior ainda em andamento — evita empilhar
        if not self._provider_ready():
            return
        screens = QApplication.screens()
        idx = self.screen_combo.currentData()
        idx = idx if isinstance(idx, int) else self.screen_combo.currentIndex()
        if idx is None or idx < 0 or idx >= len(screens):
            return
        screen = screens[idx]
        geo = screen.geometry()
        pix = screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
        if pix is None or pix.isNull():
            self.screen_watch_status.setText(t("Não foi possível capturar o monitor selecionado."))
            return
        if pix.width() > 1280:  # reduz o payload enviado à IA
            pix = pix.scaledToWidth(1280, Qt.SmoothTransformation)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        pix.save(buf, "PNG")
        buf.close()
        self.agent.read_screen(t("Tela ao vivo"), bytes(ba.data()), "image/png")

    def _on_screen_watch_captured(self, label: str, text: str):
        if text and self.screen_watch_check.isChecked():
            self._screen_watch_text = text
            self._refresh_live_context()
            self.screen_watch_status.setText(
                t("👁 Tela lida — o assistente está usando o conteúdo do monitor."))

    def _on_screen_watch_failed(self, label: str, err: str):
        self.screen_watch_status.setText(
            t("Falha ao ler a tela ({err}). Verifique o provedor de IA com visão.").format(err=err))

    # ---------------------------- Dicas -------------------------------
    def _show_tips(self):
        """Modal com dicas de uso para tirar mais proveito das reuniões."""
        dlg = QDialog(self)
        dlg.setWindowTitle(t("Dicas para reuniões"))
        dlg.setMinimumSize(560, 540)
        lay = QVBoxLayout(dlg)
        head = QLabel(t("💡 Como aproveitar melhor as reuniões"))
        head.setObjectName("sectionTitle")
        lay.addWidget(head)
        tips = [
            (t("Prepare antes de começar"),
             t("Use a seção 🧭 Preparação para escrever a pauta, os objetivos e os "
               "participantes, e anexe contexto (arquivos, PDFs, imagens ou uma captura "
               "de tela). Assim o assistente já inicia sabendo do que se trata.")),
            (t("Escolha as fontes de áudio"),
             t("Selecione o Microfone e o Áudio do sistema (monitor) para capturar tanto "
               "você quanto os outros participantes. O áudio do sistema padrão já vem "
               "selecionado quando há um disponível.")),
            (t("Ligue o Assistente ao vivo"),
             t("Marque 'Assistente ao vivo' para transcrever e extrair ações, decisões, "
               "plano e perguntas em tempo real. Pode ligar/desligar a qualquer momento, "
               "inclusive no meio da reunião.")),
            (t("Confirme o destino"),
             t("Verifique o Workspace e o Projeto no rodapé antes de gravar — é para onde "
               "a reunião e as tarefas geradas vão. Dá para trocar a qualquer momento.")),
            (t("Pergunte durante a reunião"),
             t("Use o campo 'Perguntar à reunião' para tirar dúvidas com base na "
               "transcrição e no contexto anexado, sem interromper a captura.")),
            (t("Transforme em tarefas"),
             t("Ao final, use 'Criar tarefas das ações' para enviar as ações ao board, "
               "'Salvar no Meu Dia' para o registro do dia e 'Exportar/Copiar (.md)' para "
               "um documento único.")),
            (t("Precisa de IA?"),
             t("A transcrição funciona offline (Whisper). Já o copiloto, as perguntas e a "
               "leitura de imagens/telas exigem um provedor de IA configurado em "
               "Configurações (imagens exigem um modelo com visão).")),
        ]
        body = QTextEdit()
        body.setReadOnly(True)
        body.setHtml("".join(
            f"<p style='margin:0 0 12px 0'><b>{ti}</b><br>{bo}</p>" for ti, bo in tips
        ))
        lay.addWidget(body, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.reject)
        btns.accepted.connect(dlg.accept)
        lay.addWidget(btns)
        dlg.exec()

    def _meeting_context(self) -> str:
        """Monta o contexto do workspace + projeto selecionado para o copiloto.

        Usa o projeto escolhido no seletor (o mesmo de "Criar tarefas das ações")
        e resume seus tópicos e tarefas em aberto, para o assistente alinhar plano
        e dicas ao trabalho atual.
        """
        parts = []
        prep = self.prep_edit.toPlainText().strip()
        if prep:
            parts.append(t("## Preparação / informações prévias") + "\n" + prep[:3000])
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
        if self._context_items:
            parts.append(t("## Contexto anexado à reunião"))
            for it in self._context_items:
                body = (it.get("text") or "").strip()[:3000]
                parts.append(f"### {it['label']}\n{body}")
        if self._screen_watch_text:
            parts.append(t("## Tela observada agora (ao vivo)") + "\n"
                         + self._screen_watch_text[:3000])
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
        model, lang = _whisper_settings()
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self._set_transcript_text("")
        self.agent.transcribe(audio_path, model, lang)

    # ------------------- Edição da transcrição -------------------
    def _set_transcript_text(self, text: str):
        """Define a transcrição sem disparar a revisão automática."""
        self._setting_transcript = True
        try:
            self.transcript_edit.setPlainText(text or "")
        finally:
            self._setting_transcript = False

    def _on_transcript_edited(self):
        """Usuário editou o texto: agenda a revisão (debounce)."""
        if self._setting_transcript or self.is_recording():
            return
        self._transcript_review.start()  # reinicia a contagem a cada tecla

    def _review_after_edit(self):
        """Após parar de digitar: salva o texto e manda o agente revisar os itens."""
        transcript = self.transcript_edit.toPlainText().strip()
        self._current["transcript"] = transcript
        self._autosave_live_state()  # persiste a transcrição editada
        if not transcript or not self._provider_ready():
            return
        if self.agent.is_extracting():  # já há uma revisão em curso
            return
        # keep_state: revisa mantendo o que vale, inclusive as respostas dadas.
        self._start_analyze_extract(transcript, keep_state=True)

    def _on_transcribed(self, result):
        self.progress.setVisible(False)
        self._current["transcript"] = result.text
        self._current["language"] = result.language
        self._current["duration"] = result.duration or self._current["duration"]
        self._set_transcript_text(result.text)
        # Permite salvar/enviar ao Meu Dia mesmo sem análise de IA
        self.save_day_btn.setEnabled(bool(result.text.strip()))
        self._persist_recording()
        self.status_label.setText(
            t("Transcrição concluída ({language}, {count} segmentos). Salva no histórico.").format(
                language=result.language, count=len(result.segments)
            )
        )
        self._load_history()
        # Gera o relatório automaticamente — não exige clicar em "Analisar com IA".
        if result.text.strip() and self._provider_ready():
            self._analyze()

    def _persist_recording(self):
        """Cria/atualiza o Recording atual no banco (transcrição e, se houver, resumo)."""
        rec_id = self._current.get("rec_id")
        data = {
            "kind": self.kind_combo.currentData(),
            "topic": self.topic_input.text().strip(),
            "transcript": self.transcript_edit.toPlainText().strip(),
            # Itens do assistente (plano/dicas/ações/decisões/perguntas) — salvos
            # sempre, para reabrir a reunião exatamente como estava.
            "live_state_json": json.dumps(self._live_state, ensure_ascii=False),
            "duration": self._current.get("duration", 0.0),
            "language": self._current.get("language", ""),
            "audio_path": self._current.get("audio_path", ""),
            "tags": self._current.get("tags", []),
        }
        # Título/resumo só entram quando há valor: preserva o que já está gravado.
        for key in ("title", "summary_json", "markdown"):
            value = self._current.get(key)
            if value:
                data[key] = value
        self._current["rec_id"] = repository.save(rec_id, data)

    def _on_transcribe_error(self, err):
        self.progress.setVisible(False)
        self.status_label.setText(t("Erro na transcrição: {error}").format(error=err))

    # ------------------------- Importar de arquivo -------------------------
    @staticmethod
    def _clean_subtitle(text: str) -> str:
        """Remove cabeçalho/índices/timestamps de legendas (VTT/SRT) exportadas."""
        out = []
        for line in (text or "").splitlines():
            s = line.strip()
            if not s or s.upper() == "WEBVTT":
                continue
            if s.isdigit():          # índice de cue (SRT)
                continue
            if "-->" in s:           # linha de tempo (00:00:01 --> 00:00:04)
                continue
            out.append(s)
        return "\n".join(out)

    def _import_meeting_from_file(self):
        """Cria uma reunião a partir de transcrição(ões) externa(s) e roda a análise."""
        exts = "*.txt *.md *.vtt *.srt *.log *.json *.csv *.pdf *.docx *.epub"
        paths, _ = QFileDialog.getOpenFileNames(
            self, t("Importar reunião de arquivo(s)"), "",
            t("Transcrições (texto, VTT/SRT, PDF, DOCX…)") + f" ({exts});;"
            + t("Todos os arquivos") + " (*)")
        if not paths:
            return
        from maestro_local.study.ingest import extract_text
        parts = []
        for p in paths:
            pth = Path(p)
            try:
                data = pth.read_bytes()
            except Exception as e:  # noqa: BLE001
                self.status_label.setText(t("Erro ao ler arquivo: {error}").format(error=e))
                return
            text = extract_text(data, pth.name)
            if pth.suffix.lower() in (".vtt", ".srt"):
                text = self._clean_subtitle(text)
            text = (text or "").strip()
            if not text:
                continue
            parts.append(f"### {pth.name}\n{text}" if len(paths) > 1 else text)
        transcript = "\n\n".join(parts).strip()
        if not transcript:
            self.status_label.setText(t("Não foi possível extrair texto dos arquivos."))
            return

        # Nova reunião a partir do import (estado limpo, novo registro).
        idx = self.kind_combo.findData("meeting")
        if idx >= 0:
            self.kind_combo.setCurrentIndex(idx)
        self._current = {"transcript": transcript, "duration": 0.0, "language": "",
                         "audio_path": "", "rec_id": None, "title": ""}
        self._live_transcript = transcript
        self._live_pending = ""
        self._live_state = empty_live_state()
        self._refresh_live_panels()
        self._render_questions([])
        self.live_box.setVisible(False)
        self.live_transcript_edit.clear()
        self.transcript_label.setVisible(True)
        self.transcript_edit.setVisible(True)
        self._set_transcript_text(transcript)
        self.result_edit.clear()
        self.result_edit.setVisible(False)
        self._persist_recording()   # já aparece no histórico com a transcrição importada
        self._load_history()

        if self._provider_ready():
            self.status_label.setText(t("Arquivo importado. Gerando análise..."))
            self._analyze()          # resumo + plano/dicas/ações/decisões/perguntas
        else:
            self.status_label.setText(
                t("Arquivo importado como reunião. Configure um provedor de IA para gerar a análise."))

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
        self.agent.analyze(
            kind, transcript, self.topic_input.text().strip(),
            self._current.get("duration", 0.0), self._current.get("language", ""))

        # Se o assistente ao vivo NÃO foi usado (abas vazias), gera as tabelas de
        # itens (plano, dicas, ações, decisões, perguntas) a partir da transcrição
        # completa — a mesma extração do ao vivo.
        has_live = any(self._live_state.get(k) for k in
                       ("plan", "tips", "action_items", "decisions", "questions"))
        if not has_live:
            self._start_analyze_extract(transcript)

    def _start_analyze_extract(self, transcript, keep_state: bool = False):
        """Gera/revisa os itens a partir da transcrição.

        `keep_state=True` (revisão após editar o texto) envia o estado ATUAL ao
        agente, que revisa mantendo o que continua válido — inclusive as
        respostas já dadas nas perguntas.
        """
        from maestro_local.transcricoes.live_assistant import EMPTY_STATE
        base = dict(self._live_state) if keep_state else dict(EMPTY_STATE)
        if not keep_state:
            self._live_state = dict(EMPTY_STATE)
            self._refresh_live_panels()
        self._live_transcript = transcript
        self.live_transcript_edit.setPlainText(transcript)
        self.live_box.setVisible(True)
        ai_ok = self._provider_ready()
        self.ask_input.setEnabled(ai_ok)
        self.ask_btn.setEnabled(ai_ok)
        self.live_status.setText(
            t("Revisando os itens com o texto editado...") if keep_state
            else t("Gerando itens (plano, ações, decisões, perguntas)..."))
        self.agent.extract(base, transcript, context=self._meeting_context())

    def _on_analyze_extracted(self, state: dict):
        self._live_state = self._preserve_answers(state)
        self._autosave_live_state()
        self._refresh_live_panels()
        self.live_status.setText(t("Itens gerados a partir da transcrição."))

    def _on_analyze_extract_error(self, err: str):
        self.live_status.setText(t("Erro ao gerar itens: {error}").format(error=err))

    def _on_analyzed(self, payload):
        md, summary, title, tags, duration, language = payload
        self.analyze_btn.setEnabled(True)
        self.result_edit.setVisible(True)
        self._set_result_markdown(md)
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

    # --------------------- Visualização do Markdown --------------------
    def _set_result_markdown(self, md: str):
        """Define o resumo, respeitando o modo atual (código x visualização)."""
        self._md_source = md or ""
        if self._md_preview:
            self.result_edit.setMarkdown(self._md_source)
            self.result_edit.setReadOnly(True)
        else:
            self.result_edit.setPlainText(self._md_source)
            self.result_edit.setReadOnly(False)

    def _current_result_md(self) -> str:
        """Fonte Markdown atual (no preview, o campo mostra HTML renderizado)."""
        return self._md_source if self._md_preview else self.result_edit.toPlainText()

    def _toggle_md_view(self):
        if not self._md_preview:
            # Indo para a visualização: captura edições feitas no código.
            self._md_source = self.result_edit.toPlainText()
        self._md_preview = not self._md_preview
        self._set_result_markdown(self._md_source)
        self.md_view_btn.setText(t("✎ Código") if self._md_preview else t("👁 Visualizar"))

    # ------------------------- Meu Dia -------------------------
    def _save_to_day(self):
        # Usa o resumo de IA se houver; senão, salva a própria transcrição
        md = self._current_result_md().strip()
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
        summary_md = (self._current.get("markdown") or self._current_result_md() or "").strip()
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
            prep=self.prep_edit.toPlainText().strip(),
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
    def _rec_name(self, r) -> str:
        """Nome da reunião com a data/hora de criação como PREFIXO."""
        when = r["created_at"].strftime("%d/%m/%Y %H:%M") if r["created_at"] else ""
        base = (r["title"] or r["topic"] or "").strip()
        if base and when:
            return f"{when} — {base}"
        return base or when or t("(sem título)")

    def _load_history(self):
        # Evita re-persistir ordem enquanto repovoa a lista.
        self.history.blockSignals(True)
        self.history.clear()
        query = self.history_panel.query()
        show_archived = self.history_panel.show_archived()
        try:
            for r in repository.list_recent(show_archived=show_archived):
                hay = f"{r['title']} {r['topic']} {r['transcript']}".lower()
                if query and query not in hay:
                    continue
                icon = "📓" if r["kind"] == "study" else "🗣"
                archived = "  🗄" if r["archived_at"] else ""
                item = QListWidgetItem(f"{icon}  {self._rec_name(r)}{archived}")
                item.setData(Qt.UserRole, r["rec_id"])
                self.history.addItem(item)
        finally:
            self.history.blockSignals(False)
        # Estado vazio: orienta em vez de deixar uma lista em branco.
        self.history_panel.set_empty_state(self.history.count() == 0, filtering=bool(query))

    def _history_context_menu(self, pos):
        item = self.history.itemAt(pos)
        if item is None:
            return
        rec_id = item.data(Qt.UserRole)
        archived = repository.is_archived(rec_id)
        menu = QMenu(self.history)
        menu.addAction(t("Abrir"), lambda: self._open_recording(item))
        menu.addAction(
            t("Desarquivar") if archived else t("Arquivar"),
            lambda: self._archive_recording(rec_id, not archived))
        menu.addSeparator()
        menu.addAction(t("Excluir"), lambda: self._delete_recording(rec_id))
        menu.exec(self.history.mapToGlobal(pos))

    def _archive_recording(self, rec_id, archive: bool):
        repository.set_archived(rec_id, archive)
        self.status_label.setText(
            t("Reunião arquivada.") if archive else t("Reunião desarquivada."))
        self._load_history()

    def _delete_recording(self, rec_id):
        resp = QMessageBox.question(
            self, t("Excluir reunião"),
            t("Excluir esta reunião permanentemente? Esta ação não pode ser desfeita."),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        repository.delete(rec_id)
        if self._current.get("rec_id") == rec_id:
            self._current["rec_id"] = None
        self.status_label.setText(t("Reunião excluída."))
        self._load_history()

    def _persist_history_order(self, *args):
        """Grava a ordem manual (sort_order) após arrastar itens no histórico."""
        repository.save_order([self.history.item(i).data(Qt.UserRole)
                               for i in range(self.history.count())])

    def _reset_outputs(self):
        """Limpa apenas as SAÍDAS (transcrição, resumo, itens ao vivo, perguntas)
        e o vínculo com a gravação — mantém preparação/contexto (entradas)."""
        self._current["rec_id"] = None
        self._set_transcript_text("")
        self.transcript_label.setVisible(True)
        self.transcript_edit.setVisible(True)
        self._md_preview = False
        self._md_source = ""
        self.result_edit.clear()
        self.result_edit.setReadOnly(False)
        self.result_edit.setVisible(False)
        self.md_view_btn.setText(t("👁 Visualizar"))
        self.save_day_btn.setEnabled(False)
        self._live_transcript = ""
        self._live_pending = ""
        self._live_state = empty_live_state()
        self._refresh_live_panels()
        self._render_questions([])
        self.live_transcript_edit.clear()
        self.live_box.setVisible(False)
        self.ask_answer.setVisible(False)

    def _new_meeting(self):
        """Começa uma reunião do zero: limpa saídas E entradas (preparação/contexto)."""
        if self.is_recording():
            self.status_label.setText(t("Pare a gravação atual antes de iniciar uma nova reunião."))
            return
        self._current = {"transcript": "", "duration": 0.0, "language": "",
                         "audio_path": "", "rec_id": None, "title": ""}
        self._reset_outputs()
        # Entradas (preparação/contexto/tópico)
        self.topic_input.clear()
        self.prep_edit.clear()
        self._context_items = []
        self._render_context()
        if self.screen_watch_check.isChecked():
            self.screen_watch_check.setChecked(False)
        self._screen_watch_text = ""
        self.history.clearSelection()
        self.status_label.setText(t("Nova reunião — campos limpos."))

    def _open_recording(self, item):
        rec_id = item.data(Qt.UserRole)
        r = repository.get(rec_id)
        if not r:
            return
        # O estado de trabalho passa a apontar para ESTA gravação (rec_id
        # correto para reanalisar/salvar sem sobrescrever outra).
        self._current = {
            "rec_id": r["rec_id"],
            "transcript": r["transcript"],
            "markdown": r["markdown"],
            "summary_json": r["summary_json"],
            "duration": r["duration"],
            "language": r["language"],
            "audio_path": r["audio_path"],
            "title": r["title"],
            "tags": r["tags"],
        }
        # Restaura os itens do assistente salvos com ESTA gravação (plano,
        # dicas, ações, decisões, perguntas) — reabre como estava.
        self._live_transcript = r["transcript"]
        self._live_pending = ""
        self._meeting.load_live_state_json(r["live_state_json"])
        self._refresh_live_panels()
        self.live_transcript_edit.setPlainText(r["transcript"])
        has_items = self._meeting.has_live_items()
        self.live_box.setVisible(has_items)
        if has_items:
            self.live_status.setText(t("Itens salvos desta reunião."))

        # Mostra a transcrição + resumo estáticos desta gravação.
        self.transcript_label.setVisible(True)
        self.transcript_edit.setVisible(True)
        self._set_transcript_text(r["transcript"])
        self.result_edit.setVisible(bool(r["markdown"]))
        self._set_result_markdown(r["markdown"])
        self.save_day_btn.setEnabled(bool(r["markdown"]))
        idx = self.kind_combo.findData(r["kind"])
        if idx >= 0:
            self.kind_combo.setCurrentIndex(idx)
        when = r["created_at"].strftime("%d/%m/%Y %H:%M") if r["created_at"] else ""
        self.status_label.setText(t("Gravação de {when}").format(when=when))
