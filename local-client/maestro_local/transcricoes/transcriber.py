"""Transcrição de áudio com faster-whisper em QThread."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .constants import (
    LIVE_MIN_SECONDS,
    LIVE_WINDOW_SECONDS,
    SAMPLE_RATE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEFAULT_MODEL,
    WHISPER_SUPPORTED_MODELS,
)

logger = logging.getLogger("maestro.transcricoes.transcription")

_cached_model = None
_cached_size = None


def _force_c_utf8_locale() -> None:
    """Força um locale com mensagens ASCII + ctype UTF-8.

    O QApplication do Qt reseta o LC_CTYPE para ascii. Quando o PyAV
    (usado pelo faster-whisper no resample) chama os.strerror() e o locale
    de mensagens é pt_BR, a mensagem vem acentuada e a decodificação ascii
    quebra. C.UTF-8 dá mensagens em inglês ASCII e ctype UTF-8, evitando o
    problema. Roda dentro da QThread de transcrição (à prova de reset do Qt).
    """
    import locale
    for loc in ("C.UTF-8", "C.utf8", "en_US.UTF-8"):
        try:
            locale.setlocale(locale.LC_ALL, loc)
            return
        except locale.Error:
            continue


def get_model(model_size: str = WHISPER_DEFAULT_MODEL, compute_type: str = WHISPER_COMPUTE_TYPE):
    global _cached_model, _cached_size
    if model_size not in WHISPER_SUPPORTED_MODELS:
        raise ValueError(f"Modelo Whisper inválido: {model_size}")
    if _cached_model is not None and _cached_size == model_size:
        return _cached_model
    from faster_whisper import WhisperModel
    logger.info("Carregando Whisper '%s' (compute=%s)...", model_size, compute_type)
    _cached_model = WhisperModel(model_size, device="auto", compute_type=compute_type)
    _cached_size = model_size
    return _cached_model


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    text: str
    segments: list[Segment] = field(default_factory=list)
    language: str = ""
    duration: float = 0.0


class TranscriberWorker(QThread):
    progress = Signal(int)
    segment_ready = Signal(str)
    finished_ok = Signal(object)
    finished_error = Signal(str)

    def __init__(self, audio_path: Path, model_size: str, language: str = "", parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self.model_size = model_size
        self.language = language

    def run(self) -> None:
        try:
            _force_c_utf8_locale()
            model = get_model(self.model_size)
            language = self.language or None
            segments_iter, info = model.transcribe(
                str(self.audio_path), language=language, beam_size=5, vad_filter=True,
            )
            total = info.duration or 0.0
            all_segments: list[Segment] = []
            parts: list[str] = []
            for seg in segments_iter:
                s = Segment(start=seg.start, end=seg.end, text=seg.text.strip())
                all_segments.append(s)
                parts.append(s.text)
                self.segment_ready.emit(s.text)
                if total > 0:
                    self.progress.emit(min(int((seg.end / total) * 100), 100))
            self.progress.emit(100)
            self.finished_ok.emit(TranscriptResult(
                text=" ".join(parts), segments=all_segments,
                language=info.language, duration=total,
            ))
        except Exception as e:  # noqa: BLE001
            logger.error("Erro na transcrição: %s", e)
            self.finished_error.emit(str(e))


class LiveTranscriber(QThread):
    """Transcrição contínua enquanto a gravação acontece (assistente ao vivo).

    A cada janela (~LIVE_WINDOW_SECONDS) pega o áudio novo acumulado na sessão
    e transcreve só esse trecho, emitindo `partial` com o texto do bloco. A
    transcrição definitiva (mais precisa) continua sendo feita ao parar, a
    partir do WAV completo — esta aqui é auxiliar, para a UI e a IA ao vivo.
    """

    partial = Signal(str)   # texto transcrito do bloco novo
    status = Signal(str)

    def __init__(self, session, model_size: str, language: str = "", parent=None):
        super().__init__(parent)
        self.session = session
        self.model_size = model_size
        self.language = language
        self._running = True

    def stop(self) -> None:
        self._running = False

    def _sleep_window(self) -> None:
        # Dorme em passos curtos para reagir rápido ao stop().
        steps = int(LIVE_WINDOW_SECONDS / 0.25)
        for _ in range(steps):
            if not self._running:
                return
            self.msleep(250)

    def run(self) -> None:
        try:
            _force_c_utf8_locale()
            model = get_model(self.model_size)
        except Exception as e:  # noqa: BLE001
            logger.warning("Live: falha ao carregar modelo: %s", e)
            self.status.emit(str(e))
            return
        language = self.language or None
        processed = 0  # nº de amostras já transcritas
        min_new = int(LIVE_MIN_SECONDS * SAMPLE_RATE)
        while self._running:
            self._sleep_window()
            if not self._running:
                break
            try:
                audio = self.session.snapshot_audio()
            except Exception:  # noqa: BLE001
                continue
            if len(audio) - processed < min_new:
                continue
            chunk = audio[processed:]
            processed = len(audio)
            try:
                segments_iter, _info = model.transcribe(
                    chunk, language=language, beam_size=1, vad_filter=True,
                )
                text = " ".join(seg.text.strip() for seg in segments_iter).strip()
            except Exception as e:  # noqa: BLE001
                logger.warning("Live: erro transcrevendo janela: %s", e)
                continue
            if text:
                self.partial.emit(text)
