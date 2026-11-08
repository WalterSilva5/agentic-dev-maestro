"""Testes do formato de doc de daily (parser/render) e do import/export via API."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.daily_doc import (
    format_date_br,
    parse_daily_markdown,
    parse_date_br,
    render_daily_markdown,
    suggested_filename,
)
from maestro_local.db.models import init_db

# Exemplo no formato que o time usa no vault (com todas as seções).
EXEMPLO = """# Daily - 04/11/2026 — config E3/E4 na VM (tema do dia)

Ambiente de referência de volta: módulo `config` fechado em 26/26.

## Itens trabalhados

### `13972` — modo de conexão do banco
- Criado o seam `migracao.config`.
- Testes: seam 5/5 · serviço 3/3.
- Commit `48699b53`.

### `13967` — itens da campanha
- 4/4 semânticos.

## Estado da sprint

**Progresso:** 45/156 = 29% · `config` 26/26.

## Pendências

- **PRs do `config`** — review do `#8910`.
- Testes manuais dos cards em `Dev Box`
  (bateria `CONFIG/03`).
"""


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
def project(client):
    return client.post("/api/projects", json={"name": "P Daily", "key": "PDA"}).json()["id"]


# --------------------------------------------------------------------------
# parser / render
# --------------------------------------------------------------------------

def test_parse_data_em_varios_formatos():
    assert parse_date_br("04/11/2026") == "2026-11-04"
    assert parse_date_br("04-11-2026") == "2026-11-04"
    assert parse_date_br("2026-11-04") == "2026-11-04"
    assert parse_date_br("sem data") is None
    assert format_date_br("2026-11-04") == "04/11/2026"


def test_parse_exemplo_completo():
    day, title, blocks = parse_daily_markdown(EXEMPLO)
    assert day == "2026-11-04"
    assert title == "config E3/E4 na VM (tema do dia)"

    secoes = [b.section for b in blocks]
    assert secoes == ["INTRO", "ITEMS", "ITEMS", "SPRINT", "PENDING", "PENDING"]

    itens = [b for b in blocks if b.section == "ITEMS"]
    assert itens[0].task_code == "13972"
    assert "modo de conexão do banco" in itens[0].title
    assert "seam `migracao.config`" in itens[0].body
    assert itens[1].task_code == "13967"

    sprint = next(b for b in blocks if b.section == "SPRINT")
    assert "45/156" in sprint.body

    pends = [b for b in blocks if b.section == "PENDING"]
    assert len(pends) == 2
    # bullet multilinha fica inteiro no mesmo registro
    assert "CONFIG/03" in pends[1].body


def test_render_reconstroi_o_formato():
    day, title, blocks = parse_daily_markdown(EXEMPLO)
    md = render_daily_markdown(day, title, blocks)

    assert md.startswith("# Daily - 04/11/2026 — config E3/E4 na VM (tema do dia)")
    assert "\n## Itens trabalhados\n" in md
    assert "\n### `13972` — modo de conexão do banco\n" in md
    assert "\n## Estado da sprint\n" in md
    assert "\n## Pendências\n" in md
    assert "- **PRs do `config`** — review do `#8910`." in md


def test_round_trip_estavel():
    """parse(render(parse(x))) == parse(x) — o formato não deriva."""
    day, title, blocks = parse_daily_markdown(EXEMPLO)
    md1 = render_daily_markdown(day, title, blocks)

    day2, title2, blocks2 = parse_daily_markdown(md1)
    md2 = render_daily_markdown(day2, title2, blocks2)

    assert (day2, title2) == (day, title)
    assert md2 == md1


def test_titulo_do_dia_sobrevive_ao_round_trip():
    md = "# Daily - 10/10/2026 — tema X\n\n## Itens trabalhados\n\n### `1` — item\n- feito\n"
    day, title, blocks = parse_daily_markdown(md)
    assert title == "tema X"
    out = render_daily_markdown(day, title, blocks)
    assert out.startswith("# Daily - 10/10/2026 — tema X")


def test_suggested_filename_formato_do_vault():
    nome, mes = suggested_filename("2026-11-04", "config E3 na VM")
    assert nome == "04-11-2026 - Daily - config E3 na VM.md"
    assert mes == "2026-11"


def test_round_trip_arquivo_real_do_vault():
    """Se o vault estiver disponível, o arquivo do dia 04/11 tem que bater 100%."""
    vault = Path(
        "/home/wsi/repositorios/github/vault-docs-projetos/tarefas/VERZEL/GAV/daily"
        "/2026-11/04-11-2026 - Daily - config E3 na VM.md"
    )
    if not vault.exists():
        pytest.skip("vault não disponível nesta máquina")

    import difflib

    original = vault.read_text()
    day, title, blocks = parse_daily_markdown(original)
    gerado = render_daily_markdown(day, title, blocks)

    a = [l.rstrip() for l in original.split("\n") if l.strip()]
    b = [l.rstrip() for l in gerado.split("\n") if l.strip()]
    diff = [
        l for l in difflib.unified_diff(a, b, lineterm="", n=0)
        if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))
    ]
    assert diff == [], f"round-trip divergiu em {len(diff)} linha(s): {diff[:5]}"


# --------------------------------------------------------------------------
# API import / export
# --------------------------------------------------------------------------

def test_api_import_cria_registros(client, project):
    r = client.post(f"/api/projects/{project}/daily/import", json={"content": EXEMPLO, "replace": True})
    assert r.status_code == 200
    data = r.json()
    assert data["date"] == "2026-11-04"
    assert data["created"] == 6

    entries = client.get(f"/api/projects/{project}/daily", params={"date": "2026-11-04"}).json()
    assert len(entries) == 6
    assert [e["section"] for e in entries][0] == "INTRO"
    item = next(e for e in entries if e["taskCode"] == "13972")
    assert "modo de conexão" in item["title"]


def test_api_import_substitui_quando_replace(client, project):
    client.post(f"/api/projects/{project}/daily/import", json={"content": EXEMPLO, "replace": True})
    r = client.post(f"/api/projects/{project}/daily/import", json={"content": EXEMPLO, "replace": True})
    assert r.status_code == 200
    entries = client.get(f"/api/projects/{project}/daily", params={"date": "2026-11-04"}).json()
    assert len(entries) == 6  # não duplicou


def test_api_export_devolve_markdown_e_nome(client, project):
    client.post(f"/api/projects/{project}/daily/import", json={"content": EXEMPLO, "replace": True})
    r = client.get(f"/api/projects/{project}/daily/export", params={"date": "2026-11-04"})
    assert r.status_code == 200
    data = r.json()
    assert data["date"] == "2026-11-04"
    assert data["monthDir"] == "2026-11"
    assert data["filename"].startswith("04-11-2026 - Daily - ")
    assert data["filename"].endswith(".md")
    assert data["markdown"].startswith("# Daily - 04/11/2026")
    assert "## Itens trabalhados" in data["markdown"]
    assert "`13972`" in data["markdown"]


def test_api_export_sem_registros_404(client, project):
    r = client.get(f"/api/projects/{project}/daily/export", params={"date": "2030-01-01"})
    assert r.status_code == 404


def test_api_import_validacoes(client, project):
    assert client.post(f"/api/projects/{project}/daily/import", json={}).status_code == 400
    assert client.post(
        f"/api/projects/{project}/daily/import", json={"content": "sem cabecalho"}
    ).status_code == 400
    assert client.post(
        f"/api/projects/{project}/daily/import", json={"path": "relativo.md"}
    ).status_code == 400
    assert client.post(
        f"/api/projects/{project}/daily/import", json={"path": "/nao/existe.md"}
    ).status_code == 404
    assert client.post("/api/projects/9999/daily/import", json={"content": EXEMPLO}).status_code == 404
