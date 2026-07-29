"""Liberação do modelo Whisper quando ocioso (economia de RAM)."""
from maestro_local.transcricoes import transcriber as tr
from maestro_local.transcricoes.agent_service import MeetingAgentService


def test_release_model_sem_modelo_e_noop():
    tr._cached_model = None
    tr._cached_size = None
    assert tr.release_model() is False


def test_release_model_libera_e_zera_cache():
    tr._cached_model = object()   # stand-in do WhisperModel
    tr._cached_size = "small"
    assert tr.release_model() is True
    assert tr._cached_model is None
    assert tr._cached_size is None
    # idempotente: segunda chamada não faz nada
    assert tr.release_model() is False


def test_agent_is_busy_reflete_workers(qapp):
    svc = MeetingAgentService()
    assert svc.is_busy() is False
    svc._transcriber = object()          # simula transcrição em curso
    assert svc.is_busy() is True
    svc._transcriber = None
    svc._vision_workers = [object()]     # leitura de imagem em curso
    assert svc.is_busy() is True
