"""Modelo de estado da reunião (MeetingSession) — regras de entrada/saída,
respostas e merge do estado vindo do agente."""
from __future__ import annotations

from maestro_local.transcricoes.session import MeetingSession, empty_live_state


def _sessao_preenchida() -> MeetingSession:
    s = MeetingSession()
    s.prep = "Pauta X"
    s.topic = "Tópico"
    s.add_context("req.pdf", "conteúdo")
    s.transcript = "transcrição antiga"
    s.markdown = "# resumo antigo"
    s.live_state = {**empty_live_state(), "plan": ["p"]}
    s.rec_id = 42
    return s


def test_reset_outputs_preserva_entradas():
    s = _sessao_preenchida()
    s.reset_outputs()
    # entradas ficam
    assert s.prep == "Pauta X"
    assert s.topic == "Tópico"
    assert len(s.context_items) == 1
    # saídas zeram
    assert s.transcript == ""
    assert s.markdown == ""
    assert s.live_state["plan"] == []
    assert s.rec_id is None


def test_reset_all_limpa_tudo():
    s = _sessao_preenchida()
    s.reset_all()
    assert s.prep == "" and s.topic == "" and s.context_items == []
    assert s.transcript == "" and s.live_state["plan"] == [] and s.rec_id is None


def test_estado_vazio_nao_e_compartilhado():
    a, b = MeetingSession(), MeetingSession()
    a.live_state["plan"].append("x")
    assert b.live_state["plan"] == [], "listas do estado vazio estão compartilhadas"


def test_set_answer_marca_resolvida():
    s = MeetingSession()
    s.live_state["questions"] = [{"question": "Limite?", "answer": "", "resolved": False}]
    assert s.set_answer(0, "50 mil")
    assert s.questions[0]["answer"] == "50 mil"
    assert s.questions[0]["resolved"] is True
    assert not s.set_answer(5, "fora do range")


def test_merge_preserva_resposta_manual():
    s = MeetingSession()
    s.live_state["questions"] = [{"question": "Limite?", "answer": "50 mil", "resolved": True}]
    # agente reemite a pergunta SEM a resposta
    novo = {**empty_live_state(), "questions": [
        {"question": "Limite?", "answer": "", "resolved": False}]}
    merged = s.merge_live_state(novo)
    assert merged["questions"][0]["answer"] == "50 mil"
    assert merged["questions"][0]["resolved"] is True


def test_merge_aceita_resposta_nova_do_agente():
    s = MeetingSession()
    s.live_state["questions"] = [{"question": "Versionar?", "answer": "", "resolved": False}]
    novo = {**empty_live_state(), "questions": [
        {"question": "Versionar?", "answer": "Sim, por trimestre", "resolved": True}]}
    merged = s.merge_live_state(novo)
    assert merged["questions"][0]["answer"] == "Sim, por trimestre"


def test_serializacao_do_live_state():
    s = MeetingSession()
    s.live_state = {**empty_live_state(), "plan": ["p1"], "decisions": ["d1"]}
    raw = s.live_state_json()

    outra = MeetingSession()
    outra.load_live_state_json(raw)
    assert outra.live_state["plan"] == ["p1"]
    assert outra.live_state["decisions"] == ["d1"]


def test_load_live_state_json_tolera_lixo():
    s = MeetingSession()
    for raw in (None, "", "{nao é json}", "[1,2,3]"):
        s.load_live_state_json(raw)
        assert s.live_state == empty_live_state()


def test_has_content_e_has_live_items():
    s = MeetingSession()
    assert not s.has_content()
    s.live_state["plan"] = ["p"]
    assert s.has_live_items() and s.has_content()
    s.reset_outputs()
    s.transcript = "algo"
    assert s.has_content() and not s.has_live_items()


def test_remove_context():
    s = MeetingSession()
    s.add_context("a.pdf", "x")
    s.add_context("b.pdf", "y")
    assert s.remove_context(0)
    assert [c.label for c in s.context_items] == ["b.pdf"]
    assert not s.remove_context(9)


def test_live_state_from_summary_mapeia_itens():
    from maestro_local.transcricoes.session import live_state_from_summary
    st = live_state_from_summary({
        "decisions": ["Adotar Postgres", "  ", "Deploy sexta"],
        "action_items": [{"description": "Migrar", "assignee": "Ana"}, "Revisar", {"description": ""}],
        "open_questions": ["Qual budget?", ""],
    })
    assert st["decisions"] == ["Adotar Postgres", "Deploy sexta"]
    assert st["action_items"] == [
        {"description": "Migrar", "assignee": "Ana"},
        {"description": "Revisar", "assignee": ""},
    ]
    assert st["questions"] == [{"question": "Qual budget?", "answer": "", "resolved": False}]


def test_live_state_from_summary_tolera_lixo():
    from maestro_local.transcricoes.session import live_state_from_summary
    assert live_state_from_summary(None)["decisions"] == []
    assert live_state_from_summary({})["action_items"] == []
    assert live_state_from_summary({"decisions": None})["decisions"] == []
