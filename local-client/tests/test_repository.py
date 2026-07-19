"""Repositório de persistência das reuniões."""
import json

from maestro_local.transcricoes import repository


def test_save_cria_e_devolve_id(temp_db):
    rec_id = repository.save(None, {"title": "Daily", "transcript": "oi"})
    assert rec_id
    rec = repository.get(rec_id)
    assert rec["title"] == "Daily"
    assert rec["transcript"] == "oi"


def test_save_parcial_preserva_campos_ausentes(temp_db):
    """Salvar só a transcrição não pode apagar o resumo já gravado."""
    rec_id = repository.save(None, {"markdown": "# resumo", "transcript": "a"})
    repository.save(rec_id, {"transcript": "a b c"})
    rec = repository.get(rec_id)
    assert rec["transcript"] == "a b c"
    assert rec["markdown"] == "# resumo"


def test_tags_serializam_e_desserializam(temp_db):
    rec_id = repository.save(None, {"tags": ["x", "y"]})
    assert repository.get(rec_id)["tags"] == ["x", "y"]


def test_tags_invalidas_viram_lista_vazia(temp_db):
    rec_id = repository.save(None, {})
    from maestro_local.db.models import Recording, get_session
    s = get_session()
    try:
        s.get(Recording, rec_id).tags = "{isso não é json"
        s.commit()
    finally:
        s.close()
    assert repository.get(rec_id)["tags"] == []


def test_get_de_id_inexistente_ou_vazio(temp_db):
    assert repository.get(None) is None
    assert repository.get(999999) is None


def test_arquivar_esconde_do_historico(temp_db):
    rec_id = repository.save(None, {"title": "Antiga"})
    repository.set_archived(rec_id, True)
    assert repository.is_archived(rec_id) is True
    assert all(r["rec_id"] != rec_id for r in repository.list_recent())
    assert any(r["rec_id"] == rec_id
               for r in repository.list_recent(show_archived=True))
    repository.set_archived(rec_id, False)
    assert repository.is_archived(rec_id) is False


def test_delete_remove(temp_db):
    rec_id = repository.save(None, {"title": "Some"})
    repository.delete(rec_id)
    assert repository.get(rec_id) is None


def test_save_order_grava_a_ordem_manual(temp_db):
    a = repository.save(None, {"title": "A"})
    b = repository.save(None, {"title": "B"})
    repository.save_order([b, a])
    assert [r["rec_id"] for r in repository.list_recent()] == [b, a]


def test_live_state_json_ida_e_volta(temp_db):
    state = {"action_items": [{"text": "fazer"}]}
    rec_id = repository.save(None, {"live_state_json": json.dumps(state)})
    assert json.loads(repository.get(rec_id)["live_state_json"]) == state
