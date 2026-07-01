"""Transcrições: grava reuniões/estudos, transcreve e resume com IA."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import (
    get_active_ai_provider,
    get_active_workspace_id,
    load_config,
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


class TranscricoesView(QWidget):
    def __init__(self):
        super().__init__()
        self._session = None
        self._transcriber = None
        self._analyzer = None
        self._elapsed = 0
        self._current = {"transcript": "", "duration": 0.0, "language": "", "audio_path": ""}

        # Estado do assistente ao vivo
        self._live_transcriber = None
        self._live_extractor = None
        self._live_asker = None
        self._live_transcript = ""       # transcrição ao vivo acumulada
        self._live_pending = ""          # texto novo ainda não enviado à IA
        self._live_secs_since = 0        # segundos desde a última extração
        self._live_state = {"action_items": [], "decisions": [], "open_questions": []}

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # ---- Coluna esquerda: histórico ----
        left = QVBoxLayout()
        left.setSpacing(6)
        htitle = QLabel(t("Histórico"))
        htitle.setProperty("class", "cardTitle")
        left.addWidget(htitle)
        self.search = QLineEdit()
        self.search.setPlaceholderText(t("Buscar nas gravações..."))
        self.search.textChanged.connect(self._load_history)
        left.addWidget(self.search)
        self.history = QListWidget()
        self.history.setFixedWidth(240)
        self.history.itemClicked.connect(self._open_recording)
        left.addWidget(self.history, 1)
        root.addLayout(left)

        # ---- Coluna direita: gravação + transcrição ----
        right = QVBoxLayout()
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
        self.record_btn = QPushButton(t("● Gravar"))
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
            t("Transcreve e extrai ações/decisões durante a gravação (mais uso de CPU/IA).")
        )
        row4.addWidget(self.live_check)
        cl.addLayout(row4)

        right.addWidget(ctrl)

        # ---- Painel do assistente ao vivo (visível só durante gravação ao vivo) ----
        self.live_box = self._build_live_box()
        self.live_box.setVisible(False)
        right.addWidget(self.live_box, 3)

        # Progresso de transcrição
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        right.addWidget(self.status_label)

        # Transcrição
        right.addWidget(QLabel(t("Transcrição:")))
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText(t("A transcrição aparecerá aqui..."))
        right.addWidget(self.transcript_edit, 1)

        # Ações
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.analyze_btn = QPushButton(t("Analisar com IA"))
        self.analyze_btn.setFixedHeight(32)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._analyze)
        actions.addWidget(self.analyze_btn)
        self.save_day_btn = QPushButton(t("Salvar no Meu Dia"))
        self.save_day_btn.setFixedHeight(32)
        self.save_day_btn.setCursor(Qt.PointingHandCursor)
        self.save_day_btn.clicked.connect(self._save_to_day)
        self.save_day_btn.setEnabled(False)
        actions.addWidget(self.save_day_btn)
        actions.addStretch()
        actions.addWidget(QLabel(t("Projeto:")))
        self.proj_combo = QComboBox()
        self.proj_combo.setMinimumWidth(140)
        actions.addWidget(self.proj_combo)
        self.tasks_btn = QPushButton(t("Criar tarefas das ações"))
        self.tasks_btn.setFixedHeight(32)
        self.tasks_btn.setCursor(Qt.PointingHandCursor)
        self.tasks_btn.clicked.connect(self._actions_to_tasks)
        actions.addWidget(self.tasks_btn)
        right.addLayout(actions)

        # Resultado markdown
        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText(t("O resumo estruturado aparecerá aqui após a análise."))
        self.result_edit.setVisible(False)
        right.addWidget(self.result_edit, 1)

        root.addLayout(right, 1)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        self._populate_devices()
        self._populate_projects()
        self._load_history()
        self._check_provider()

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

    def _on_kind_changed(self):
        self.topic_input.setVisible(self.kind_combo.currentData() == "study")

    # ------------------------- Painel ao vivo -------------------------
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

        # Transcrição ao vivo em cima (altura limitada)
        v.addWidget(QLabel(t("Transcrição ao vivo")))
        self.live_transcript_edit = QTextEdit()
        self.live_transcript_edit.setReadOnly(True)
        self.live_transcript_edit.setPlaceholderText(t("A transcrição aparecerá aqui em tempo real..."))
        self.live_transcript_edit.setMaximumHeight(120)
        v.addWidget(self.live_transcript_edit)

        # Abas do assistente em largura total (as 5 cabem sem sobrepor)
        self.live_tabs = QTabWidget()
        self.live_tabs.setMinimumHeight(160)
        self.live_plan_list = QListWidget()
        self.live_tips_list = QListWidget()
        self.live_actions_list = QListWidget()
        self.live_decisions_list = QListWidget()
        self.live_questions_list = QListWidget()
        self.live_tabs.addTab(self.live_plan_list, t("Plano"))
        self.live_tabs.addTab(self.live_tips_list, t("Dicas"))
        self.live_tabs.addTab(self.live_actions_list, t("Ações"))
        self.live_tabs.addTab(self.live_decisions_list, t("Decisões"))
        self.live_tabs.addTab(self.live_questions_list, t("Perguntas"))
        v.addWidget(self.live_tabs, 1)

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
        self.record_btn.setText(t("● Gravar"))
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

    def _start_live(self):
        from maestro_local.transcricoes.transcriber import LiveTranscriber
        _, lang = _whisper_settings()
        # Reseta o estado ao vivo
        self._live_transcript = ""
        self._live_pending = ""
        self._live_secs_since = 0
        self._live_state = {
            "action_items": [], "decisions": [], "open_questions": [], "plan": [], "tips": [],
        }
        self._live_context = self._meeting_context()
        self.live_transcript_edit.clear()
        self.live_plan_list.clear()
        self.live_tips_list.clear()
        self.live_actions_list.clear()
        self.live_decisions_list.clear()
        self.live_questions_list.clear()
        self.ask_answer.setVisible(False)
        self.live_box.setVisible(True)
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
        self.live_questions_list.clear()
        for q in self._live_state.get("open_questions", []):
            self.live_questions_list.addItem(f"? {q}")

        def _tab(idx, label, widget):
            n = widget.count()
            self.live_tabs.setTabText(idx, t(label) + (f" ({n})" if n else ""))

        _tab(0, "Plano", self.live_plan_list)
        _tab(1, "Dicas", self.live_tips_list)
        _tab(2, "Ações", self.live_actions_list)
        _tab(3, "Decisões", self.live_decisions_list)
        _tab(4, "Perguntas", self.live_questions_list)

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
