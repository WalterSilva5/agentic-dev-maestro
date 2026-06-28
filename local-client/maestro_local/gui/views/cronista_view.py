"""Cronista: grava reuniões/estudos, transcreve e resume com IA."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import (
    get_active_ai_provider,
    get_active_workspace_id,
    load_config,
)
from maestro_local.cronista import audio as audio_backend
from maestro_local.cronista.constants import WHISPER_DEFAULT_LANGUAGE, WHISPER_DEFAULT_MODEL
from maestro_local.db.models import DATA_DIR, Recording, get_session
from maestro_local.gui.theme import current_theme


def _whisper_settings():
    cfg = load_config().get("settings", {}).get("cronista", {})
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
            from maestro_local.cronista import assistants, markdown_gen
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            if self.kind == "study":
                notes = assistants.analyze_study(self.transcript, self.topic, self.duration)
                md = markdown_gen.study_to_markdown(notes, date_str)
                summary = {
                    "topic": notes.topic, "summary": notes.summary,
                    "key_concepts": [c.__dict__ for c in notes.key_concepts],
                    "exercises": [e.__dict__ for e in notes.practical_exercises],
                }
                self.done.emit((md, summary, notes.topic or "Estudo", notes.tags, self.duration, self.language))
            else:
                s = assistants.analyze_meeting(self.transcript, self.duration, self.language)
                md = markdown_gen.meeting_to_markdown(s, date_str)
                summary = {
                    "title": s.title, "key_points": s.key_points,
                    "decisions": s.decisions,
                    "action_items": [a.__dict__ for a in s.action_items],
                }
                self.done.emit((md, summary, s.title or "Reunião", s.tags, self.duration, self.language))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class CronistaView(QWidget):
    def __init__(self):
        super().__init__()
        self._session = None
        self._transcriber = None
        self._analyzer = None
        self._elapsed = 0
        self._current = {"transcript": "", "duration": 0.0, "language": "", "audio_path": ""}

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # ---- Coluna esquerda: histórico ----
        left = QVBoxLayout()
        left.setSpacing(6)
        htitle = QLabel("Histórico")
        htitle.setProperty("class", "cardTitle")
        left.addWidget(htitle)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar nas gravações...")
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

        title = QLabel("Cronista")
        title.setObjectName("sectionTitle")
        right.addWidget(title)

        subtitle = QLabel(
            "Grave reuniões e estudos, transcreva localmente com Whisper e gere "
            "resumos estruturados com IA."
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
        row1.addWidget(QLabel("Tipo:"))
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Reunião", "meeting")
        self.kind_combo.addItem("Estudo", "study")
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        row1.addWidget(self.kind_combo)
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("Tópico do estudo")
        self.topic_input.setVisible(False)
        row1.addWidget(self.topic_input, 1)
        cl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(QLabel("Microfone:"))
        self.mic_combo = QComboBox()
        row2.addWidget(self.mic_combo, 1)
        cl.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(8)
        row3.addWidget(QLabel("Áudio do sistema:"))
        self.monitor_combo = QComboBox()
        row3.addWidget(self.monitor_combo, 1)
        cl.addLayout(row3)

        row4 = QHBoxLayout()
        row4.setSpacing(8)
        self.record_btn = QPushButton("● Gravar")
        self.record_btn.setFixedHeight(34)
        self.record_btn.setCursor(Qt.PointingHandCursor)
        self.record_btn.clicked.connect(self._toggle_record)
        row4.addWidget(self.record_btn)
        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-family: monospace; font-size: 16px;")
        row4.addWidget(self.timer_label)
        row4.addStretch()
        cl.addLayout(row4)

        right.addWidget(ctrl)

        # Progresso de transcrição
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("subtitle")
        right.addWidget(self.status_label)

        # Transcrição
        right.addWidget(QLabel("Transcrição:"))
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText("A transcrição aparecerá aqui...")
        right.addWidget(self.transcript_edit, 1)

        # Ações
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.analyze_btn = QPushButton("Analisar com IA")
        self.analyze_btn.setFixedHeight(32)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._analyze)
        actions.addWidget(self.analyze_btn)
        self.save_day_btn = QPushButton("Salvar no Meu Dia")
        self.save_day_btn.setFixedHeight(32)
        self.save_day_btn.setCursor(Qt.PointingHandCursor)
        self.save_day_btn.clicked.connect(self._save_to_day)
        self.save_day_btn.setEnabled(False)
        actions.addWidget(self.save_day_btn)
        actions.addStretch()
        right.addLayout(actions)

        # Resultado markdown
        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText("O resumo estruturado aparecerá aqui após a análise.")
        self.result_edit.setVisible(False)
        right.addWidget(self.result_edit, 1)

        root.addLayout(right, 1)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        self._populate_devices()
        self._load_history()
        self._check_provider()

    def _check_provider(self):
        provider = get_active_ai_provider()
        t = current_theme()
        msgs = []
        if not audio_backend.parec_available():
            msgs.append("⚠ parec/pactl não encontrados — gravação indisponível (instale pulseaudio-utils).")
        if not provider or not provider.get("model"):
            msgs.append("⚠ Provedor de IA não configurado — a análise com IA ficará indisponível (Configurações → Provedores de IA).")
        if msgs:
            self.banner.setText("\n".join(msgs))
            self.banner.setStyleSheet(
                f"background: {t.bg_badge}; color: {t.text_secondary}; border: 1px solid {t.border}; "
                f"border-radius: 8px; padding: 8px 12px; font-size: 12px;"
            )
            self.banner.setVisible(True)
            self.analyze_btn.setEnabled(bool(provider and provider.get("model")))
        else:
            self.banner.setVisible(False)
            self.analyze_btn.setEnabled(True)

    def _populate_devices(self):
        self.mic_combo.clear()
        self.monitor_combo.clear()
        self.monitor_combo.addItem("Nenhum", None)
        sources = audio_backend.list_sources()
        for s in sources:
            if s.is_monitor:
                self.monitor_combo.addItem(s.description, s.name)
            else:
                self.mic_combo.addItem(s.description, s.name)
        if self.mic_combo.count() == 0:
            self.mic_combo.addItem("Nenhum microfone", None)

    def _on_kind_changed(self):
        self.topic_input.setVisible(self.kind_combo.currentData() == "study")

    # ------------------------- Gravação -------------------------
    def toggle_record_external(self):
        """Chamado por atalho global (thread-safe via QTimer)."""
        QTimer.singleShot(0, self._toggle_record)

    def _toggle_record(self):
        if self._session and self._session.is_recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self):
        if not audio_backend.parec_available():
            self.status_label.setText("parec indisponível — não é possível gravar.")
            return
        mic_name = self.mic_combo.currentData()
        mon_name = self.monitor_combo.currentData()
        mic = next((s for s in audio_backend.list_sources() if s.name == mic_name), None) if mic_name else None
        mon = next((s for s in audio_backend.list_sources() if s.name == mon_name), None) if mon_name else None
        if not mic and not mon:
            self.status_label.setText("Selecione ao menos uma fonte de áudio.")
            return
        try:
            self._session = audio_backend.RecordingSession(mic, mon)
            self._session.start()
        except Exception as e:  # noqa: BLE001
            self.status_label.setText(f"Erro ao iniciar gravação: {e}")
            self._session = None
            return
        self._elapsed = 0
        self.timer_label.setText("00:00")
        self._tick.start()
        self.record_btn.setText("■ Parar")
        self.status_label.setText("Gravando...")

    def _stop_record(self):
        self._tick.stop()
        self.record_btn.setText("● Gravar")
        if not self._session:
            return
        out = _recordings_dir() / f"rec-{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
        try:
            path, duration = self._session.stop_and_save(out)
        except Exception as e:  # noqa: BLE001
            self.status_label.setText(f"Erro ao salvar áudio: {e}")
            self._session = None
            return
        self._session = None
        self._current["audio_path"] = str(path)
        self._current["duration"] = duration
        self.status_label.setText(f"Gravação salva ({duration:.0f}s). Transcrevendo...")
        self._transcribe(path)

    def _on_tick(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self.timer_label.setText(f"{m:02d}:{s:02d}")

    # ------------------------- Transcrição -------------------------
    def _transcribe(self, audio_path: Path):
        from maestro_local.cronista.transcriber import TranscriberWorker
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
        self.status_label.setText(
            f"Transcrição concluída ({result.language}, {len(result.segments)} segmentos)."
        )

    def _on_transcribe_error(self, err):
        self.progress.setVisible(False)
        self.status_label.setText(f"Erro na transcrição: {err}")

    # ------------------------- Análise IA -------------------------
    def _analyze(self):
        transcript = self.transcript_edit.toPlainText().strip()
        if not transcript:
            self.status_label.setText("Sem transcrição para analisar.")
            return
        provider = get_active_ai_provider()
        if not provider or not provider.get("model"):
            self.status_label.setText("Configure um provedor de IA primeiro.")
            return
        kind = self.kind_combo.currentData()
        self.analyze_btn.setEnabled(False)
        self.status_label.setText("Analisando com IA...")
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
        self._current.update({"markdown": md, "title": title, "tags": tags})

        # Persiste no banco
        s = get_session()
        try:
            rec = Recording(
                kind=self.kind_combo.currentData(),
                title=title,
                topic=self.topic_input.text().strip(),
                transcript=self.transcript_edit.toPlainText().strip(),
                summary_json=json.dumps(summary, ensure_ascii=False),
                markdown=md,
                duration=duration,
                language=language,
                audio_path=self._current.get("audio_path", ""),
                tags=json.dumps(tags or [], ensure_ascii=False),
            )
            s.add(rec)
            s.commit()
        finally:
            s.close()
        self.status_label.setText("Análise concluída e salva no histórico.")
        self._load_history()

    def _on_analyze_error(self, err):
        self.analyze_btn.setEnabled(True)
        self.status_label.setText(f"Erro na análise: {err}")

    # ------------------------- Meu Dia -------------------------
    def _save_to_day(self):
        md = self.result_edit.toPlainText().strip()
        if not md:
            return
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
        self.status_label.setText("Resumo adicionado ao relatório do Meu Dia.")

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
                item = QListWidgetItem(f"{icon}  {r.title or '(sem título)'}\n{when}")
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
            self.status_label.setText(f"Gravação de {r.created_at.strftime('%d/%m/%Y %H:%M') if r.created_at else ''}")
        finally:
            s.close()
