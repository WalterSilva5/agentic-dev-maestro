"""Lista de responsáveis do projeto: CRUD, atribuição e métricas."""
from relay.db.models import (
    BoardColumn,
    Member,
    Project,
    Task,
    get_or_create_member,
    get_session,
    member_stats,
    project_members,
)


def _projeto():
    s = get_session()
    p = Project(name="P", key="P")
    s.add(p)
    s.flush()
    pid = p.id
    s.add(BoardColumn(project_id=pid, name="A fazer", order=0))
    done = BoardColumn(project_id=pid, name="Feito", order=1, is_done=True)
    s.add(done)
    s.commit()
    s.close()
    return pid


def test_criar_e_listar_membros(temp_db):
    pid = _projeto()
    s = get_session()
    try:
        get_or_create_member(s, pid, "Walter")
        get_or_create_member(s, pid, "Ana")
        s.commit()
        assert [m.name for m in project_members(s, pid)] == ["Ana", "Walter"]
    finally:
        s.close()


def test_nome_duplicado_nao_duplica(temp_db):
    pid = _projeto()
    s = get_session()
    try:
        a = get_or_create_member(s, pid, "Walter")
        s.commit()
        b = get_or_create_member(s, pid, "  walter  ")
        s.commit()
        assert a.id == b.id
        assert s.query(Member).filter_by(project_id=pid).count() == 1
    finally:
        s.close()


def test_metricas_por_responsavel(temp_db):
    from datetime import datetime, timedelta
    pid = _projeto()
    s = get_session()
    try:
        cols = {c.name: c for c in s.query(BoardColumn).filter_by(project_id=pid)}
        get_or_create_member(s, pid, "Walter")
        get_or_create_member(s, pid, "Outro")
        s.add(Task(project_id=pid, column_id=cols["Feito"].id, number=1,
                   title="A", assignee="Walter"))
        s.add(Task(project_id=pid, column_id=cols["A fazer"].id, number=2,
                   title="B", assignee="Walter",
                   due_date=datetime.now() - timedelta(days=1)))
        s.add(Task(project_id=pid, column_id=cols["A fazer"].id, number=3,
                   title="C", assignee="Outro"))
        s.commit()
        stats = {st["member"].name: st for st in member_stats(s, pid)}
        assert stats["Walter"]["total"] == 2
        assert stats["Walter"]["done"] == 1
        assert stats["Walter"]["pct"] == 50
        # sem Dev Box no fluxo: dev concluído cai na coluna de conclusão
        assert stats["Walter"]["developed"] == 1
        assert stats["Walter"]["developedPct"] == 50
        assert stats["Walter"]["overdue"] == 1
        assert stats["Outro"]["total"] == 1
        assert stats["Outro"]["done"] == 0
        assert stats["Outro"]["developed"] == 0
    finally:
        s.close()


def test_dev_box_conta_como_desenvolvido_por_responsavel(temp_db):
    """Card em Dev Box é dev concluído do responsável, mesmo sem aceite."""
    s = get_session()
    try:
        p = Project(name="Fluxo", key="FLX")
        s.add(p)
        s.flush()
        cols = {}
        for nome, ordem, done in [
            ("To do", 0, False), ("Dev Review", 5, False),
            ("Dev Box", 6, False), ("Done", 8, True),
        ]:
            c = BoardColumn(project_id=p.id, name=nome, order=ordem, is_done=done)
            s.add(c)
            s.flush()
            cols[nome] = c
        get_or_create_member(s, p.id, "Moises")
        s.add(Task(project_id=p.id, column_id=cols["Dev Box"].id, number=1,
                   title="dev pronto", assignee="Moises"))
        s.add(Task(project_id=p.id, column_id=cols["Done"].id, number=2,
                   title="aceito", assignee="Moises"))
        s.add(Task(project_id=p.id, column_id=cols["To do"].id, number=3,
                   title="a fazer", assignee="Moises"))
        s.commit()
        stats = {st["member"].name: st for st in member_stats(s, p.id)}
        assert stats["Moises"]["total"] == 3
        assert stats["Moises"]["done"] == 1
        assert stats["Moises"]["pct"] == 33
        assert stats["Moises"]["developed"] == 2
        assert stats["Moises"]["developedPct"] == 67
    finally:
        s.close()


def test_filtro_inclui_membros_sem_card(qapp, temp_db):
    from relay.gui.views.board_view import BoardView
    pid = _projeto()
    s = get_session()
    try:
        get_or_create_member(s, pid, "Livre")
        s.commit()
    finally:
        s.close()
    v = BoardView()
    v.set_project(pid)
    nomes = [v.filter_bar.assignee_combo.itemText(i)
             for i in range(v.filter_bar.assignee_combo.count())]
    assert "Livre" in nomes


def test_dialogo_responsaveis_abre(qapp, temp_db):
    from relay.gui.views.board_view import BoardView, MembersDialog
    pid = _projeto()
    s = get_session()
    try:
        get_or_create_member(s, pid, "Walter")
        s.commit()
    finally:
        s.close()
    v = BoardView()
    v.set_project(pid)
    dlg = MembersDialog(pid, v)
    assert dlg.windowTitle() == "Responsáveis do projeto"
