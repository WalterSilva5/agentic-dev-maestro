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

    class _LiveFalso:
        """Evita subir o Whisper de verdade — uma QThread real ficaria viva no
        teardown e o Qt aborta ao destruir QThread em execução."""

        def __init__(self, *a, **k):
            self.partial = types.SimpleNamespace(connect=lambda f: None)
            self.status = types.SimpleNamespace(connect=lambda f: None)

        def start(self):
            pass

        def stop(self):
            pass

        def wait(self, msecs=0):
            return True

        def isFinished(self):
            return True

    monkeypatch.setattr(audio_backend, "parec_available", lambda: True)
    monkeypatch.setattr(audio_backend, "list_sources", lambda: [src])
    monkeypatch.setattr(audio_backend, "RecordingSession", _Sessao)
    import maestro_local.transcricoes.transcriber as transcriber
    monkeypatch.setattr(transcriber, "LiveTranscriber", _LiveFalso)
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


def _abrir_por_rec_id(v, rid):
    """Abre pelo rec_id, sem depender da ordem do histórico."""
    from PySide6.QtCore import Qt
    v._load_history()
    item = next(v.history.item(i) for i in range(v.history.count())
                if v.history.item(i).data(Qt.UserRole) == rid)
    v._open_recording(item)


def test_reuniao_com_itens_e_transcricao_vazia_continua(gravavel):
    """O sinal de 'reunião pré-existente' é o rec_id, não o texto.

    Uma reunião reaberta pode ter itens e resumo com a transcrição ainda vazia
    (ex.: a transcrição anterior falhou). Olhando só o texto, clicar em gravar
    apagava o vínculo e todos os itens.
    """
    v = gravavel
    v.live_check.setChecked(True)
    rid = repository.save(None, {
        "title": "Sem transcrição", "transcript": "", "markdown": "# resumo",
        "live_state_json": '{"decisions":["Adotar Postgres"],"action_items":[],'
                           '"questions":[],"plan":["Passo 1"],"tips":[]}'})
    _abrir_por_rec_id(v, rid)
    assert v._live_state["decisions"] == ["Adotar Postgres"]

    v._start_record()
    assert v._current["rec_id"] == rid, "perdeu o vínculo com a reunião salva"
    assert v._live_state["decisions"] == ["Adotar Postgres"], "perdeu as decisões"
    assert v._live_state["plan"] == ["Passo 1"], "perdeu o plano"


def test_ao_vivo_usa_o_mesmo_sinal_de_continuacao(gravavel):
    """_start_live decidia por conta própria olhando o texto — ficava fora de
    sincronia com _start_record quando a transcrição estava vazia."""
    v = gravavel
    v.live_check.setChecked(True)
    rid = repository.save(None, {
        "title": "Sem transcrição", "transcript": "",
        "live_state_json": '{"decisions":["D"],"action_items":[],'
                           '"questions":[],"plan":[],"tips":[]}'})
    _abrir_por_rec_id(v, rid)
    v._start_record()
    assert v._continuing_meeting is True
