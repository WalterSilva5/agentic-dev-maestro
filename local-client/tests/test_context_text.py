"""Inserir texto no contexto da reunião — inclusive em tempo real, durante a gravação."""
from PySide6.QtWidgets import QInputDialog


def test_nota_vazia_e_ignorada(meetings_view):
    v = meetings_view
    v._add_live_note("   ")
    v._add_live_note("")
    assert v._context_items == []


def test_nota_vira_item_de_contexto_com_hora(meetings_view):
    v = meetings_view
    v._add_live_note("O prazo mudou para sexta")
    assert len(v._context_items) == 1
    item = v._context_items[0]
    assert item["text"] == "O prazo mudou para sexta"
    assert item["label"].startswith("Nota ")  # rotulado com a hora


def test_nota_entra_no_contexto_enviado_a_ia(meetings_view):
    """É o ponto central: o que foi digitado precisa chegar ao prompt."""
    v = meetings_view
    v._add_live_note("Cliente aprovou o orçamento")
    assert "Cliente aprovou o orçamento" in v._meeting_context()


def test_campo_inline_emite_e_limpa(meetings_view):
    v = meetings_view
    v.live.note_input.setText("Veio pelo campo do painel ao vivo")
    v.live._emit_note()
    assert v.live.note_input.text() == ""
    assert "Veio pelo campo do painel ao vivo" in v._meeting_context()


def test_campo_inline_ignora_texto_vazio(meetings_view):
    v = meetings_view
    v.live.note_input.setText("   ")
    v.live._emit_note()
    assert v._context_items == []


def test_live_context_atualiza_durante_a_gravacao(meetings_view):
    """Durante o ao vivo o contexto precisa refletir a nota na hora."""
    v = meetings_view
    v._live_transcriber = object()   # simula transcrição ao vivo ativa
    try:
        v._add_live_note("Informação de última hora")
        assert "Informação de última hora" in (v._live_context or "")
    finally:
        v._live_transcriber = None


def test_dialogo_de_texto_adiciona(meetings_view, monkeypatch):
    v = meetings_view
    monkeypatch.setattr(QInputDialog, "getMultiLineText",
                        staticmethod(lambda *a, **k: ("Ata da reunião anterior", True)))
    v._add_context_text()
    assert "Ata da reunião anterior" in v._meeting_context()
    assert v._context_items[0]["label"].startswith("Texto")


def test_dialogo_cancelado_nao_adiciona(meetings_view, monkeypatch):
    v = meetings_view
    monkeypatch.setattr(QInputDialog, "getMultiLineText",
                        staticmethod(lambda *a, **k: ("texto qualquer", False)))
    v._add_context_text()
    assert v._context_items == []


def test_remover_nota_tira_do_contexto(meetings_view):
    v = meetings_view
    v._add_live_note("Some daqui")
    v._remove_context_item(0)
    assert v._context_items == []
    assert "Some daqui" not in v._meeting_context()


def test_nova_reuniao_limpa_as_notas(meetings_view):
    v = meetings_view
    v._add_live_note("Nota da reunião antiga")
    v._new_meeting()
    assert v._context_items == []
