"""Backend de áudio para Linux (PulseAudio/PipeWire via parec).

Captura microfone e/ou áudio do sistema (fontes .monitor) com `parec`,
lendo PCM s16le 16kHz mono direto para numpy. Substitui o backend WASAPI
do projeto cronista (que era exclusivo do Windows).
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .constants import CHANNELS, SAMPLE_RATE

logger = logging.getLogger("maestro.transcricoes.audio")


@dataclass
class AudioSource:
    name: str          # nome técnico da fonte PulseAudio
    description: str    # rótulo amigável
    is_monitor: bool    # True = áudio do sistema (loopback)


def parec_available() -> bool:
    return shutil.which("parec") is not None and shutil.which("pactl") is not None


def list_sources() -> list[AudioSource]:
    """Lista fontes de áudio: microfones e monitores (áudio do sistema)."""
    if not parec_available():
        return []
    try:
        short = subprocess.run(
            ["pactl", "list", "short", "sources"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except Exception as e:  # noqa: BLE001
        logger.warning("pactl falhou: %s", e)
        return []

    # Descrições amigáveis
    descriptions: dict[str, str] = {}
    try:
        full = subprocess.run(
            ["pactl", "list", "sources"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        cur = None
        for line in full.splitlines():
            line = line.strip()
            if line.startswith("Name:"):
                cur = line.split("Name:", 1)[1].strip()
            elif line.startswith("Description:") and cur:
                descriptions[cur] = line.split("Description:", 1)[1].strip()
    except Exception:  # noqa: BLE001
        pass

    sources = []
    for line in short.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[1]
        is_monitor = name.endswith(".monitor")
        desc = descriptions.get(name, name)
        sources.append(AudioSource(name=name, description=desc, is_monitor=is_monitor))
    return sources


def default_mic() -> AudioSource | None:
    for s in list_sources():
        if not s.is_monitor:
            return s
    return None


def default_monitor() -> AudioSource | None:
    for s in list_sources():
        if s.is_monitor:
            return s
    return None


def _mix(mic_audio: np.ndarray, mon_audio: np.ndarray) -> np.ndarray:
    """Mixa (soma) mic + monitor alinhando o tamanho por padding."""
    if len(mic_audio) and len(mon_audio):
        n = max(len(mic_audio), len(mon_audio))
        mic_audio = np.pad(mic_audio, (0, n - len(mic_audio)))
        mon_audio = np.pad(mon_audio, (0, n - len(mon_audio)))
        return mic_audio + mon_audio
    if len(mic_audio):
        return mic_audio
    if len(mon_audio):
        return mon_audio
    return np.zeros(0, dtype=np.float32)


class ParecRecorder:
    """Grava de uma fonte PulseAudio via parec em thread separada."""

    def __init__(self, source: AudioSource) -> None:
        self.source = source
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._running = False
        self._peak = 0.0

    def start(self) -> None:
        if self._running:
            return
        self._chunks.clear()
        self._peak = 0.0
        self._proc = subprocess.Popen(
            [
                "parec", "--device", self.source.name,
                "--format=s16le", f"--rate={SAMPLE_RATE}", f"--channels={CHANNELS}",
                "--raw",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        logger.info("Gravação iniciada: %s", self.source.name)

    def _read_loop(self) -> None:
        block = 4096
        while self._running and self._proc and self._proc.stdout:
            data = self._proc.stdout.read(block)
            if not data:
                break
            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            with self._lock:
                self._chunks.append(audio)
                if len(audio):
                    self._peak = float(np.max(np.abs(audio)))

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except Exception:  # noqa: BLE001
                self._proc.kill()
            self._proc = None
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Gravação parada: %s", self.source.name)

    @property
    def peak_level(self) -> float:
        with self._lock:
            return self._peak

    def get_audio(self) -> np.ndarray:
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            return np.concatenate(self._chunks)

    def get_audio_since(self, offset: int) -> np.ndarray:
        """Só as amostras a partir de `offset`.

        Evita concatenar/copiar a gravação inteira a cada janela do assistente
        ao vivo (que ficava mais caro conforme a reunião crescia).
        """
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            out = []
            pos = 0
            for ch in self._chunks:
                n = len(ch)
                end = pos + n
                if end > offset:
                    out.append(ch[max(0, offset - pos):])
                pos = end
            return np.concatenate(out) if out else np.zeros(0, dtype=np.float32)


class RecordingSession:
    """Sessão completa: mic e/ou monitor, mixa e salva WAV 16kHz mono."""

    def __init__(self, mic: AudioSource | None, monitor: AudioSource | None) -> None:
        if mic is None and monitor is None:
            raise ValueError("Selecione ao menos uma fonte de áudio")
        self.mic_rec = ParecRecorder(mic) if mic else None
        self.mon_rec = ParecRecorder(monitor) if monitor else None
        self._frames = 0

    def start(self) -> None:
        if self.mic_rec:
            try:
                self.mic_rec.start()
            except Exception as e:  # noqa: BLE001
                logger.warning("Mic indisponível: %s", e)
                self.mic_rec = None
        if self.mon_rec:
            try:
                self.mon_rec.start()
            except Exception as e:  # noqa: BLE001
                logger.warning("Monitor indisponível: %s", e)
                self.mon_rec = None
        if not self.mic_rec and not self.mon_rec:
            raise RuntimeError("Nenhuma fonte de áudio disponível")

    def stop_and_save(self, out_path: Path) -> tuple[Path, float]:
        if self.mic_rec:
            self.mic_rec.stop()
        if self.mon_rec:
            self.mon_rec.stop()

        mic_audio = self.mic_rec.get_audio() if self.mic_rec else np.zeros(0, dtype=np.float32)
        mon_audio = self.mon_rec.get_audio() if self.mon_rec else np.zeros(0, dtype=np.float32)

        mixed = _mix(mic_audio, mon_audio)
        if not len(mixed):
            mixed = np.zeros(SAMPLE_RATE, dtype=np.float32)

        # Normaliza para evitar clipping
        peak = float(np.max(np.abs(mixed))) if len(mixed) else 0.0
        if peak > 1.0:
            mixed = mixed / peak

        out_path.parent.mkdir(parents=True, exist_ok=True)
        import soundfile as sf
        sf.write(str(out_path), mixed, SAMPLE_RATE)
        duration = len(mixed) / SAMPLE_RATE
        return out_path, duration

    def snapshot_audio(self) -> np.ndarray:
        """Retorna o áudio mixado acumulado até agora, SEM parar a gravação."""
        return self.snapshot_since(0)

    def snapshot_since(self, offset: int) -> np.ndarray:
        """Áudio mixado a partir de `offset` amostras, SEM parar a gravação.

        A transcrição ao vivo consome janelas sequencialmente, então copiar só o
        trecho novo mantém o custo constante (antes crescia com a reunião).
        """
        empty = np.zeros(0, dtype=np.float32)
        mic_audio = self.mic_rec.get_audio_since(offset) if self.mic_rec else empty
        mon_audio = self.mon_rec.get_audio_since(offset) if self.mon_rec else empty
        return _mix(mic_audio, mon_audio)

    @property
    def is_recording(self) -> bool:
        return bool((self.mic_rec and self.mic_rec._running) or (self.mon_rec and self.mon_rec._running))

    @property
    def mic_level(self) -> float:
        return self.mic_rec.peak_level if self.mic_rec else 0.0

    @property
    def monitor_level(self) -> float:
        return self.mon_rec.peak_level if self.mon_rec else 0.0
