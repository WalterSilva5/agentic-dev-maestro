"""Resumo do avanço ontem → hoje a partir dos docs de daily do vault.

Fonte: o diretório raiz configurado no projeto (`daily_docs_path`), no padrão
`YYYY-MM/DD-MM-YYYY - Daily - <tema>.md`. Sem diretório configurado (ou
ilegível), o recurso fica indisponível (`configured: false`).
"""
import pytest
from datetime import date, timedelta
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


def _vault(tmp_path, ontem_txt=None, hoje_txt=None):
    """Monta um diretório no padrão do vault com docs de ontem/hoje."""
    from datetime import date as _d, timedelta as _td
    hoje = _d.today()
    ontem = hoje - _td(days=1)
    raiz = tmp_path / "daily"
    for dia, texto in ((ontem, ontem_txt), (hoje, hoje_txt)):
        if texto is None:
            continue
        pasta = raiz / dia.strftime("%Y-%m")
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / f"{dia.strftime('%d-%m-%Y')} - Daily - tema.md").write_text(texto, encoding="utf-8")
    return raiz


def test_sem_diretorio_nao_funciona(client, project):
    d = client.get(f"/api/projects/{project}/metrics/daily-advance").json()
    assert d["configured"] is False
    assert d["engine"] == "empty"
    assert d["summary"] == ""


def test_diretorio_inexistente_nao_funciona(client, project, tmp_path):
    r = client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(tmp_path / "nao-existe")})
    assert r.status_code == 200
    d = client.get(f"/api/projects/{project}/metrics/daily-advance").json()
    assert d["configured"] is False
    assert d["reason"] == "not_found"


def test_path_relativo_rejeitado(client, project):
    assert client.patch(f"/api/projects/{project}", json={"dailyDocsPath": "relativo/path"}).status_code == 400


def test_resume_docs_do_vault(client, project, tmp_path):
    raiz = _vault(tmp_path,
                  ontem_txt="# Daily — ontem\n\n## Endpoint X\n\n- fechei o endpoint X\n\n## Revisão Y\n\n- revisei Y\n",
                  hoje_txt="# Daily — hoje\n\n## Deploy Z\n\n- subi Z em HML\n")
    r = client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(raiz)})
    assert r.status_code == 200 and r.json()["dailyDocsPath"] == str(raiz)

    d = client.get(f"/api/projects/{project}/metrics/daily-advance").json()
    assert d["configured"] is True
    assert d["engine"] == "heuristic"  # sem provedor no ambiente de teste
    assert d["yesterday"]["topicos"] == ["Endpoint X", "Revisão Y"]
    assert d["today"]["topicos"] == ["Deploy Z"]
    assert d["summary"] == "Ontem o foco foi Endpoint X e Revisão Y. Hoje o dia é sobre Deploy Z."
    assert "registro(s)" not in d["summary"]

    # segunda chamada usa o cache curto
    assert client.get(f"/api/projects/{project}/metrics/daily-advance").json()["cached"] is True
    # refresh ignora o cache
    assert client.get(f"/api/projects/{project}/metrics/daily-advance", params={"refresh": 1}).json()["cached"] is False


def test_cabecalhos_genericos_nao_viram_topico(client, project, tmp_path):
    raiz = _vault(tmp_path,
                  ontem_txt="# Daily\n\n## Itens trabalhados\n\n- fiz X\n\n## Docs\n\n- y\n\n## Ontem 01/01 - resumo\n\n- z\n\n## Endpoint X\n\n- fechei X\n",
                  hoje_txt=None)
    client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(raiz)})
    d = client.get(f"/api/projects/{project}/metrics/daily-advance", params={"refresh": 1}).json()
    assert d["yesterday"]["topicos"] == ["Endpoint X"]
    assert "Itens trabalhados" not in d["summary"]
    assert d["summary"].startswith("Ontem o foco foi Endpoint X.")


def test_sem_cabecalho_cai_para_contagem(client, project, tmp_path):
    raiz = _vault(tmp_path, ontem_txt="texto corrido sem secao\n", hoje_txt=None)
    client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(raiz)})
    d = client.get(f"/api/projects/{project}/metrics/daily-advance", params={"refresh": 1}).json()
    assert d["yesterday"]["topicos"] == []
    assert "1 registro(s)" in d["summary"]


def test_subdiretorio_legado_mm_yyyy(client, project, tmp_path):
    from datetime import date as _d, timedelta as _td
    ontem = _d.today() - _td(days=1)
    raiz = tmp_path / "daily"
    pasta = raiz / ontem.strftime("%m-%Y")
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{ontem.strftime('%d-%m-%Y')} - Daily - legado.md").write_text("# Daily\n\n- item legado\n", encoding="utf-8")
    client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(raiz)})
    d = client.get(f"/api/projects/{project}/metrics/daily-advance").json()
    assert d["configured"] is True
    assert d["yesterday"]["registros"] == 1


def test_llm_quando_provedor_responde(client, project, tmp_path, monkeypatch):
    import relay.daily_advance as da

    _vault(tmp_path, ontem_txt="# Daily\n\n- migrei X\n", hoje_txt="# Daily\n\n- reviso Y\n")
    # aponta o projeto para o vault temporário
    raiz = tmp_path / "daily"
    client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(raiz)})
    monkeypatch.setattr("relay.ai.llm.invoke_text", lambda *a, **k: "Avancei X ontem; hoje sigo em Y.")
    da._CACHE.clear()
    d = client.get(f"/api/projects/{project}/metrics/daily-advance", params={"refresh": 1}).json()
    assert d["engine"] == "llm"
    assert "Avancei X" in d["summary"]


def test_projeto_inexistente_404(client):
    assert client.get("/api/projects/9999/metrics/daily-advance").status_code == 404
    assert client.get("/api/projects/9999/metrics/daily-summary", params={"date": "2026-11-10"}).status_code == 404


def test_daily_summary_data_invalida_400(client, project):
    assert client.get(f"/api/projects/{project}/metrics/daily-summary").status_code == 422
    assert client.get(f"/api/projects/{project}/metrics/daily-summary", params={"date": "10/11/2026"}).status_code == 400


def test_daily_summary_por_dia(client, project, tmp_path):
    from datetime import date as _d

    raiz = tmp_path / "daily"
    pasta = raiz / "2026-11"
    pasta.mkdir(parents=True)
    (pasta / "10-11-2026 - Daily - tema.md").write_text("# Daily\n\n## Migração Y\n\n- fechei Y\n", encoding="utf-8")
    client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(raiz)})

    d = client.get(f"/api/projects/{project}/metrics/daily-summary", params={"date": "2026-11-10"}).json()
    assert d["configured"] is True
    assert d["engine"] == "heuristic"
    assert d["registros"] == 1
    assert d["summary"] == "O dia foi sobre Migração Y."

    vazio = client.get(f"/api/projects/{project}/metrics/daily-summary", params={"date": "2026-11-09"}).json()
    assert vazio["engine"] == "empty"
    assert vazio["summary"] == ""

    sem_cfg = client.post("/api/projects", json={"name": "Sem Dir", "key": "SDIR"}).json()["id"]
    d2 = client.get(f"/api/projects/{sem_cfg}/metrics/daily-summary", params={"date": "2026-11-10"}).json()
    assert d2["configured"] is False


def test_daily_summary_llm(client, project, tmp_path, monkeypatch):
    import relay.daily_advance as da

    raiz = tmp_path / "daily"
    pasta = raiz / "2026-11"
    pasta.mkdir(parents=True)
    (pasta / "10-11-2026 - Daily - tema.md").write_text("# Daily\n\n- fiz X\n", encoding="utf-8")
    client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(raiz)})
    monkeypatch.setattr("relay.ai.llm.invoke_text", lambda *a, **k: "Resumo do dia X.")
    da._CACHE.clear()
    d = client.get(f"/api/projects/{project}/metrics/daily-summary", params={"date": "2026-11-10"}).json()
    assert d["engine"] == "llm"
    assert d["summary"] == "Resumo do dia X."


def test_salvar_resumo_gera_doc_padronizado(client, project, tmp_path):
    raiz = tmp_path / "daily"
    pasta = raiz / "2026-11"
    pasta.mkdir(parents=True)
    (pasta / "10-11-2026 - Daily - tema.md").write_text("# Daily\n\n- fechei X\n", encoding="utf-8")
    client.patch(f"/api/projects/{project}", json={"dailyDocsPath": str(raiz)})

    r = client.post(f"/api/projects/{project}/metrics/daily-summary", json={"date": "2026-11-10"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["saved"] is True
    assert d["file"] == "generated-daily-10-11-2026.md"

    alvo = raiz / "generated-daily-10-11-2026.md"
    assert alvo.exists()
    texto = alvo.read_text(encoding="utf-8")
    assert texto.startswith("# Resumo gerado por IA — 10/11/2026")
    assert "10-11-2026 - Daily - tema.md" in texto

    # GET passa a indicar que existe resumo salvo
    g = client.get(f"/api/projects/{project}/metrics/daily-summary", params={"date": "2026-11-10"}).json()
    assert g["saved"] is True
    assert g["savedFile"] == "generated-daily-10-11-2026.md"


def test_salvar_sem_config_400(client, project):
    r = client.post(f"/api/projects/{project}/metrics/daily-summary", json={"date": "2026-11-10"})
    assert r.status_code == 400
    r = client.post(f"/api/projects/{project}/metrics/daily-summary", json={"date": "10/11/2026"})
    assert r.status_code == 400
