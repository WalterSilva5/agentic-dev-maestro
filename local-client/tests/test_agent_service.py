"""MeetingAgentService — orquestração dos trabalhos de IA.

A camada LLM é falsificada: o que se verifica aqui é o serviço iniciar o
worker certo, reemitir o resultado e soltar a referência ao terminar.
"""
from PySide6.QtCore import QEventLoop, QTimer

from maestro_local.transcricoes.agent_service import MeetingAgentService


def _wait(signal, timeout_ms=5000):
    """Espera um sinal e devolve os argumentos (ou None se estourar o tempo)."""
    loop = QEventLoop()
    got = []
    signal.connect(lambda *a: (got.append(a), loop.quit()))
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    return got[0] if got else None


def test_extract_reemite_o_estado_do_agente(qapp, monkeypatch):
    import maestro_local.ai.llm as llm
    monkeypatch.setattr(llm, "invoke_json", lambda *a, **k: {
        "action_items": [{"text": "fazer x"}], "decisions": [],
        "questions": [], "plan": [], "tips": [],
    })
    svc = MeetingAgentService()
    svc.extract({}, "texto da reuniao")
    result = _wait(svc.extracted)
    assert result is not None
    assert result[0]["action_items"] == [{"text": "fazer x"}]


def test_extract_live_ignora_chamada_concorrente(qapp, monkeypatch):
    """Duas extrações ao vivo em paralelo sobrescreveriam o estado uma da outra."""
    import maestro_local.ai.llm as llm
    monkeypatch.setattr(llm, "invoke_json", lambda *a, **k: {})
    svc = MeetingAgentService()
    svc.extract_live({}, "a")
    primeiro = svc._live_extractor
    svc.extract_live({}, "b")
    assert svc._live_extractor is primeiro
    _wait(svc.live_extracted)


def test_worker_e_liberado_ao_terminar(qapp, monkeypatch):
    import maestro_local.ai.llm as llm
    monkeypatch.setattr(llm, "invoke_json", lambda *a, **k: {})
    svc = MeetingAgentService()
    svc.extract_live({}, "a")
    assert svc.is_extracting_live() is True
    _wait(svc.live_extracted)
    qapp.processEvents()
    assert svc.is_extracting_live() is False


def test_ask_reemite_a_resposta(qapp, monkeypatch):
    import maestro_local.ai.llm as llm
    monkeypatch.setattr(llm, "invoke_text", lambda *a, **k: "  a resposta  ")
    svc = MeetingAgentService()
    svc.ask("transcricao", "o que ficou decidido?")
    result = _wait(svc.answered)
    assert result == ("a resposta",)


def test_ask_falha_vira_sinal_de_erro(qapp, monkeypatch):
    import maestro_local.ai.llm as llm

    def boom(*a, **k):
        raise RuntimeError("sem provedor")

    monkeypatch.setattr(llm, "invoke_text", boom)
    svc = MeetingAgentService()
    svc.ask("transcricao", "pergunta")
    result = _wait(svc.ask_failed)
    assert result and "sem provedor" in result[0]


def test_read_screen_nao_empilha_capturas(qapp, monkeypatch):
    """Visão é cara: só uma leitura de tela por vez."""
    import maestro_local.ai.llm as llm
    monkeypatch.setattr(llm, "invoke_vision", lambda *a, **k: "tela")
    svc = MeetingAgentService()
    svc.read_screen("Tela", b"fake")
    primeiro = svc._screen_reader
    svc.read_screen("Tela", b"fake")
    assert svc._screen_reader is primeiro
    _wait(svc.screen_read)


def test_read_image_permite_anexos_em_paralelo(qapp, monkeypatch):
    import maestro_local.ai.llm as llm
    monkeypatch.setattr(llm, "invoke_vision", lambda *a, **k: "conteudo")
    svc = MeetingAgentService()
    svc.read_image("A", b"1")
    svc.read_image("B", b"2")
    assert len(svc._vision_workers) == 2
    _wait(svc.vision_done)
