"""Ordem das colunas do fluxo: Dev Review antes de Dev Box.

`Doing → Dev Review → Dev Box → In Test → … → Done` — Dev Box é o último
estado do desenvolvimento (aguardando teste), não o primeiro depois do Doing.
"""
import pytest
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.db.models import BoardColumn, Project, init_db, get_session


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


def test_template_tem_dev_review_antes_de_dev_box(client):
    pid = client.post("/api/projects", json={"name": "Fluxo", "key": "FLX"}).json()["id"]
    assert client.post(f"/api/projects/{pid}/columns/template").status_code == 200
    cols = client.get(f"/api/projects/{pid}/columns").json()
    nomes = [c["name"] for c in cols]

    assert nomes.index("Doing") < nomes.index("Dev Review") < nomes.index("Dev Box")
    assert nomes.index("Dev Box") < nomes.index("In Test") < nomes.index("Done")
    # Dev Box é o último estado do dev: nada de dev depois dele
    assert "Dev Review" not in nomes[nomes.index("Dev Box"):]
    # e só Done é coluna de conclusão
    assert [c["name"] for c in cols if c["isDone"]] == ["Done"]


def test_migracao_corrige_banco_com_ordem_antiga(tmp_path):
    db = str(tmp_path / "antigo.db")
    init_db(db)

    import maestro_local.db.models as m
    m._engine = None
    m._SessionLocal = None
    m._active_db_path = db
    init_db(db)

    s = get_session()
    p = Project(name="Antigo", key="OLD")
    s.add(p)
    s.flush()
    # ordem errada: Dev Box antes de Dev Review
    s.add(BoardColumn(project_id=p.id, name="Doing", order=4))
    s.add(BoardColumn(project_id=p.id, name="Dev Box", order=5))
    s.add(BoardColumn(project_id=p.id, name="Dev Review", order=6))
    s.add(BoardColumn(project_id=p.id, name="In Test", order=7))
    s.commit()
    projeto_id = p.id
    s.close()

    # reabrir o banco dispara a migração
    m._engine = None
    m._SessionLocal = None
    init_db(db)

    s = get_session()
    ordem = {
        c.name: c.order
        for c in s.query(BoardColumn)
        .filter(BoardColumn.project_id == projeto_id)
        .all()
    }
    s.close()
    m._engine = None
    m._SessionLocal = None

    assert ordem["Dev Review"] == 5
    assert ordem["Dev Box"] == 6
    assert ordem["Doing"] == 4 and ordem["In Test"] == 7


def test_migracao_e_idempotente(tmp_path):
    db = str(tmp_path / "idem.db")
    import maestro_local.db.models as m
    m._engine = None
    m._SessionLocal = None
    m._active_db_path = db
    init_db(db)

    s = get_session()
    p = Project(name="Ok", key="OK")
    s.add(p)
    s.flush()
    s.add(BoardColumn(project_id=p.id, name="Dev Review", order=5))
    s.add(BoardColumn(project_id=p.id, name="Dev Box", order=6))
    s.commit()
    pid = p.id
    s.close()

    for _ in range(3):  # reabrir várias vezes não mexe mais
        m._engine = None
        m._SessionLocal = None
        init_db(db)
        s = get_session()
        ordem = {c.name: c.order for c in s.query(BoardColumn).filter(
            BoardColumn.project_id == pid).all()}
        s.close()
        assert ordem == {"Dev Review": 5, "Dev Box": 6}
    m._engine = None
    m._SessionLocal = None
