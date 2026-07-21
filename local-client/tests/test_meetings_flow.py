"""Regressões do fluxo de Reuniões.

Cada teste aqui corresponde a um bug que já aconteceu de verdade — servem de
rede de segurança para a refatoração dos componentes.
"""
from __future__ import annotations

import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from maestro_local.db.models import Recording, get_session

EMPTY = {"action_items": [], "decisions": [], "questions": [], "plan": [], "tips": []}


def _make_recording(**kw) -> int:
    """Cria uma gravação no banco de teste e devolve o id."""
    s = get_session()
    try:
        rec = Recording(**kw)
        s.add(rec)
        s.commit()
        return rec.id
    finally:
        s.close()


def _item_for(rec_id: int) -> QListWidgetItem:
    item = QListWidgetItem("x")
    item.setData(Qt.UserRole, rec_id)
    return item


def _read(rec_id: int) -> dict:
    s = get_session()
    try:
        r = s.query(Recording).get(rec_id)
        return {"transcript": r.transcript, "live_state_json": r.live_state_json,
                "markdown": r.markdown}
    finally:
        s.close()


# --------------------------------------------------------------------------
# Bug: abrir outra reunião do histórico mantinha as abas da PRIMEIRA analisada
# --------------------------------------------------------------------------
def test_abrir_do_historico_troca_de_reuniao(meetings_view):
    v = meetings_view
    a = _make_recording(kind="meeting", title="A", transcript="transcrição A",
                        live_state_json=json.dumps({**EMPTY, "plan": ["plano de A"]}))
    b = _make_recording(kind="meeting", title="B", transcript="transcrição B",
                        live_state_json=json.dumps({**EMPTY, "plan": ["plano de B"]}))

    v._open_recording(_item_for(a))
    assert v.transcript_edit.toPlainText() == "transcrição A"
    assert v._live_state["plan"] == ["plano de A"]
    assert v._current["rec_id"] == a

    v._open_recording(_item_for(b))
    assert v.transcript_edit.toPlainText() == "transcrição B"
    assert v._live_state["plan"] == ["plano de B"], "abas ficaram presas na 1ª reunião"
    assert v._current["rec_id"] == b, "rec_id não acompanhou — salvaria por cima da outra"


# --------------------------------------------------------------------------
# Bug: reanalisar descartava as respostas digitadas à mão
# --------------------------------------------------------------------------
def test_respostas_manuais_sobrevivem_a_reanalise(meetings_view):
    v = meetings_view
    v._live_state = {**EMPTY, "questions": [
        {"question": "Qual o limite?", "answer": "50 mil", "resolved": True},
    ]}
    # O agente reemite a mesma pergunta SEM a resposta (caso real observado).
    novo = {**EMPTY, "questions": [
        {"question": "Qual o limite?", "answer": "", "resolved": False},
    ]}
    merged = v._preserve_answers(novo)
    assert merged["questions"][0]["answer"] == "50 mil"
    assert merged["questions"][0]["resolved"] is True


def test_revisao_envia_estado_atual_ao_agente(meetings_view, monkeypatch):
    """keep_state=True deve mandar o estado ATUAL (com respostas), não vazio."""
    v = meetings_view
    v._live_state = {**EMPTY, "questions": [
        {"question": "Versionar?", "answer": "Sim, por trimestre", "resolved": True},
    ]}
    capturado = {}

    class FakeWorker:
        def __init__(self, state, new_text, context=""):
            capturado["state"] = state
        def __getattr__(self, _name):
            class _Sig:
                def connect(self, *a, **k): pass
            return _Sig()
        def start(self): pass

    import maestro_local.transcricoes.live_assistant as la
    monkeypatch.setattr(la, "LiveExtractWorker", FakeWorker)
    monkeypatch.setattr(v, "_provider_ready", lambda: True)

    v._start_analyze_extract("transcrição corrigida", keep_state=True)
    enviado = capturado["state"]["questions"][0]["answer"]
    assert enviado == "Sim, por trimestre", "revisão zerou o estado antes de enviar"
    assert v._live_state["questions"][0]["answer"] == "Sim, por trimestre"


# --------------------------------------------------------------------------
# Autosave + restauração dos itens do assistente
# --------------------------------------------------------------------------
def test_autosave_e_restauracao_do_live_state(meetings_view):
    v = meetings_view
    v._set_transcript_text("transcrição da reunião")
    v._live_state = {**EMPTY, "plan": ["p1", "p2"], "decisions": ["d1"],
                     "questions": [{"question": "q", "answer": "r", "resolved": True}]}
    v._autosave_live_state()

    rec_id = v._current.get("rec_id")
    assert rec_id, "autosave não criou a gravação"
    saved = json.loads(_read(rec_id)["live_state_json"])
    assert saved["plan"] == ["p1", "p2"]

    # Sai da reunião e volta: tem que voltar igual
    v._new_meeting()
    assert v._live_state["plan"] == []
    v._open_recording(_item_for(rec_id))
    assert v._live_state["plan"] == ["p1", "p2"]
    assert v._live_state["decisions"] == ["d1"]
    assert v._live_state["questions"][0]["answer"] == "r"
    assert v.transcript_edit.toPlainText() == "transcrição da reunião"


# --------------------------------------------------------------------------
# "Nova reunião" limpa tudo; iniciar gravação preserva a preparação
# --------------------------------------------------------------------------
def test_nova_reuniao_limpa_entradas_e_saidas(meetings_view):
    v = meetings_view
    v.prep_edit.setPlainText("Pauta X")
    v._add_context_item("req.pdf", "conteúdo")
    v._set_transcript_text("transcrição antiga")
    v._set_result_markdown("# resumo antigo")
    v._live_state = {**EMPTY, "plan": ["p"]}
    v._current["rec_id"] = 123

    v._new_meeting()

    assert v.prep_edit.toPlainText() == ""
    assert v._context_items == []
    assert v.transcript_edit.toPlainText() == ""
    assert v._md_source == ""
    assert v._live_state["plan"] == []
    assert v._current["rec_id"] is None


def test_reset_de_saidas_preserva_a_preparacao(meetings_view):
    """Ao iniciar uma gravação, preparação/contexto (entradas) devem ficar."""
    v = meetings_view
    v.prep_edit.setPlainText("Pauta que vale para ESTA reunião")
    v._add_context_item("req.pdf", "conteúdo")
    v._set_transcript_text("transcrição da reunião anterior")
    v._live_state = {**EMPTY, "plan": ["plano antigo"]}

    v._reset_outputs()

    assert v.prep_edit.toPlainText() == "Pauta que vale para ESTA reunião"
    assert len(v._context_items) == 1
    assert v.transcript_edit.toPlainText() == ""
    assert v._live_state["plan"] == []


# --------------------------------------------------------------------------
# Markdown: preview não pode virar a fonte exportada
# --------------------------------------------------------------------------
def test_export_usa_a_fonte_markdown_mesmo_no_preview(meetings_view):
    v = meetings_view
    md = "# Resumo\n\n- item **A**"
    v._set_result_markdown(md)
    assert v._current_result_md() == md

    v._toggle_md_view()  # entra no preview (renderizado, read-only)
    assert v.result_edit.isReadOnly()
    assert v._current_result_md() == md, "exportaria o HTML renderizado"

    v._toggle_md_view()  # volta para o código
    assert not v.result_edit.isReadOnly()
    assert v.result_edit.toPlainText() == md


# --------------------------------------------------------------------------
# Edição da transcrição agenda a revisão; escrita programática não
# --------------------------------------------------------------------------
def test_edicao_do_usuario_agenda_revisao_programatica_nao(meetings_view):
    v = meetings_view
    v._set_transcript_text("texto vindo do Whisper")
    assert not v._transcript_review.isActive(), "escrita programática disparou revisão"

    v.transcript_edit.setPlainText("texto corrigido pelo usuário")
    assert v._transcript_review.isActive(), "edição do usuário não agendou a revisão"


# --------------------------------------------------------------------------
# Combos sensíveis não podem trocar com a roda do mouse
# --------------------------------------------------------------------------
@pytest.mark.parametrize("attr", ["ws_combo", "proj_combo", "kind_combo",
                                  "mic_combo", "monitor_combo", "screen_combo"])
def test_combos_ignoram_a_roda_do_mouse(meetings_view, attr):
    from maestro_local.gui.no_wheel_combo import NoWheelComboBox
    assert isinstance(getattr(meetings_view, attr), NoWheelComboBox)


def test_transcricao_ao_vivo_alimenta_o_campo_unico(meetings_view):
    """Só existe um campo de transcrição: o da etapa 3 recebe o texto ao vivo."""
    v = meetings_view
    assert not hasattr(v, "live_transcript_edit")
    v._on_live_partial("primeira frase.")
    v._on_live_partial("segunda frase.")
    texto = v.transcript_edit.toPlainText()
    assert "primeira frase." in texto and "segunda frase." in texto
    assert v._live_transcript == "primeira frase. segunda frase."


def test_texto_ao_vivo_nao_dispara_revisao(meetings_view):
    """Cada trecho transcrito não pode agendar uma revisão do agente."""
    v = meetings_view
    v._transcript_review.stop()
    v._on_live_partial("trecho novo.")
    assert not v._transcript_review.isActive()


def test_reabrir_gravacao_antiga_deriva_abas_do_resumo(meetings_view):
    """Gravação analisada antes das abas (só summary_json) mostra itens ao reabrir."""
    import json
    from maestro_local.transcricoes import repository
    repository.save(None, {
        "title": "Antiga", "transcript": "t",
        "summary_json": json.dumps({
            "decisions": ["Postgres"],
            "action_items": [{"description": "Migrar", "assignee": "Ana"}],
            "open_questions": ["Prazo?"],
        }),
        "markdown": "# r", "live_state_json": "",
    })
    v = meetings_view
    v._load_history()
    v._open_recording(v.history.item(0))
    assert v.live_actions_list.count() == 1
    assert v.live_decisions_list.count() == 1
    assert v._live_state["questions"][0]["question"] == "Prazo?"
