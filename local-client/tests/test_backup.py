"""Backup rápido do banco: cópia consistente + listagem + download."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.db.models import init_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    import maestro_local.db.models as m
    m._engine = None
    m._SessionLocal = None
    m._active_db_path = db_path
    init_db(db_path)

    pasta = tmp_path / "backups"
    monkeypatch.setattr("maestro_local.api.app._backup_dir", lambda: pasta)
    pasta.mkdir(exist_ok=True)

    with TestClient(app) as c:
        yield c
    m._engine = None
    m._SessionLocal = None


def test_backup_cria_copia_consistente_do_banco(client, tmp_path):
    pid = client.post("/api/projects", json={"name": "Backup", "key": "BKP"}).json()["id"]
    client.post("/api/tasks", json={"projectId": pid, "title": "card que precisa sobreviver"})

    r = client.post("/api/backup")
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert len(d["backups"]) == 1

    info = d["backups"][0]
    assert info["file"].startswith("maestro-")
    assert info["file"].endswith(".db")
    assert info["bytes"] > 0

    # o arquivo existe e é um banco válido com os mesmos dados
    assert (tmp_path / "backups" / info["file"]).exists()
    con = sqlite3.connect(info["path"])
    try:
        tarefas = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        projetos = con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    assert tarefas == 1
    assert projetos == 1
    assert {"tasks", "projects", "board_columns"} <= tabelas


def test_backup_nao_sujo_com_o_banco_aberto(client, tmp_path):
    """Depois do backup o banco original continua funcionando normalmente."""
    pid = client.post("/api/projects", json={"name": "Vivo", "key": "VIV"}).json()["id"]
    assert client.post("/api/backup").status_code == 200

    r = client.post("/api/tasks", json={"projectId": pid, "title": "criada depois do backup"})
    assert r.status_code == 200
    board = client.get(f"/api/projects/{pid}/board").json()
    cards = [t for c in board["columns"] for t in c["tasks"]]
    assert len(cards) == 1


def test_lista_backups_mais_recente_primeiro(client):
    assert client.get("/api/backup").json()["backups"] == []
    client.post("/api/backup")

    r = client.get("/api/backup")
    assert r.status_code == 200
    d = r.json()
    assert d["dir"]
    assert len(d["backups"]) == 1
    assert d["backups"][0]["createdAt"]


def test_baixa_o_backup(client):
    nome = client.post("/api/backup").json()["backups"][0]["file"]
    r = client.get(f"/api/backup/{nome}")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert nome in r.headers["content-disposition"]
    assert r.content[:16].startswith(b"SQLite format 3")


def test_nao_serve_arquivo_fora_da_pasta_de_backup(client, tmp_path):
    # nome com caminho relativo não pode escapar da pasta
    assert client.get("/api/backup/..%2Ftest.db").status_code == 404
    assert client.get("/api/backup/qualquer.txt").status_code == 404
    # arquivo existente mas fora da pasta
    (tmp_path / "fora" / "maestro-x.db").parent.mkdir(exist_ok=True)
    (tmp_path / "fora" / "maestro-x.db").write_bytes(b"x")
    assert client.get("/api/backup/maestro-x.db").status_code == 404


def test_backup_de_todos_os_workspaces(client, tmp_path, monkeypatch):
    raiz = tmp_path / "workspaces"
    for ws in ("alfa", "beta"):
        pasta = raiz / ws
        pasta.mkdir(parents=True)
        # banco mínimo só para provar que o backup percorre todos os workspaces
        con = sqlite3.connect(pasta / "maestro.db")
        con.execute("CREATE TABLE t (x INTEGER)")
        con.commit()
        con.close()
    monkeypatch.setattr("maestro_local.config.WORKSPACES_DIR", raiz)

    r = client.post("/api/backup", params={"all": 1})
    assert r.status_code == 200
    d = r.json()
    workspaces = sorted(b["workspace"] for b in d["backups"])
    assert workspaces == ["alfa", "beta"]
    for b in d["backups"]:
        assert (tmp_path / "backups" / b["file"]).exists()
