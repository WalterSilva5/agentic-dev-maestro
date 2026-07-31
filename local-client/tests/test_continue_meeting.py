"""Continuar uma reunião existente ao gravar de novo.

Bug corrigido: abrir uma reunião do histórico e clicar em gravar descartava a
transcrição, os itens do assistente e o vínculo com a gravação salva — criava
uma reunião nova e perdia o trabalho anterior.
"""
import types

import pytest

from maestro_local.transcricoes import audio as audio_backend
from maestro_local.transcricoes import repository


@pytest.fixture
def gravavel(meetings_view, monkeypatch):
    """View com o backend de áudio simulado, para `_start_record` rodar de verdade."""
    src = audio_backend.AudioSource(name="fonte-teste", description="Fonte de teste",
                                    is_monitor=False)

    class _Sessao:
        def __init__(self, *a, **k):
            self.is_recording = True
            self.mic_rec = None
            self.mon_rec = None

        def start(self):
            pass

    monkeypatch.setattr(audio_backend, "parec_available", lambda: True)
    monkeypatch.setattr(audio_backend, "list_sources", lambda: [src])
    monkeypatch.setattr(audio_backend, "RecordingSession", _Sessao)
    v = meetings_view
    v.mic_combo.clear()
    v.mic_combo.addItem("Fonte de teste", "fonte-teste")
    return v


def _transcrito(texto, duracao=45.0):
    return types.SimpleNamespace(text=texto, language="pt", duration=duracao,
                                 segments=[1, 2])


def test_gravar_em_reuniao_aberta_preserva_o_vinculo(gravavel):
    v = gravavel
    rid = repository.save(None, {"title": "Daily", "transcript": "Primeira parte.",
                                 "duration": 60.0})
    v._load_history()
    v._open_recording(v.history.item(0))
    assert v._current["rec_id"] == rid

    v._start_record()
    assert v._current["rec_id"] == rid, "perdeu o vínculo — criaria uma reunião nova"
    assert v._transcript_base == "Primeira parte."


def test_gravar_em_reuniao_aberta_nao_apaga_a_transcricao(gravavel):
    v = gravavel
    repository.save(None, {"title": "Daily", "transcript": "Primeira parte."})
    v._load_history()
    v._open_recording(v.history.item(0))

    v._start_record()
    assert v.transcript_edit.toPlainText().strip() == "Primeira parte."


def test_trecho_novo_e_somado_ao_anterior(gravavel):
    v = gravavel
    repository.save(None, {"title": "Daily", "transcript": "Primeira parte.",
                           "duration": 60.0})
    v._load_history()
    v._open_recording(v.history.item(0))
    v._start_record()

    v._on_transcribed(_transcrito("Segunda parte."))
    assert v._current["transcript"] == "Primeira parte.\n\nSegunda parte."
    assert v._current["duration"] == pytest.approx(105.0)   # 60 + 45


def test_continuar_nao_cria_gravacao_duplicada(gravavel):
    v = gravavel
    repository.save(None, {"title": "Daily", "transcript": "Primeira parte."})
    v._load_history()
    v._open_recording(v.history.item(0))
    v._start_record()
    v._on_transcribed(_transcrito("Segunda parte."))

    recs = repository.list_recent()
    assert len(recs) == 1, "deveria continuar a mesma reunião, não criar outra"
    assert recs[0]["transcript"] == "Primeira parte.\n\nSegunda parte."


def test_itens_do_assistente_sao_preservados(gravavel):
    """Plano/ações/decisões acumulam ao longo da reunião, não recomeçam."""
    v = gravavel
    repository.save(None, {
        "title": "Daily", "transcript": "Primeira parte.",
        "live_state_json": '{"decisions":["Adotar Postgres"],"action_items":[],'
                           '"questions":[],"plan":[],"tips":[]}'})
    v._load_history()
    v._open_recording(v.history.item(0))
    assert v._live_state["decisions"] == ["Adotar Postgres"]

    v._start_record()
    assert v._live_state["decisions"] == ["Adotar Postgres"]


def test_reuniao_nova_continua_zerando(gravavel):
    """Sem transcrição prévia o comportamento antigo vale: começa do zero."""
    v = gravavel
    v._new_meeting()
    v._start_record()
    assert v._transcript_base == ""
    assert v._current["rec_id"] is None
    assert v.transcript_edit.toPlainText().strip() == ""


def test_abrir_outra_reuniao_limpa_o_trecho_pendente(gravavel):
    v = gravavel
    repository.save(None, {"title": "A", "transcript": "Reunião A."})
    repository.save(None, {"title": "B", "transcript": "Reunião B."})
    v._load_history()
    v._open_recording(v.history.item(0))
    v._start_record()
    assert v._transcript_base != ""

    v._open_recording(v.history.item(1))   # troca de reunião no meio
    assert v._transcript_base == ""
    assert v._base_duration == 0.0
