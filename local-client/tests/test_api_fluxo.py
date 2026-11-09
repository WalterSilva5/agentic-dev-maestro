"""Endpoints de API para Goals, Epics e Members (apoio de fluxo)."""
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.db.models import (
    BoardColumn,
    Project,
    Sprint,
    Task,
    get_session,
)


def _client():
    return TestClient(app)


def _projeto(pid_holder=None):
    s = get_session()
    try:
        p = Project(name="P", key="P")
        s.add(p)
        s.flush()
        cols = [
            BoardColumn(project_id=p.id, name="A fazer", order=0),
            BoardColumn(project_id=p.id, name="Feito", order=1, is_done=True),
        ]
        for c in cols:
            s.add(c)
        s.flush()
        sp = Sprint(project_id=p.id, name="S1", status="ATIVA", sort_order=0)
        s.add(sp)
        s.commit()
        return p.id, sp.id, cols[0].id, cols[1].id
    finally:
        s.close()


def test_epics_crud_e_vinculo(temp_db):
    c = _client()
    pid, _, _, _ = _projeto()

    r = c.post(f"/api/projects/{pid}/epics", json={"name": "Cashier", "color": "#123456"})
    assert r.status_code == 200, r.text
    eid = r.json()["id"]
    assert r.json()["name"] == "Cashier"

    r = c.get(f"/api/projects/{pid}/epics")
    assert r.status_code == 200 and len(r.json()) == 1

    s = get_session()
    try:
        s.add(Task(project_id=pid, column_id=s.query(BoardColumn).filter_by(
            project_id=pid).first().id, number=1, title="T"))
        s.commit()
        tid = s.query(Task).filter_by(project_id=pid).first().id
    finally:
        s.close()

    r = c.post(f"/api/epics/{eid}/tasks/{tid}")
    assert r.status_code == 200, r.text
    r = c.get("/api/tasks")
    assert any(e["name"] == "Cashier" for t in r.json() for e in t.get("epics", []))

    r = c.delete(f"/api/epics/{eid}/tasks/{tid}")
    assert r.status_code == 200
    r = c.delete(f"/api/epics/{eid}")
    assert r.status_code == 200, r.text


def test_epic_projeto_inexistente(temp_db):
    c = _client()
    assert c.post("/api/projects/9999/epics", json={"name": "X"}).status_code == 404
    assert c.post("/api/epics/9999/tasks/1").status_code in (404,)


def test_projeto_target_date_roundtrip(temp_db):
    """Previsão de entrega do projeto: PATCH grava, board devolve, null limpa."""
    from datetime import date, timedelta
    c = _client()
    pid, _, _, _ = _projeto()

    alvo = (date.today() + timedelta(days=30)).isoformat()
    r = c.patch(f"/api/projects/{pid}", json={"targetDate": alvo})
    assert r.status_code == 200, r.text
    assert r.json()["targetDate"].startswith(alvo)

    r = c.get(f"/api/projects/{pid}/board")
    assert r.status_code == 200, r.text
    assert r.json()["targetDate"].startswith(alvo)

    r = c.patch(f"/api/projects/{pid}", json={"targetDate": None})
    assert r.status_code == 200, r.text
    assert r.json()["targetDate"] is None


def test_projeto_target_date_invalida(temp_db):
    c = _client()
    pid, _, _, _ = _projeto()
    r = c.patch(f"/api/projects/{pid}", json={"targetDate": "31/12/2026"})
    assert r.status_code == 400


def test_sprint_end_date_editavel(temp_db):
    """Data de finalização da sprint: cria com endDate e edita via PATCH."""
    c = _client()
    pid, spid, _, _ = _projeto()

    r = c.patch(f"/api/sprints/{spid}", json={"endDate": "2026-11-20"})
    assert r.status_code == 200, r.text
    assert r.json()["endDate"].startswith("2026-11-20")

    r = c.post(f"/api/projects/{pid}/sprints",
               json={"name": "S2", "startDate": "2026-11-21", "endDate": "2026-11-27"})
    assert r.status_code == 200, r.text
    assert r.json()["endDate"].startswith("2026-11-27")

    r = c.get(f"/api/projects/{pid}/sprints")
    assert r.status_code == 200
    nomes = {sp["name"]: sp for sp in r.json()}
    assert nomes["S2"]["endDate"].startswith("2026-11-27")


def test_collect_metrics_regressivas(temp_db):
    """collect_metrics traz as contagens regressivas (sprint + projeto)."""
    from datetime import date, timedelta
    from maestro_local.db.models import Project, Sprint
    from maestro_local.metrics_pdf import collect_metrics, build_metrics_pdf
    c = _client()
    pid, spid, _, _ = _projeto()

    fim_sprint = (date.today() + timedelta(days=5)).isoformat()
    c.patch(f"/api/sprints/{spid}", json={"endDate": fim_sprint})
    alvo = (date.today() + timedelta(days=40)).isoformat()
    c.patch(f"/api/projects/{pid}", json={"targetDate": alvo})

    s = get_session()
    try:
        p = s.get(Project, pid)
        m = collect_metrics(s, p)
        assert m["regressivas"]["sprint"]["days"] == 5
        assert m["regressivas"]["sprint"]["name"] == "S1"
        assert m["regressivas"]["projeto"]["days"] == 40
        pdf = build_metrics_pdf(s, p)
        assert pdf.startswith(b"%PDF")
    finally:
        s.close()


def test_goals_crud_e_progresso(temp_db):
    c = _client()
    pid, sprint_id, todo_id, done_id = _projeto()

    s = get_session()
    try:
        s.add(Task(project_id=pid, column_id=todo_id, number=1, title="A",
                   sprint_id=sprint_id))
        s.add(Task(project_id=pid, column_id=done_id, number=2, title="B",
                   sprint_id=sprint_id))
        s.commit()
    finally:
        s.close()

    r = c.post(f"/api/projects/{pid}/goals", json={
        "name": "Entregar tudo", "sprintId": sprint_id})
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    assert r.json()["progress"] == {"total": 2, "done": 1, "pct": 50, "daysLeft": None}

    r = c.get(f"/api/projects/{pid}/goals")
    assert r.status_code == 200 and len(r.json()) == 1

    r = c.patch(f"/api/goals/{gid}", json={"name": "Novo nome", "tag": "onda-1"})
    assert r.status_code == 200 and r.json()["name"] == "Novo nome"
    assert r.json()["progress"] == {"total": 0, "done": 0, "pct": 0, "daysLeft": None}

    r = c.delete(f"/api/goals/{gid}")
    assert r.status_code == 200
    assert c.get(f"/api/goals/{gid}").status_code == 404


def test_goal_com_data_e_filtros(temp_db):
    from datetime import date, timedelta
    c = _client()
    pid, sprint_id, todo_id, _ = _projeto()
    alvo = (date.today() + timedelta(days=5)).isoformat()

    r = c.post(f"/api/projects/{pid}/goals", json={
        "name": "Onda", "dueDate": alvo, "tag": "x", "sprintId": sprint_id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["progress"]["daysLeft"] == 5

    r = c.post(f"/api/projects/{pid}/goals", json={"name": "Ruim", "sprintId": 9999})
    assert r.status_code == 400


def test_members_crud_e_stats(temp_db):
    c = _client()
    pid, _, todo_id, done_id = _projeto()
    s = get_session()
    try:
        s.add(Task(project_id=pid, column_id=done_id, number=1, title="A", assignee="Walter"))
        s.commit()
    finally:
        s.close()

    r = c.post(f"/api/projects/{pid}/members", json={"name": "Walter"})
    assert r.status_code == 200, r.text
    mid = r.json()["id"]

    r = c.post(f"/api/projects/{pid}/members", json={"name": "  walter "})
    assert r.status_code == 200 and r.json()["id"] == mid  # idempotente

    r = c.get(f"/api/projects/{pid}/members")
    assert r.status_code == 200
    walter = next(m for m in r.json() if m["name"] == "Walter")
    assert walter["total"] == 1 and walter["done"] == 1 and walter["pct"] == 100

    r = c.delete(f"/api/members/{mid}")
    assert r.status_code == 200
    assert c.get(f"/api/projects/{pid}/members").json() == []
