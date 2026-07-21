"""Orquestrador dos trabalhos de IA de uma reunião.

A view antes criava, guardava e limpava sete QThreads na mão, cada um com o
seu par de atributos e conexões. Aqui isso vira um objeto só: os workers são
propriedade do serviço, que os mantém vivos enquanto rodam, libera a
referência ao terminar e reemite os resultados como sinais próprios.

O serviço não conhece widgets — só recebe texto/imagem e devolve resultado.
Quem decide o que mostrar continua sendo a view.

Fora daqui fica só o ``LiveTranscriber``: ele é um fluxo contínuo preso à
sessão de áudio da gravação, não uma chamada de ida e volta como as demais.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from maestro_local.i18n import t


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
                self.done.emit((md, summary, notes.topic or t("Estudo"), notes.tags,
                                self.duration, self.language))
            else:
                s = assistants.analyze_meeting(self.transcript, self.duration, self.language)
                md = markdown_gen.meeting_to_markdown(s, date_str)
                summary = {
                    "title": s.title, "key_points": s.key_points,
                    "decisions": s.decisions,
                    "action_items": [a.__dict__ for a in s.action_items],
                    "open_questions": s.open_questions,
                }
                self.done.emit((md, summary, s.title or t("Reunião"), s.tags,
                                self.duration, self.language))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class MeetingAgentService(QObject):
    """Ponto único de entrada para os trabalhos de IA de uma reunião."""

    # Transcrição de arquivo (Whisper)
    transcribe_progress = Signal(int)
    transcribed = Signal(object)
    transcribe_failed = Signal(str)

    # Análise (resumo + markdown)
    analyzed = Signal(object)
    analyze_failed = Signal(str)

    # Extração de itens durante a gravação
    live_extracted = Signal(dict)
    live_extract_failed = Signal(str)

    # Extração de itens a partir da transcrição inteira
    extracted = Signal(dict)
    extract_failed = Signal(str)

    # Perguntar à reunião
    answered = Signal(str)
    ask_failed = Signal(str)

    # Leitura de imagens: anexos de contexto e o observador de tela
    vision_done = Signal(str, str)      # (label, texto)
    vision_failed = Signal(str, str)    # (label, erro)
    screen_read = Signal(str, str)
    screen_failed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._transcriber = None
        self._analyzer = None
        self._live_extractor = None
        self._extractor = None
        self._asker = None
        self._screen_reader = None
        self._vision_workers: list = []   # anexos podem ser lidos em paralelo

    # ---------------------------- estado ----------------------------
    def is_extracting_live(self) -> bool:
        return self._live_extractor is not None

    def is_extracting(self) -> bool:
        return self._extractor is not None

    def is_reading_screen(self) -> bool:
        return self._screen_reader is not None

    # -------------------------- transcrição --------------------------
    def transcribe(self, audio_path: Path, model: str, language: str) -> None:
        from maestro_local.transcricoes.transcriber import TranscriberWorker
        w = TranscriberWorker(audio_path, model, language)
        w.progress.connect(self.transcribe_progress)
        w.finished_ok.connect(self.transcribed)
        w.finished_error.connect(self.transcribe_failed)
        w.finished.connect(lambda: setattr(self, "_transcriber", None))
        self._transcriber = w
        w.start()

    # ---------------------------- análise ----------------------------
    def analyze(self, kind: str, transcript: str, topic: str,
                duration: float, language: str) -> None:
        w = AnalyzeWorker(kind, transcript, topic, duration, language)
        w.done.connect(self.analyzed)
        w.failed.connect(self.analyze_failed)
        w.finished.connect(lambda: setattr(self, "_analyzer", None))
        self._analyzer = w
        w.start()

    # --------------------------- extração ---------------------------
    def extract_live(self, state: dict, new_text: str, context: str = "") -> None:
        """Passada incremental durante a gravação. Ignora se já há uma em curso —
        senão duas extrações concorrentes sobrescreveriam o estado uma da outra."""
        if self._live_extractor is not None:
            return
        from maestro_local.transcricoes.live_assistant import LiveExtractWorker
        w = LiveExtractWorker(dict(state), new_text, context=context)
        w.done.connect(self.live_extracted)
        w.failed.connect(self.live_extract_failed)
        w.finished.connect(lambda: setattr(self, "_live_extractor", None))
        self._live_extractor = w
        w.start()

    def extract(self, state: dict, transcript: str, context: str = "") -> None:
        """Gera/revisa os itens a partir da transcrição completa."""
        from maestro_local.transcricoes.live_assistant import LiveExtractWorker
        w = LiveExtractWorker(dict(state), transcript, context=context)
        w.done.connect(self.extracted)
        w.failed.connect(self.extract_failed)
        w.finished.connect(lambda: setattr(self, "_extractor", None))
        self._extractor = w
        w.start()

    # ---------------------------- perguntar ----------------------------
    def ask(self, transcript: str, question: str, context: str = "") -> None:
        from maestro_local.transcricoes.live_assistant import LiveAskWorker
        w = LiveAskWorker(transcript, question, context=context)
        w.answered.connect(self.answered)
        w.failed.connect(self.ask_failed)
        w.finished.connect(lambda: setattr(self, "_asker", None))
        self._asker = w
        w.start()

    # ------------------------------ visão ------------------------------
    def read_image(self, label: str, image_bytes: bytes, mime: str = "image/png") -> None:
        """Lê um anexo de contexto. Vários podem rodar ao mesmo tempo."""
        from maestro_local.transcricoes.live_assistant import VisionContextWorker
        w = VisionContextWorker(label, image_bytes, mime)
        w.done.connect(self.vision_done)
        w.failed.connect(self.vision_failed)
        w.finished.connect(
            lambda w=w: self._vision_workers.remove(w) if w in self._vision_workers else None)
        self._vision_workers.append(w)
        w.start()

    def read_screen(self, label: str, image_bytes: bytes, mime: str = "image/png") -> None:
        """Captura periódica do monitor observado — no máximo uma por vez, para
        não acumular chamadas de visão (caras) se a IA estiver lenta."""
        if self._screen_reader is not None:
            return
        from maestro_local.transcricoes.live_assistant import VisionContextWorker
        w = VisionContextWorker(label, image_bytes, mime)
        w.done.connect(self.screen_read)
        w.failed.connect(self.screen_failed)
        w.finished.connect(lambda: setattr(self, "_screen_reader", None))
        self._screen_reader = w
        w.start()

    # ------------------------------ parada ------------------------------
    def stop_all(self, msecs: int = 3000) -> None:
        """Espera os trabalhos em andamento — usado ao fechar a aplicação."""
        workers = [self._transcriber, self._analyzer, self._live_extractor,
                   self._extractor, self._asker, self._screen_reader]
        for w in workers + list(self._vision_workers):
            if w is not None and w.isRunning():
                w.wait(msecs)
