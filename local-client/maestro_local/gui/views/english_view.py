"""Praticar Inglês: conversação com um parceiro de IA por nível, com entrada
por voz (whisper offline) e feedback gentil (correção + sugestão + vocabulário
com pronúncia em português). Desktop, in-process."""
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t

LEVELS = [
    ("BEGINNER", "Iniciante"),
    ("INTERMEDIATE", "Intermediário"),
    ("ADVANCED", "Avançado"),
    ("FREE", "Livre"),
]


class _TurnWorker(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, mode, level, topic, history, message="", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.level = level
        self.topic = topic
        self.history = history
        self.message = message

    def run(self):
        from maestro_local import english
        try:
            if self.mode == "start":
                res = english.start(self.level, self.topic)
            else:
                res = english.converse(self.level, self.topic, self.history, self.message)
            self.done.emit(res)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class EnglishView(QWidget):
    def __init__(self):
        super().__init__()
        self._history = []       # [{role, text}]
        self._busy = False
        self._worker = None
        self._recorder = None
        self._rec_session = None
        self._transcriber = None
        self._tmp_wav = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(_t("Praticar Inglês"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel(_t("Converse em inglês com a IA no seu nível. Fale ou escreva; receba correções e vocabulário."))
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Configuração da sessão
        cfg = QHBoxLayout()
        cfg.addWidget(QLabel(_t("Nível:")))
        self.level = QComboBox()
        for val, label in LEVELS:
            self.level.addItem(_t(label), val)
        self.level.setCurrentIndex(1)
        cfg.addWidget(self.level)
        self.topic = QLineEdit()
        self.topic.setPlaceholderText(_t("Tema (opcional): viagem, comida, trabalho..."))
        cfg.addWidget(self.topic, 1)
        self.start_btn = QPushButton(_t("Iniciar conversa"))
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start)
        cfg.addWidget(self.start_btn)
        layout.addLayout(cfg)

        # Chat
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setSpacing(8)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_container)
        layout.addWidget(self.scroll, 1)

        # Entrada
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText(_t("Escreva em inglês (ou use o microfone)..."))
        self.input.returnPressed.connect(self._send)
        self.input.setEnabled(False)
        row.addWidget(self.input, 1)
        self.rec_btn = QPushButton("🎤")
        self.rec_btn.setToolTip(_t("Gravar voz"))
        self.rec_btn.setFixedWidth(44)
        self.rec_btn.setEnabled(False)
        self.rec_btn.setCursor(Qt.PointingHandCursor)
        self.rec_btn.clicked.connect(self._toggle_record)
        row.addWidget(self.rec_btn)
        self.send_btn = QPushButton(_t("Enviar"))
        self.send_btn.setEnabled(False)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        self.status = QLabel("")
        self.status.setObjectName("subtitle")
        layout.addWidget(self.status)

    def refresh(self):
        pass

    # ---- Fluxo da conversa ----
    def _set_busy(self, busy, status=""):
        self._busy = busy
        started = self._conversa_iniciada()
        self.input.setEnabled(not busy and started)
        self.send_btn.setEnabled(not busy and started)
        self.rec_btn.setEnabled(not busy and started)
        self.start_btn.setEnabled(not busy)
        self.status.setText(status)

    def _conversa_iniciada(self):
        return len(self._history) > 0

    def _start(self):
        self._history = []
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.status.setText(_t("Pensando..."))
        self.start_btn.setEnabled(False)
        self._worker = _TurnWorker("start", self.level.currentData(), self.topic.text().strip(), [])
        self._worker.done.connect(self._on_opening)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_opening(self, res):
        reply = res.get("reply", "")
        self._history.append({"role": "assistant", "text": reply})
        self._add_assistant(reply, res.get("suggestion", ""))
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.rec_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.status.setText("")
        self.input.setFocus()

    def _send(self):
        if self._busy:
            return
        text = self.input.text().strip()
        if not text or not self._conversa_iniciada():
            return
        self.input.clear()
        self._add_user(text)
        self._history.append({"role": "user", "text": text})
        self._set_busy(True, _t("Pensando..."))
        self._worker = _TurnWorker("message", self.level.currentData(),
                                   self.topic.text().strip(), list(self._history), text)
        self._worker.done.connect(self._on_reply)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_reply(self, res):
        # anexa correção/feedback/vocab à última bolha do usuário
        self._attach_coach(res.get("feedback", ""), res.get("correction", ""), res.get("vocab", []))
        reply = res.get("reply", "")
        self._history.append({"role": "assistant", "text": reply})
        self._add_assistant(reply, res.get("suggestion", ""))
        self._set_busy(False)
        self.input.setFocus()

    def _on_failed(self, msg):
        self._set_busy(False)
        self.status.setText(_t("Erro") + f": {msg}")

    # ---- Bolhas de chat ----
    def _bubble(self, align_right, bg, border):
        wrap = QHBoxLayout()
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {border}; "
            f"border-radius: 10px; }}")
        frame.setMaximumWidth(560)
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(10, 8, 10, 8)
        inner.setSpacing(4)
        if align_right:
            wrap.addStretch()
            wrap.addWidget(frame)
        else:
            wrap.addWidget(frame)
            wrap.addStretch()
        holder = QWidget()
        holder.setLayout(wrap)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, holder)
        self._scroll_bottom()
        return inner

    def _add_assistant(self, reply, suggestion):
        t = current_theme()
        inner = self._bubble(False, t.bg_card, t.border)
        lbl = QLabel(reply)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setStyleSheet(f"color: {t.text_primary}; border: none; background: transparent;")
        inner.addWidget(lbl)
        if suggestion:
            sug = QLabel("💡 " + suggestion)
            sug.setWordWrap(True)
            sug.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; font-style: italic; "
                              f"border: none; background: transparent;")
            inner.addWidget(sug)

    def _add_user(self, text):
        t = current_theme()
        self._last_user_inner = self._bubble(True, t.accent_light, t.accent)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setStyleSheet(f"color: {t.text_primary}; border: none; background: transparent;")
        self._last_user_inner.addWidget(lbl)

    def _attach_coach(self, feedback, correction, vocab):
        inner = getattr(self, "_last_user_inner", None)
        if inner is None:
            return
        t = current_theme()
        if correction:
            corr = QLabel("✅ " + correction)
            corr.setWordWrap(True)
            corr.setStyleSheet(f"color: {t.success}; font-size: 12px; border: none; background: transparent;")
            inner.addWidget(corr)
        if feedback:
            fb = QLabel("📝 " + feedback)
            fb.setWordWrap(True)
            fb.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px; border: none; background: transparent;")
            inner.addWidget(fb)
        if vocab:
            chips = " · ".join(
                f"<b>{v['word']}</b> <i>{v['respell']}</i> — {v['meaning']}" for v in vocab)
            vb = QLabel("🗂 " + chips)
            vb.setWordWrap(True)
            vb.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; border: none; background: transparent;")
            inner.addWidget(vb)
        self._scroll_bottom()

    def _scroll_bottom(self):
        bar = self.scroll.verticalScrollBar()
        QApplication.processEvents()
        bar.setValue(bar.maximum())

    # ---- Voz (whisper) ----
    def _toggle_record(self):
        if self._rec_session is None:
            self._begin_record()
        else:
            self._end_record()

    def _begin_record(self):
        from maestro_local.transcricoes.audio import RecordingSession, default_mic, parec_available
        if not parec_available():
            self.status.setText(_t("Áudio indisponível (parec/pactl)."))
            return
        mic = default_mic()
        if mic is None:
            self.status.setText(_t("Microfone não encontrado."))
            return
        try:
            self._rec_session = RecordingSession(mic, None)
            self._rec_session.start()
        except Exception as e:  # noqa: BLE001
            self._rec_session = None
            self.status.setText(_t("Erro ao gravar") + f": {e}")
            return
        self.rec_btn.setText("⏹")
        self.status.setText(_t("Gravando... clique novamente para parar."))

    def _end_record(self):
        from maestro_local.transcricoes.transcriber import TranscriberWorker
        session = self._rec_session
        self._rec_session = None
        self.rec_btn.setText("🎤")
        if session is None:
            return
        fd, path = tempfile.mkstemp(suffix=".wav")
        import os
        os.close(fd)
        self._tmp_wav = Path(path)
        try:
            session.stop_and_save(self._tmp_wav)
        except Exception as e:  # noqa: BLE001
            self.status.setText(_t("Erro ao gravar") + f": {e}")
            return
        self.status.setText(_t("Transcrevendo..."))
        self.rec_btn.setEnabled(False)
        model = _whisper_model_size()
        self._transcriber = TranscriberWorker(self._tmp_wav, model, language="en")
        self._transcriber.finished_ok.connect(self._on_transcribed)
        self._transcriber.finished_error.connect(self._on_transcribe_error)
        self._transcriber.start()

    def _on_transcribed(self, result):
        self.rec_btn.setEnabled(self._conversa_iniciada())
        self.status.setText("")
        self._cleanup_wav()
        text = (getattr(result, "text", "") or "").strip()
        if not text:
            self.status.setText(_t("Não entendi o áudio. Tente de novo."))
            return
        self.input.setText(text)
        self._send()  # envia automaticamente o que você falou

    def _on_transcribe_error(self, msg):
        self.rec_btn.setEnabled(self._conversa_iniciada())
        self._cleanup_wav()
        self.status.setText(_t("Erro na transcrição") + f": {msg}")

    def _cleanup_wav(self):
        if self._tmp_wav and self._tmp_wav.exists():
            try:
                self._tmp_wav.unlink()
            except OSError:
                pass
        self._tmp_wav = None


def _whisper_model_size():
    from maestro_local.transcricoes.constants import WHISPER_DEFAULT_MODEL
    try:
        from maestro_local.config import load_config
        return (load_config().get("settings", {}).get("transcricoes", {})
                .get("whisper_model") or WHISPER_DEFAULT_MODEL)
    except Exception:  # noqa: BLE001
        return WHISPER_DEFAULT_MODEL
