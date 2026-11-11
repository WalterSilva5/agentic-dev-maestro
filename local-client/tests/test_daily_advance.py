"""Resumo do avanço ontem → hoje a partir dos docs de daily (IA + fallback)."""
from datetime import date, timedelta

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
    r = client.post("/api/projects", json={"name": "Proj Avanço", "key": "AVA"})
    assert r.status_code == 200
    return r.json()["id"]


@pytest.fixture(autouse=True)
def _limpa_cache():
    import relay.daily_advance as da
    da._CACHE.clear()
    yield
    da._CACHE.clear()


def _dias():
    hoje = date.today()
    return (hoje - timedelta(days=1)).isoformat(), hoje.isoformat()


def test_sem_registros_devolve_vazio(client, project):
    d = client.get(f"/api/projects/{project}/metrics/daily-advance").json()
    assert d["engine"] == "empty"
    assert d["summary"] == ""
    assert d["yesterday"]["registros"] == 0
    assert d["today"]["registros"] == 0


def test_heuristic_resume_fatos_sem_ia(client, project):
    ontem, hoje = _dias()
    client.post(f"/api/projects/{project}/daily",
                json={"body": "fechei o endpoint X", "kind": "WORK", "author": "ana",
                      "minutes": 60, "date": ontem})
    client.post(f"/api/projects/{project}/daily",
                json={"body": "travou no DBA", "kind": "BLOCKER", "date": ontem})
    client.post(f"/api/projects/{project}/daily",
                json={"body": "revisando PR", "kind": "WORK", "date": hoje})

    d = client.get(f"/api/projects/{project}/metrics/daily-advance").json()
    assert d["engine"] == "heuristic"  # sem provedor no ambiente de teste
    assert d["yesterday"] == {"date": ontem, "registros": 2,
                              "tipos": {"WORK": 1, "BLOCKER": 1}, "minutos": 60}
    assert d["today"]["registros"] == 1
    assert "Ontem" in d["summary"] and "Hoje" in d["summary"]
    assert "2 registro(s)" in d["summary"]

    # segunda chamada usa cache curto
    d2 = client.get(f"/api/projects/{project}/metrics/daily-advance").json()
    assert d2["cached"] is True
    # refresh ignora o cache
    d3 = client.get(f"/api/projects/{project}/metrics/daily-advance", params={"refresh": 1}).json()
    assert d3["cached"] is False


def test_llm_quando_provedor_responde(client, project, monkeypatch):
    import relay.daily_advance as da

    ontem, hoje = _dias()
    client.post(f"/api/projects/{project}/daily",
                json={"body": "migrei o endpoint X", "date": ontem})

    monkeypatch.setattr("relay.ai.llm.invoke_text", lambda *a, **k: "Avancei X ontem; hoje sigo em Y.")
    # limpa o cache do modulo para o teste passar pelo LLM
    da._CACHE.clear()
    d = client.get(f"/api/projects/{project}/metrics/daily-advance", params={"refresh": 1}).json()
    assert d["engine"] == "llm"
    assert "Avancei X" in d["summary"]


def test_projeto_inexistente_404(client):
    assert client.get("/api/projects/9999/metrics/daily-advance").status_code == 404
