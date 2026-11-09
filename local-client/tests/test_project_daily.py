"""Testes do Daily do projeto (registro de trabalho por dia).

Cobre criação, filtros (dia/intervalo/tipo/autor/texto), edição, exclusão,
validações e o resumo usado pelo painel do board.
"""
import pytest
from fastapi.testclient import TestClient

from relay.api.app import app
from relay.db.models import init_db


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    import relay.db.models as m
    m._engine = None
    m._SessionLocal = None
    m._active_db_path = db_path
    init_db(db_path)
    with TestClient(app) as c:
        yield c
    m._engine = None
    m._SessionLocal = None


@pytest.fixture
def project(client):
    r = client.post("/api/projects", json={"name": "Proj Daily", "key": "DAILY"})
    assert r.status_code == 200
    return r.json()["id"]


def _create(client, pid, **body):
    payload = {"body": "trabalhei no endpoint X"}
    payload.update(body)
    return client.post(f"/api/projects/{pid}/daily", json=payload)


def test_cria_e_lista_por_dia(client, project):
    r = _create(client, project, body="implementei E2E", kind="WORK", author="ana", minutes=60, date="2026-11-05")
    assert r.status_code == 200
    entry = r.json()
    assert entry["kind"] == "WORK"
    assert entry["minutes"] == 60
    assert entry["date"] == "2026-11-05"

    r = _create(client, project, body="bloqueio de DBA", kind="BLOCKER", date="2026-11-06")
    assert r.status_code == 200

    all_entries = client.get(f"/api/projects/{project}/daily").json()
    assert len(all_entries) == 2
    # ordenado do mais recente para o mais antigo
    assert [e["date"] for e in all_entries] == ["2026-11-06", "2026-11-05"]


def test_filtra_por_dia_intervalo_tipo_autor_e_texto(client, project):
    _create(client, project, body="alpha um", date="2026-11-01", kind="WORK", author="ana")
    _create(client, project, body="beta dois", date="2026-11-02", kind="BLOCKER", author="bia")
    _create(client, project, body="gamma tres", date="2026-11-03", kind="DECISION", author="ana")

    assert len(client.get(f"/api/projects/{project}/daily", params={"date": "2026-11-02"}).json()) == 1
    assert len(client.get(f"/api/projects/{project}/daily", params={"dateFrom": "2026-11-02"}).json()) == 2
    assert len(client.get(f"/api/projects/{project}/daily", params={"dateTo": "2026-11-02"}).json()) == 2
    assert len(client.get(f"/api/projects/{project}/daily", params={"kind": "BLOCKER"}).json()) == 1
    assert len(client.get(f"/api/projects/{project}/daily", params={"author": "ana"}).json()) == 2
    assert len(client.get(f"/api/projects/{project}/daily", params={"q": "gamma"}).json()) == 1


def test_edita_e_exclui(client, project):
    entry = _create(client, project, body="texto original", date="2026-11-04").json()

    r = client.patch(f"/api/project-daily/{entry['id']}", json={"body": "texto revisado", "kind": "NOTE", "minutes": 30})
    assert r.status_code == 200
    assert r.json()["body"] == "texto revisado"
    assert r.json()["kind"] == "NOTE"
    assert r.json()["minutes"] == 30

    assert client.delete(f"/api/project-daily/{entry['id']}").status_code == 200
    assert client.get(f"/api/projects/{project}/daily").json() == []


def test_validacoes(client, project):
    assert client.post(f"/api/projects/{project}/daily", json={"body": "   "}).status_code == 400
    assert client.post(f"/api/projects/{project}/daily", json={"body": "x", "kind": "FOO"}).status_code == 400
    assert client.post(f"/api/projects/{project}/daily", json={"body": "x", "date": "08/11/2026"}).status_code == 400
    assert client.post("/api/projects/9999/daily", json={"body": "x"}).status_code == 404
    assert client.patch("/api/project-daily/9999", json={"body": "x"}).status_code == 404
    assert client.delete("/api/project-daily/9999").status_code == 404


def test_resumo_por_dia_tipo_e_autor(client, project):
    _create(client, project, body="a", date="2026-11-01", kind="WORK", author="ana", minutes=60)
    _create(client, project, body="b", date="2026-11-01", kind="BLOCKER", author="bia")
    _create(client, project, body="c", date="2026-11-02", kind="WORK", author="ana", minutes=30)

    r = client.get(f"/api/projects/{project}/daily/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["totalMinutes"] == 90
    assert data["byKind"]["WORK"] == 2
    assert data["byKind"]["BLOCKER"] == 1
    assert data["byAuthor"] == {"ana": 2, "bia": 1}
    assert len(data["days"]) == 2
    # mais recente primeiro
    assert data["days"][0]["date"] == "2026-11-02"


def test_isolado_por_projeto(client):
    p1 = client.post("/api/projects", json={"name": "P1", "key": "P1D"}).json()["id"]
    p2 = client.post("/api/projects", json={"name": "P2", "key": "P2D"}).json()["id"]
    _create(client, p1, body="do p1")
    _create(client, p2, body="do p2")

    assert [e["body"] for e in client.get(f"/api/projects/{p1}/daily").json()] == ["do p1"]
    assert [e["body"] for e in client.get(f"/api/projects/{p2}/daily").json()] == ["do p2"]
