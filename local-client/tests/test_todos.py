"""Consulta de TODOs em aberto usada pela tela da pausa para os olhos."""
from datetime import datetime, timedelta

from maestro_local.db.models import Todo, get_session
from maestro_local.todos import todos_abertos


def _todo(texto, prioridade="MEDIUM", due=None, done=False):
    s = get_session()
    try:
        td = Todo(text=texto, priority=prioridade, due_at=due, done=done)
        s.add(td)
        s.commit()
        return td.id
    finally:
        s.close()


def test_lista_so_pendencias_em_aberto(temp_db):
    _todo("pendente")
    _todo("ja feito", done=True)
    textos = [td["text"] for td in todos_abertos()]
    assert textos == ["pendente"]


def test_ordena_por_prioridade_e_vencimento(temp_db):
    _todo("baixa", "LOW")
    _todo("urgente", "URGENT")
    _todo("media", "MEDIUM")
    _todo("alta", "HIGH")
    assert [td["text"] for td in todos_abertos()] == \
        ["urgente", "alta", "media", "baixa"]


def test_vencimento_desempata_dentro_da_prioridade(temp_db):
    _todo("depois", "HIGH", due=datetime.now() + timedelta(days=5))
    _todo("antes", "HIGH", due=datetime.now() + timedelta(days=1))
    assert [td["text"] for td in todos_abertos()][:2] == ["antes", "depois"]


def test_limite_corta_a_lista(temp_db):
    for i in range(5):
        _todo(f"todo {i}")
    assert len(todos_abertos(limite=3)) == 3
