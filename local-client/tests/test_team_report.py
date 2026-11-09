"""Report semanal do time: números do board + anotações de gestão."""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.db.models import init_db
from maestro_local.team_report import compute_weekly, render_markdown, week_bounds


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
def projeto(client):
    """Projeto com fluxo completo, 2 membros e cards em semanas diferentes."""
    pid = client.post("/api/projects", json={"name": "Time", "key": "TM"}).json()["id"]
    client.post(f"/api/projects/{pid}/columns/template")
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}
    client.post(f"/api/projects/{pid}/members", json={"name": "Ana"})
    client.post(f"/api/projects/{pid}/members", json={"name": "Bruno"})

    def tarefa(titulo, coluna, assignee=None, labels=()):
        r = client.post("/api/tasks", json={
            "projectId": pid, "columnId": cols[coluna], "title": titulo, "assignee": assignee,
        }).json()
        for nome in labels:
            lb = client.post("/api/labels", json={"name": nome}).json()
            client.post(f"/api/labels/{lb['id']}/tasks/{r['id']}")
        return r

    # entregues nesta semana
    a1 = tarefa("config E1", "To do", "Ana", ["cfg-e1"])
    a2 = tarefa("config E2", "To do", "Ana", ["config"])
    # em aberto
    a3 = tarefa("cashier O1", "Doing", "Ana", ["onda-1"])
    b1 = tarefa("auth login", "Dev Box", "Bruno", ["auth"])
    # sem dono
    tarefa("sem dono", "To do")
    # tarefa local não entra
    local = client.post("/api/tasks", json={
        "projectId": pid, "title": "lembrete", "isLocal": True, "assignee": "Ana",
    }).json()

    for code in (a1["code"], a2["code"]):
        assert client.post(f"/api/tasks/{code}/move", json={"columnId": cols["Done"]}).status_code == 200

    # move uma entrega para a semana passada
    from maestro_local.db.models import Task, get_session
    s = get_session()
    t = s.query(Task).filter(Task.number == a2["number"]).first()
    t.done_at = datetime.now() - timedelta(days=10)
    s.commit()
    s.close()

    return {"pid": pid, "cols": cols, "ana": a1, "bruno": b1, "local": local}


# --------------------------------------------------------------------------
# semana
# --------------------------------------------------------------------------

def test_semana_normaliza_para_segunda():
    quarta = date(2026, 11, 4)
    inicio, fim = week_bounds(quarta)
    assert inicio == date(2026, 11, 2)      # segunda
    assert fim == date(2026, 11, 8)         # domingo


def test_api_semana_normaliza_qualquer_dia(client, projeto):
    for dia in ("2026-11-02", "2026-11-04", "2026-11-08"):
        d = client.get(f"/api/projects/{projeto['pid']}/team/weekly", params={"week": dia}).json()
        assert d["week"]["start"] == "2026-11-02"
        assert d["week"]["end"] == "2026-11-08"


def test_week_invalida_da_400(client, projeto):
    r = client.get(f"/api/projects/{projeto['pid']}/team/weekly", params={"week": "ontem"})
    assert r.status_code == 400


# --------------------------------------------------------------------------
# números por membro
# --------------------------------------------------------------------------

def test_entrega_da_semana_aparece_e_a_antiga_nao(client, projeto):
    hoje = date.today()
    d = client.get(
        f"/api/projects/{projeto['pid']}/team/weekly", params={"week": hoje.isoformat()}
    ).json()

    ana = next(m for m in d["members"] if m["name"] == "Ana")
    brunno = next(m for m in d["members"] if m["name"] == "Bruno")

    assert ana["deliveredCount"] == 1            # só a de hoje (a outra foi há 10 dias)
    assert ana["delivered"][0]["module"] == "config"   # cfg-e1 -> config
    assert ana["delivered"][0]["inferred"] is False
    assert ana["open"] == 1                     # cashier em Doing

    assert brunno["deliveredCount"] == 0
    assert brunno["open"] == 1
    assert brunno["byColumn"] == [{"name": "Dev Box", "count": 1}]


def test_tarefa_local_nao_entra_no_report(client, projeto):
    d = client.get(f"/api/projects/{projeto['pid']}/team/weekly").json()
    assert d["summary"]["cards"] == 5           # a local ficou de fora
    assert all(m["assigned"] <= 3 for m in d["members"])


def test_resumo_tem_colunas_e_sem_responsavel(client, projeto):
    d = client.get(f"/api/projects/{projeto['pid']}/team/weekly").json()
    r = d["summary"]
    assert r["cards"] == 5
    assert r["unassigned"] >= 1
    nomes = [c["name"] for c in r["byColumn"]]
    assert "Doing" in nomes and "Done" in nomes
    assert r["byModule"][0]["module"] in ("config", "cashier", "auth")


def test_ordenacao_por_entrega(client, projeto):
    d = client.get(f"/api/projects/{projeto['pid']}/team/weekly").json()
    assert d["members"][0]["name"] == "Ana"     # quem entregou vem primeiro


# --------------------------------------------------------------------------
# anotação do líder
# --------------------------------------------------------------------------

def test_salva_e_recupera_anotacao(client, projeto):
    semana = client.get(f"/api/projects/{projeto['pid']}/team/weekly").json()["week"]["start"]
    r = client.put(f"/api/projects/{projeto['pid']}/team/notes", json={
        "member": "Ana", "weekStart": "2026-11-04",   # quarta -> normaliza
        "highlights": "Fechou config no rito",
        "service": "Revisou 2 PRs",
        "attention": "PR sem revisor por 3 dias",
        "nextStep": "Onda 1 do cashier",
    })
    assert r.status_code == 200
    assert r.json()["weekStart"] == "2026-11-02"

    d = client.get(f"/api/projects/{projeto['pid']}/team/weekly",
                   params={"week": "2026-11-02"}).json()
    ana = next(m for m in d["members"] if m["name"] == "Ana")
    assert ana["note"]["highlights"] == "Fechou config no rito"
    assert ana["note"]["nextStep"] == "Onda 1 do cashier"
    assert semana  # só para deixar claro que a semana existe


def test_atualiza_anotacao_existente(client, projeto):
    url = f"/api/projects/{projeto['pid']}/team/notes"
    corpo = {"member": "Bruno", "weekStart": "2026-11-02", "highlights": "v1"}
    client.put(url, json=corpo)
    client.put(url, json={**corpo, "highlights": "v2"})
    d = client.get(f"/api/projects/{projeto['pid']}/team/weekly",
                   params={"week": "2026-11-02"}).json()
    bruno = next(m for m in d["members"] if m["name"] == "Bruno")
    assert bruno["note"]["highlights"] == "v2"


def test_membro_obrigatorio(client, projeto):
    r = client.put(f"/api/projects/{projeto['pid']}/team/notes", json={
        "member": "  ", "weekStart": "2026-11-02",
    })
    assert r.status_code == 422


# --------------------------------------------------------------------------
# markdown
# --------------------------------------------------------------------------

def test_markdown_nominal(client, projeto):
    client.put(f"/api/projects/{projeto['pid']}/team/notes", json={
        "member": "Ana", "weekStart": date.today().isoformat(),
        "highlights": "Fechou config", "attention": "Revisão travada",
        "nextStep": "Cashier O1",
    })
    r = client.get(f"/api/projects/{projeto['pid']}/team/weekly/export")
    assert r.status_code == 200
    md = r.text
    assert md.startswith("# Acompanhamento semanal da equipe")
    for trecho in ("## 1. Resumo do período", "## 2. Como cada membro está trabalhando",
                   "## 3. Distribuição de carga", "### Ana", "Fechou config",
                   "Revisão travada", "Cashier O1", "| Membro | Cards |"):
        assert trecho in md
    assert "attachment" in r.headers["content-disposition"]


def test_markdown_anonimizado_esconde_nomes(client, projeto):
    r = client.get(f"/api/projects/{projeto['pid']}/team/weekly/export",
                   params={"anonymized": 1})
    md = r.text
    assert "Pessoa A" in md
    assert "Ana" not in md
    assert "Bruno" not in md
    assert "versão anonimizada" in md
    assert "anonimizado" in r.headers["content-disposition"]


def test_render_sem_membros_nao_quebra():
    dados = {
        "project": {"id": 1, "key": "K", "name": "N"},
        "week": {"start": "2026-11-02", "end": "2026-11-08", "label": "02/11 a 08/11/2026"},
        "summary": {"cards": 0, "done": 0, "pct": 0, "doneInWeek": 0, "inferred": 0,
                    "open": 0, "overdue": 0, "unassigned": 0, "byColumn": [], "byModule": []},
        "members": [], "notesPending": 0,
    }
    md = render_markdown(dados)
    assert "_Nenhum membro com cards no projeto._" in md


def test_compute_sem_sessao_de_outro_workspace(tmp_path):
    """compute_weekly não deve depender de estado global de workspace."""
    from maestro_local.db.models import BoardColumn, Project, Task, get_session

    db = str(tmp_path / "x.db")
    init_db(db)
    import maestro_local.db.models as m
    m._engine = None
    m._SessionLocal = None
    m._active_db_path = db
    init_db(db)

    s = get_session()
    p = Project(name="P", key="P")
    s.add(p); s.flush()
    col = BoardColumn(project_id=p.id, name="To do", order=0, is_done=False)
    done = BoardColumn(project_id=p.id, name="Done", order=1, is_done=True)
    s.add_all([col, done]); s.flush()
    s.add(Task(project_id=p.id, column_id=done.id, number=1, title="x",
               assignee="Ana", done_at=datetime.now()))
    s.commit()

    d = compute_weekly(s, p, date.today())
    s.close()
    m._engine = None
    m._SessionLocal = None
    assert d["summary"]["doneInWeek"] == 1
    assert d["members"][0]["name"] == "Ana"


def test_servico_vem_dos_comentarios_de_review(client, projeto):
    """Revisões e PRs saem dos comentários — sem o líder digitar."""
    tid = projeto["ana"]["id"]
    r = client.post("/api/comments", json={
        "taskId": tid, "type": "CODE_REVIEW", "author": "Ana",
        "body": "PR #8910 aprovado; conferi também o #8938.",
    })
    assert r.status_code == 200
    assert r.json()["author"] == "Ana"

    d = client.get(f"/api/projects/{projeto['pid']}/team/weekly").json()
    ana = next(m for m in d["members"] if m["name"] == "Ana")

    assert ana["reviews"] == 1
    assert [c["code"] for c in ana["reviewedCards"]] == [projeto["ana"]["code"]]
    assert set(ana["prs"]) == {"8910", "8938"}
    assert "Revisou 1 card" in ana["serviceSuggested"]
    assert "#8910" in ana["serviceSuggested"]


def test_comentario_sem_autor_continua_local(client, projeto):
    r = client.post("/api/comments", json={
        "taskId": projeto["ana"]["id"], "type": "CODE_REVIEW", "body": "sem autor",
    })
    assert r.json()["author"] == "local"


def test_markdown_usa_servico_do_board_quando_campo_vazio(client, projeto):
    client.post("/api/comments", json={
        "taskId": projeto["ana"]["id"], "type": "CODE_REVIEW", "author": "Ana",
        "body": "PR #8910 aprovado.",
    })
    md = client.get(f"/api/projects/{projeto['pid']}/team/weekly/export").text
    assert "Serviço/apoio (levantado do board)" in md
    assert "#8910" in md
