"""Testes do relatório de métricas em PDF."""
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
    from relay.db.models import get_session, Project
    from relay.metrics_pdf import build_metrics_pdf, collect_metrics

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
        # por pessoa também tem a leitura de dev concluído (sem Dev Box = aceite)
        ana = next(x for x in m["por_pessoa"] if x["nome"] == "ana")
        assert ana["developed"] == ana["done"] == 1
        assert ana["developedPct"] == ana["pct"] == 33
        # prioridades
        assert m["por_prioridade"].get("HIGH") == 1
        # daily agregado
        assert m["daily"]["total"] == 1
        assert m["daily"]["minutos"] == 60

        pdf = build_metrics_pdf(s, p)
        assert pdf.startswith(b"%PDF")
    finally:
        s.close()


def test_pdf_tem_graficos_dos_mesmos_dados_da_ui(client, projeto_com_tarefas):
    """O PDF precisa ter os donuts (Por coluna/Responsável/Prioridade/Módulo),
    não apenas tabelas — é o pedido de paridade com a interface."""
    from relay.db.models import get_session, Project
    from relay.metrics_pdf import (
        _dados_colunas,
        _dados_modulos,
        _dados_pessoas,
        _dados_prioridade,
        collect_metrics,
    )

    s = get_session()
    try:
        m = collect_metrics(s, s.get(Project, projeto_com_tarefas))
    finally:
        s.close()

    colunas = _dados_colunas(m)
    pessoas = _dados_pessoas(m)
    prioridade = _dados_prioridade(m)
    modulos = _dados_modulos(m)

    # colunas com cards viram fatias
    assert sum(v for _r, v, _c in colunas) == m["total"]
    # "Sem responsável" aparece com a cor cinza da interface
    if any(p["sem_dono"] for p in m["por_pessoa"]):
        cor = dict((r, c) for r, _v, c in pessoas)["Sem responsável"]
        assert cor.upper() == "#9CA3AF"
    # prioridade mantém a ordem e as cores da UI
    assert [r for r, _v, _c in prioridade] == ["Urgente", "Alta", "Média", "Baixa"]
    assert dict((r, c) for r, _v, c in prioridade)["Alta"] == "#EA580C"
    # módulos (labels) presentes
    assert all(v > 0 for _r, v, _c in modulos)


def test_pdf_oculta_por_responsavel_quando_projeto_pede(client, projeto_com_tarefas):
    """Default oculto; ao exibir, o PDF traz 'Por responsável' (tela e export)."""
    import io
    from pypdf import PdfReader

    def texto(pdf_bytes: bytes) -> str:
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf_bytes)).pages)

    pid = projeto_com_tarefas
    assert client.get(f"/api/projects/{pid}/board").json()["hideAssignee"] is True

    r = client.get(f"/api/projects/{pid}/metrics/export.pdf")
    assert r.status_code == 200
    assert "Por responsável" not in texto(r.content)

    r = client.patch(f"/api/projects/{pid}", json={"hideAssignee": False})
    assert r.status_code == 200 and r.json()["hideAssignee"] is False

    r = client.get(f"/api/projects/{pid}/metrics/export.pdf")
    assert r.status_code == 200
    assert "Por responsável" in texto(r.content)


def test_pdf_duas_paginas_no_maximo_para_projeto_pequeno(client, projeto_com_tarefas):
    """Projeto pequeno não deve gerar PDF gigante."""
    r = client.get(f"/api/projects/{projeto_com_tarefas}/metrics/export.pdf")
    assert r.status_code == 200
    assert r.content.count(b"/Type /Page") <= 4


def test_pdf_inclui_sem_responsavel_quando_existe(client):
    pid = client.post("/api/projects", json={"name": "Sem dono", "key": "SDO"}).json()["id"]
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}
    client.post("/api/tasks", json={"projectId": pid, "columnId": cols["A fazer"], "title": "sem dono"})

    from relay.db.models import get_session, Project
    from relay.metrics_pdf import collect_metrics

    s = get_session()
    try:
        m = collect_metrics(s, s.get(Project, pid))
        sem = next((x for x in m["por_pessoa"] if x["sem_dono"]), None)
        assert sem is not None
        assert sem["total"] == 1
    finally:
        s.close()
