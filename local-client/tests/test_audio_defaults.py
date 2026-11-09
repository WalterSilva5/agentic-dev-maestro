"""Seleção do dispositivo de áudio padrão (PulseAudio/PipeWire)."""
from relay.transcricoes import audio


def _fonte(nome, monitor=False):
    return audio.AudioSource(name=nome, description=nome, is_monitor=monitor)


def test_default_mic_usa_o_padrao(monkeypatch):
    fontes = [_fonte("mic-a"), _fonte("mic-b"), _fonte("mon.monitor", True)]
    monkeypatch.setattr(audio, "list_sources", lambda: fontes)
    monkeypatch.setattr(audio, "_pactl_get_default", lambda arg: "mic-b")
    assert audio.default_mic().name == "mic-b"


def test_default_mic_fallback_quando_sem_padrao(monkeypatch):
    fontes = [_fonte("mon.monitor", True), _fonte("mic-a")]
    monkeypatch.setattr(audio, "list_sources", lambda: fontes)
    monkeypatch.setattr(audio, "_pactl_get_default", lambda arg: None)
    assert audio.default_mic().name == "mic-a"


def test_default_monitor_usa_a_saida_padrao(monkeypatch):
    fontes = [_fonte("saida.monitor", True), _fonte("outra.monitor", True),
              _fonte("mic-a")]
    monkeypatch.setattr(audio, "list_sources", lambda: fontes)
    monkeypatch.setattr(audio, "_pactl_get_default", lambda arg: "saida")
    assert audio.default_monitor().name == "saida.monitor"


def test_default_monitor_fallback_quando_sem_padrao(monkeypatch):
    fontes = [_fonte("mic-a"), _fonte("outra.monitor", True)]
    monkeypatch.setattr(audio, "list_sources", lambda: fontes)
    monkeypatch.setattr(audio, "_pactl_get_default", lambda arg: None)
    assert audio.default_monitor().name == "outra.monitor"
