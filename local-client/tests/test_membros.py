"""Lista de responsáveis do projeto: CRUD, atribuição e métricas."""
from maestro_local.db.models import (
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
        assert stats["Walter"]["overdue"] == 1
        assert stats["Outro"]["total"] == 1
        assert stats["Outro"]["done"] == 0
    finally:
        s.close()


def test_filtro_inclui_membros_sem_card(qapp, temp_db):
    from maestro_local.gui.views.board_view import BoardView
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
    from maestro_local.gui.views.board_view import BoardView, MembersDialog
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
