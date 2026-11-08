"""Tarefas locais: existem só aqui e o sync do board externo as ignora."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.db.models import init_db

RAIZ = Path(__file__).resolve().parents[1]


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


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def test_cria_tarefa_local_e_marca_no_card(client):
    pid = client.post("/api/projects", json={"name": "Local", "key": "LOC"}).json()["id"]

    r = client.post("/api/tasks", json={
        "projectId": pid,
        "title": "revisar o que o dev fez hoje",
        "isLocal": True,
    })
    assert r.status_code == 200
    task = r.json()
    assert task["isLocal"] is True

    board = client.get(f"/api/projects/{pid}/board").json()
    cards = [t for c in board["columns"] for t in c["tasks"]]
    assert len(cards) == 1
    assert cards[0]["isLocal"] is True


def test_tarefa_padrao_e_remota(client):
    pid = client.post("/api/projects", json={"name": "Remoto", "key": "REM"}).json()["id"]
    task = client.post("/api/tasks", json={"projectId": pid, "title": "do board"}).json()
    assert task["isLocal"] is False


def test_alterna_local_remoto_no_update(client):
    pid = client.post("/api/projects", json={"name": "Alt", "key": "ALT"}).json()["id"]
    task = client.post("/api/tasks", json={"projectId": pid, "title": "x"}).json()

    r = client.patch(f"/api/tasks/{task['code']}", json={"isLocal": True})
    assert r.status_code == 200
    assert r.json()["isLocal"] is True

    r = client.patch(f"/api/tasks/{task['code']}", json={"isLocal": False})
    assert r.json()["isLocal"] is False


def test_tarefa_local_nao_entra_na_contagem_remota_do_sync(client):
    """O corte é por flag, não pelo número: local e remota convivem no board."""
    pid = client.post("/api/projects", json={"name": "Misto", "key": "MIS"}).json()["id"]
    local = client.post("/api/tasks", json={
        "projectId": pid, "title": "lembrete local", "isLocal": True}).json()
    remota = client.post("/api/tasks", json={
        "projectId": pid, "title": "veio do board"}).json()

    board = client.get(f"/api/projects/{pid}/board").json()
    cards = {t["id"]: t for c in board["columns"] for t in c["tasks"]}
    assert cards[local["id"]]["isLocal"] is True
    assert cards[remota["id"]]["isLocal"] is False


# --------------------------------------------------------------------------
# sync real (subprocess com MAESTRO_DATA_DIR isolado)
# --------------------------------------------------------------------------

def _azure_item(wid: int, titulo: str) -> dict:
    return {
        "id": wid,
        "fields": {
            "System.Title": titulo,
            "System.State": "To do",
            "System.Tags": "",
        },
    }


def _rodar_sync(data_dir: Path, itens: list[dict], projeto: str = "P") -> subprocess.CompletedProcess:
    entrada = data_dir / f"azure-{len(itens)}.json"
    entrada.write_text(json.dumps(itens))
    env = {
        **os.environ,
        "MAESTRO_DATA_DIR": str(data_dir),
        "PYTHONPATH": str(RAIZ),
        "QT_QPA_PLATFORM": "offscreen",
    }
    python = RAIZ / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)
    return subprocess.run(
        [str(python), str(RAIZ / "scripts" / "sync_azure_to_local.py"),
         "--project", projeto, "--local-project-key", "PRJ", "--input", str(entrada)],
        cwd=str(RAIZ), env=env, capture_output=True, text=True, timeout=120,
    )


def test_sync_ignora_tarefa_local_com_mesmo_numero(tmp_path):
    data_dir = tmp_path / "maestro-data"
    data_dir.mkdir()

    # 1) sync inicial cria a remota 101
    r1 = _rodar_sync(data_dir, [_azure_item(101, "Remota 101")])
    assert r1.returncode == 0, r1.stderr

    db = data_dir / "workspaces" / "default" / "maestro.db"
    assert db.exists()
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO tasks (project_id, column_id, number, title, type, priority, is_local, created_at, updated_at)"
        " SELECT id, (SELECT id FROM board_columns WHERE project_id=projects.id ORDER BY \"order\" LIMIT 1),"
        "        999, 'revisar o que o dev fez hoje', 'CHORE', 'MEDIUM', 1, datetime('now'), datetime('now')"
        " FROM projects WHERE key='PRJ' LIMIT 1"
    )
    con.commit()
    con.close()

    # 2) o Azure traz um item com o MESMO número 999 -> não pode sobrescrever a local
    r2 = _rodar_sync(data_dir, [_azure_item(101, "Remota 101 editada"),
                                _azure_item(999, "Do board, mesmo número")])
    assert r2.returncode == 0, r2.stderr
    assert "ignorado #999" in r2.stdout
    assert "Tarefas locais preservadas" in r2.stdout

    con = sqlite3.connect(db)
    linhas = con.execute(
        "SELECT number, title, is_local FROM tasks WHERE number IN (999, 101) ORDER BY number"
    ).fetchall()
    con.close()

    # 999 continua sendo a local, intacta; 101 foi atualizada normalmente
    assert linhas == [
        (101, "Remota 101 editada", 0),
        (999, "revisar o que o dev fez hoje", 1),
    ]


def test_sync_cria_so_as_remotas_e_preserva_as_locais(tmp_path):
    data_dir = tmp_path / "maestro-data"
    data_dir.mkdir()
    assert _rodar_sync(data_dir, [_azure_item(1, "Remota 1")]).returncode == 0

    db = data_dir / "workspaces" / "default" / "maestro.db"
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO tasks (project_id, column_id, number, title, type, priority, is_local, created_at, updated_at)"
        " SELECT id, (SELECT id FROM board_columns WHERE project_id=projects.id ORDER BY \"order\" LIMIT 1),"
        "        5000, 'anotação local', 'CHORE', 'MEDIUM', 1, datetime('now'), datetime('now')"
        " FROM projects WHERE key='PRJ' LIMIT 1"
    )
    con.commit()
    con.close()

    assert _rodar_sync(data_dir, [_azure_item(1, "Remota 1"), _azure_item(2, "Remota 2")]).returncode == 0

    con = sqlite3.connect(db)
    total = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    local = con.execute("SELECT COUNT(*) FROM tasks WHERE is_local=1").fetchone()[0]
    remotas = con.execute("SELECT COUNT(*) FROM tasks WHERE is_local=0").fetchone()[0]
    con.close()
    assert (total, local, remotas) == (3, 1, 2)


# --------------------------------------------------------------------------
# tarefa local não entra em métrica nenhuma
# --------------------------------------------------------------------------

class _Col:
    def __init__(self, cid, nome, ordem, done=False):
        self.id, self.name, self.order, self.is_done = cid, nome, ordem, done


class _Label:
    def __init__(self, nome):
        self.name = nome


class _Task:
    def __init__(self, tid, coluna, labels=(), local=False):
        self.id, self.column = tid, coluna
        self.column_id = coluna.id
        self.labels = [_Label(n) for n in labels]
        self.is_local = local


def test_dimensoes_ignoram_tarefas_locais():
    from maestro_local.dimensions import aggregate_dimensions

    remota = _Col(1, "To do", 0)
    feito = _Col(2, "Done", 1, done=True)
    tasks = [
        _Task(1, remota, ["config"]),
        _Task(2, feito, ["config"]),
        _Task(3, remota, ["config"], local=True),   # não conta
    ]
    d = aggregate_dimensions(tasks, {feito.id})
    assert d["cards"] == 2          # só as remotas
    assert d["local"] == 1
    config = next(m for m in d["modules"] if m["name"] == "config")
    assert config["total"] == 2
    assert config["done"] == 1
    assert d["unlabeled"]["total"] == 0


def test_estagios_ignoram_tarefas_locais():
    from maestro_local.stages import compute_stages

    col = _Col(6, "Dev Box", 5)
    tasks = [
        _Task(1, col),
        _Task(2, col, local=True),
    ]
    d = compute_stages(tasks, [col])
    assert d["total"] == 1
    assert d["local"] == 1
    assert d["stages"][0]["reached"] == 1
    assert sum(g["total"] for g in d["breakdown"]["dev-box"]) == 1


def test_api_metricas_ignoram_tarefas_locais(client):
    pid = client.post("/api/projects", json={"name": "Met", "key": "MET"}).json()["id"]
    client.post(f"/api/projects/{pid}/columns/template")
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}

    client.post("/api/tasks", json={"projectId": pid, "columnId": cols["Done"], "title": "remota ok"})
    client.post("/api/tasks", json={
        "projectId": pid, "columnId": cols["To do"], "title": "lembrete", "isLocal": True})

    dims = client.get(f"/api/projects/{pid}/metrics/dimensions").json()
    assert dims["cards"] == 1
    assert dims["local"] == 1

    stages = client.get(f"/api/projects/{pid}/metrics/stages").json()
    assert stages["total"] == 1
    assert stages["local"] == 1
    done = next(x for x in stages["stages"] if x["stage"] == "done")
    assert done["reached"] == 1        # só a remota
    to_do = next(x for x in stages["stages"] if x["stage"] == "to-do")
    assert to_do["reached"] == 1       # a local não conta nem em "To do"


def test_pdf_ignora_tarefas_locais(tmp_path):
    from maestro_local.metrics_pdf import collect_metrics

    import maestro_local.db.models as m
    from maestro_local.db.models import BoardColumn, Project, Task, get_session

    db = str(tmp_path / "pdf.db")
    init_db(db)
    m._engine = None
    m._SessionLocal = None
    m._active_db_path = db
    init_db(db)

    s = get_session()
    p = Project(name="PDF", key="PDF")
    s.add(p); s.flush()
    col = BoardColumn(project_id=p.id, name="To do", order=0, is_done=False)
    s.add(col); s.flush()
    s.add(Task(project_id=p.id, column_id=col.id, number=1, title="remota"))
    s.add(Task(project_id=p.id, column_id=col.id, number=2, title="local", is_local=True))
    s.commit()

    dados = collect_metrics(s, p)
    s.close()
    assert dados["total"] == 1
    assert dados["local"] == 1
    m._engine = None
    m._SessionLocal = None
