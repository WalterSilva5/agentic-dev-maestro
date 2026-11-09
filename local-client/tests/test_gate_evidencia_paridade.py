import pytest
from fastapi.testclient import TestClient
from relay.api.app import app
from relay.db.models import init_db, get_session, Project, BoardColumn, Task
import tempfile, os

@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    from relay.db.models import get_engine, _SessionLocal, _active_db_path, Base
    import relay.db.models as m
    m._engine = None
    m._SessionLocal = None
    m._active_db_path = db_path
    init_db(db_path)
    with TestClient(app) as c:
        yield c
    m._engine = None
    m._SessionLocal = None

def _create_project(client):
    r = client.post("/api/projects", json={"name": "Proj Gate", "key": "GATE"})
    assert r.status_code == 200
    pid = r.json()["id"]
    return pid

def _ensure_columns(client, pid):
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}
    # garante colunas do template para o gate
    needed = ["In Test", "Dev Review"]
    for name in needed:
        if name not in cols:
            r = client.post(f"/api/projects/{pid}/columns", json={"name": name})
            assert r.status_code == 200
    return {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}

def test_gate_in_test_sem_evidencia_bloqueia(client):
    pid = _create_project(client)
    cols = _ensure_columns(client, pid)
    # pega primeira coluna como origem
    origem = list(cols.values())[0]
    task = client.post("/api/tasks", json={"projectId": pid, "columnId": origem, "title": "endpoint x", "priority": "MEDIUM"}).json()
    code = task["code"]
    r = client.post(f"/api/tasks/{code}/move", json={"columnId": cols["In Test"]})
    assert r.status_code == 422
    assert "EVIDENCIA" in r.json()["detail"]["missing"]
    r = client.post(f"/api/tasks/{code}/evidence", json={"kind": "REQUEST_RESPONSE", "title": "t", "url": "http://x", "result": "OK"})
    assert r.status_code == 200
    r = client.post(f"/api/tasks/{code}/move", json={"columnId": cols["In Test"]})
    assert r.status_code == 200
    task2 = client.post("/api/tasks", json={"projectId": pid, "columnId": origem, "title": "endpoint y"}).json()
    code2 = task2["code"]
    client.post(f"/api/tasks/{code2}/evidence", json={"kind": "REQUEST_RESPONSE", "title": "t", "url": "http://x", "result": "OK"})
    client.post(f"/api/tasks/{code2}/parity", json={"case_name": "c1", "status": "DIVERGENCIA"})
    r = client.post(f"/api/tasks/{code2}/move", json={"columnId": cols["In Test"]})
    assert r.status_code == 422
    assert "PARITY_FIEL" in r.json()["detail"]["missing"]

def test_gate_dev_review_sem_code_review_bloqueia(client):
    pid = _create_project(client)
    cols = _ensure_columns(client, pid)
    origem = list(cols.values())[0]
    task = client.post("/api/tasks", json={"projectId": pid, "columnId": origem, "title": "ep"}).json()
    code = task["code"]
    r = client.post(f"/api/tasks/{code}/move", json={"columnId": cols["Dev Review"]})
    assert r.status_code == 422
    assert "CODE_REVIEW" in r.json()["detail"]["missing"]
    tid = task["id"]
    client.post("/api/comments", json={"taskId": tid, "body": "review", "type": "CODE_REVIEW"})
    r = client.post(f"/api/tasks/{code}/move", json={"columnId": cols["Dev Review"]})
    assert r.status_code == 200

def test_quality_endpoint(client):
    pid = _create_project(client)
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}
    origem = list(cols.values())[0]
    task = client.post("/api/tasks", json={"projectId": pid, "columnId": origem, "title": "q"}).json()
    code = task["code"]
    r = client.get(f"/api/tasks/{code}/quality")
    assert r.status_code == 200
    assert r.json()["evidence_count"] == 0
    assert r.json()["parity"]["fiel"] == 0
    client.post(f"/api/tasks/{code}/evidence", json={"kind": "SQL", "title": "sql", "result": "OK"})
    client.post(f"/api/tasks/{code}/parity", json={"case_name": "c", "status": "FIEL"})
    r = client.get(f"/api/tasks/{code}/quality")
    assert r.json()["evidence_count"] == 1
    assert r.json()["parity"]["fiel"] == 1
