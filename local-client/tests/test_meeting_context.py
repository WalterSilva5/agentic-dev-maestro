"""Contexto de reunião: board, métricas e dailies recentes entram no copiloto."""
from datetime import date, datetime, timedelta

import pytest


@pytest.fixture
def projeto_com_dados(temp_db):
    """Projeto com board movimentado, atraso, módulo e dailies."""
    from maestro_local.db.models import (
        BoardColumn, Label, Project, ProjectDailyEntry, Task, get_session,
    )

    s = get_session()
    p = Project(name="Migração", key="MIG")
    s.add(p)
    s.flush()
    cols = {}
    for i, (nome, done) in enumerate([
        ("To do", False), ("Ready for Dev", False), ("Doing", False),
        ("Dev Review", False), ("Dev Box", False), ("In Test", False), ("Done", True),
    ]):
        c = BoardColumn(project_id=p.id, name=nome, order=i, is_done=done)
        s.add(c)
        cols[nome] = c
    s.flush()

    mod = Label(name="config")
    s.add(mod)
    s.flush()

    parado = Task(project_id=p.id, column_id=cols["Dev Box"].id, number=1,
                  title="bug GX #4: teste de erro", assignee="Walter",
                  updated_at=datetime.now() - timedelta(days=5))
    atrasado = Task(project_id=p.id, column_id=cols["Doing"].id, number=2,
                    title="ajustar consulta", assignee="Jeferson",
                    due_date=datetime.now() - timedelta(days=2))
    feito = Task(project_id=p.id, column_id=cols["Done"].id, number=3,
                 title="login v2", assignee="Moisés",
                 done_at=datetime.now() - timedelta(days=1))
    local = Task(project_id=p.id, column_id=cols["To do"].id, number=4,
                 title="lembrete pessoal", is_local=True)
    parado.labels.append(mod)
    s.add_all([parado, atrasado, feito, local])
    s.flush()

    s.add_all([
        ProjectDailyEntry(project_id=p.id, date=(date.today()).isoformat(), kind="WORK",
                          title="cashier", body="Fechamos a onda 1 do cashier; falta validar o E2."),
        ProjectDailyEntry(project_id=p.id, date=(date.today() - timedelta(days=1)).isoformat(),
                          kind="BLOCKER", body="PR sem revisor travou a entrega do cliente."),
    ])
    s.commit()
    pid = p.id
    s.close()
    return pid


def test_contexto_traz_board_atrasos_modulos_e_dailies(projeto_com_dados):
    from maestro_local.db.models import get_session
    from maestro_local.meeting_context import project_context

    s = get_session()
    texto = project_context(s, projeto_com_dados)
    s.close()

    assert texto.startswith("## Projeto — MIG · Migração")
    # board
    assert "Board: 3 cards" in texto          # a tarefa local não entra
    assert "1 concluídos (33%)" in texto
    assert "2 em aberto" in texto
    # em andamento com sinal de tempo parado
    assert "MIG-1" in texto and "parado há 5d" in texto
    # atraso
    assert "### Atrasados" in texto and "venceu" in texto
    # módulo
    assert "### Progresso por módulo" in texto and "config 0/1" in texto
    # entregas recentes
    assert "### Concluídos nos últimos 7 dias" in texto and "MIG-3" in texto
    # dailies
    assert "### Registros recentes (daily do projeto)" in texto
    assert "Fechamos a onda 1 do cashier" in texto
    assert "PR sem revisor" in texto


def test_contexto_ignora_tarefa_local(projeto_com_dados):
    from maestro_local.db.models import get_session
    from maestro_local.meeting_context import project_context

    s = get_session()
    texto = project_context(s, projeto_com_dados)
    s.close()
    assert "lembrete pessoal" not in texto
    assert "MIG-4" not in texto


def test_contexto_de_projeto_inexistente_e_vazio(temp_db):
    from maestro_local.db.models import get_session
    from maestro_local.meeting_context import project_context

    s = get_session()
    assert project_context(s, 9999) == ""
    s.close()


# --------------------------------------------------------------------------
# integração com a view de reuniões
# --------------------------------------------------------------------------

class _Combo:
    def __init__(self, valor):
        self._v = valor

    def currentData(self):
        return self._v


def test_meeting_context_inclui_bloco_do_projeto(meetings_view, projeto_com_dados):
    view = meetings_view
    view.proj_combo = _Combo(projeto_com_dados)

    texto = view._meeting_context()

    assert "## Projeto — MIG · Migração" in texto
    assert "bug GX #4" in texto


def test_meeting_context_sem_projeto_nao_quebra(meetings_view):
    view = meetings_view
    view.proj_combo = _Combo(None)
    view.prep_edit.setPlainText("pauta da reunião")
    texto = view._meeting_context()
    assert "pauta da reunião" in texto
    assert "## Projeto" not in texto


def test_contexto_do_projeto_usa_cache(meetings_view, projeto_com_dados, monkeypatch):
    view = meetings_view
    chamadas = []
    original = view._project_context_cached.__func__ if hasattr(view._project_context_cached, "__func__") else None

    # conta idas ao banco por dentro do builder
    import maestro_local.meeting_context as mc
    contador = {"n": 0}
    real = mc.project_context

    def contando(session, pid):
        contador["n"] += 1
        return real(session, pid)

    monkeypatch.setattr(mc, "project_context", contando)
    view._proj_ctx_cache = None

    primeiro = view._project_context_cached(projeto_com_dados)
    segundo = view._project_context_cached(projeto_com_dados)

    assert primeiro == segundo
    assert contador["n"] == 1        # segunda chamada veio do cache
    assert original is not None
