"""Testes do relatório de métricas em PDF."""
import pytest
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.db.models import init_db


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    import maestro_local.db.models as m
    m._engine = None
    m._SessionLocal = None
    m._active_db_path = db_path
    init_db(db_path)
    with TestClient(app) as c:
        yield c
    m._engine = None
    m._SessionLocal = None


@pytest.fixture
def projeto_com_tarefas(client):
    pid = client.post("/api/projects", json={"name": "Proj Métricas", "key": "MET"}).json()["id"]
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}
    todo, doing = cols["A fazer"], cols["Fazendo"]
    feito = cols["Feito"]

    for i, (col, prio, quem) in enumerate([
        (todo, "HIGH", "ana"),
        (todo, "MEDIUM", "bia"),
        (doing, "URGENT", "ana"),
        (feito, "LOW", "ana"),
    ]):
        r = client.post("/api/tasks", json={
            "projectId": pid,
            "columnId": col,
            "title": f"tarefa {i}",
            "priority": prio,
            "assignee": quem,
        })
        assert r.status_code == 200

    # um registro de daily para aparecer no relatório
    client.post(f"/api/projects/{pid}/daily", json={
        "body": "trabalhei nas tarefas", "date": "2026-11-01", "kind": "WORK", "minutes": 60,
    })
    return pid


def test_export_pdf_responde_pdf(client, projeto_com_tarefas):
    r = client.get(f"/api/projects/{projeto_com_tarefas}/metrics/export.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert ".pdf" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 1000


def test_export_pdf_404_para_projeto_inexistente(client):
    assert client.get("/api/projects/9999/metrics/export.pdf").status_code == 404


def test_pdf_tem_conteudo_esperado(client, projeto_com_tarefas):
    from maestro_local.db.models import get_session, Project
    from maestro_local.metrics_pdf import build_metrics_pdf, collect_metrics

    s = get_session()
    try:
        p = s.get(Project, projeto_com_tarefas)
        m = collect_metrics(s, p)
        assert m["total"] == 4
        assert m["done"] == 1
        assert m["pct"] == 25
        # "sem responsável" nunca some das métricas
        nomes = [x["nome"] for x in m["por_pessoa"]]
        assert "ana" in nomes and "bia" in nomes
        # prioridades
        assert m["por_prioridade"].get("HIGH") == 1
        # daily agregado
        assert m["daily"]["total"] == 1
        assert m["daily"]["minutos"] == 60

        pdf = build_metrics_pdf(s, p)
        assert pdf.startswith(b"%PDF")
    finally:
        s.close()


def test_pdf_inclui_sem_responsavel_quando_existe(client):
    pid = client.post("/api/projects", json={"name": "Sem dono", "key": "SDO"}).json()["id"]
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}
    client.post("/api/tasks", json={"projectId": pid, "columnId": cols["A fazer"], "title": "sem dono"})

    from maestro_local.db.models import get_session, Project
    from maestro_local.metrics_pdf import collect_metrics

    s = get_session()
    try:
        m = collect_metrics(s, s.get(Project, pid))
        sem = next((x for x in m["por_pessoa"] if x["sem_dono"]), None)
        assert sem is not None
        assert sem["total"] == 1
    finally:
        s.close()
