"""Goals: vínculo de épicos e progresso por filtro (tag/épico/sprint)."""
from maestro_local.db.models import (
    BoardColumn,
    Epic,
    Goal,
    Label,
    Project,
    Sprint,
    Task,
    get_session,
)
from maestro_local.gui.views.goals_view import _progresso


def _setup():
    s = get_session()
    p = Project(name="P", key="P")
    s.add(p)
    s.flush()
    todo = BoardColumn(project_id=p.id, name="A fazer", order=0)
    done = BoardColumn(project_id=p.id, name="Feito", order=1, is_done=True)
    s.add(todo)
    s.add(done)
    s.flush()
    ep = Epic(project_id=p.id, name="Cashier")
    s.add(ep)
    s.flush()
    lbl = Label(name="onda-1")
    s.add(lbl)
    s.flush()
    sp = Sprint(project_id=p.id, name="S1")
    s.add(sp)
    s.flush()
    t1 = Task(project_id=p.id, column_id=todo.id, number=1, title="A", sprint_id=sp.id)
    t1.labels.append(lbl)
    t1.epics.append(ep)
    s.add(t1)
    t2 = Task(project_id=p.id, column_id=done.id, number=2, title="B", sprint_id=sp.id)
    t2.labels.append(lbl)
    t2.epics.append(ep)
    s.add(t2)
    s.commit()
    return p.id, ep.id, sp.id


def test_epico_vincula_varios_cards(temp_db):
    _pid, eid, _sid = _setup()
    s = get_session()
    try:
        ep = s.get(Epic, eid)
        assert len(ep.tasks) == 2
    finally:
        s.close()


def test_progresso_por_tag(temp_db):
    pid, _eid, _sid = _setup()
    s = get_session()
    try:
        g = Goal(project_id=pid, name="g", tag="onda-1")
        s.add(g)
        s.commit()
        assert _progresso(g, s) == (1, 2)
    finally:
        s.close()


def test_progresso_por_epico_e_sprint(temp_db):
    pid, eid, sid = _setup()
    s = get_session()
    try:
        g = Goal(project_id=pid, name="g", epic_id=eid, sprint_id=sid)
        s.add(g)
        s.commit()
        assert _progresso(g, s) == (1, 2)
    finally:
        s.close()


def test_progresso_sem_filtro_conta_tudo(temp_db):
    pid, _eid, _sid = _setup()
    s = get_session()
    try:
        g = Goal(project_id=pid, name="g")
        s.add(g)
        s.commit()
        assert _progresso(g, s) == (1, 2)
    finally:
        s.close()
