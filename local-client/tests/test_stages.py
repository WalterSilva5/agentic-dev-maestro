"""Testes de "quem chegou em cada estágio" e do corte por grupo (soma 100%)."""
import pytest
from fastapi.testclient import TestClient

from relay.api.app import app
from relay.db.models import init_db
from relay.stages import compute_stages, pct_split, primary_group, slug


# --------------------------------------------------------------------------
# fakes
# --------------------------------------------------------------------------

class _Col:
    def __init__(self, cid, nome, ordem, done=False):
        self.id, self.name, self.order, self.is_done = cid, nome, ordem, done


class _Label:
    def __init__(self, nome):
        self.name = nome


class _Task:
    def __init__(self, tid, coluna, labels=()):
        self.id, self.column = tid, coluna
        self.labels = [_Label(n) for n in labels]


# Fluxo do time: ... Doing -> Dev Review -> Dev Box -> In Test -> ... -> Done
COLS = [
    _Col(1, "To do", 0),
    _Col(4, "Ready for Dev", 3),
    _Col(5, "Doing", 4),
    _Col(7, "Dev Review", 5),
    _Col(6, "Dev Box", 6),
    _Col(8, "In Test", 7),
    _Col(12, "Done", 11, done=True),
]
TO_DO, RFD, DOING, DEV_REVIEW, DEV_BOX, IN_TEST, DONE = COLS


# --------------------------------------------------------------------------
# "chegou" é cumulativo
# --------------------------------------------------------------------------

def test_quem_esta_em_dev_box_chegou_em_dev_review():
    """Dev Box é o último estado do dev: quem está nele já passou por Dev Review."""
    tasks = [_Task(1, DEV_BOX)]
    d = compute_stages(tasks, COLS)
    por_estagio = {x["stage"]: x for x in d["stages"]}
    assert por_estagio["dev-review"]["reached"] == 1
    assert por_estagio["dev-review"]["current"] == 0
    assert por_estagio["dev-box"]["current"] == 1
    # não "chegou" no que vem depois (teste)
    assert por_estagio["in-test"]["reached"] == 0


def test_quem_esta_em_dev_review_ainda_nao_chegou_em_dev_box():
    tasks = [_Task(1, DEV_REVIEW)]
    d = compute_stages(tasks, COLS)
    por_estagio = {x["stage"]: x for x in d["stages"]}
    assert por_estagio["dev-review"]["reached"] == 1
    assert por_estagio["dev-box"]["reached"] == 0


def test_estagios_posteriores_nao_contam_para_tras():
    tasks = [_Task(1, DOING)]
    d = compute_stages(tasks, COLS)
    por_estagio = {x["stage"]: x for x in d["stages"]}
    assert por_estagio["doing"]["reached"] == 1
    assert por_estagio["dev-box"]["reached"] == 0


def test_voltar_de_coluna_nao_apaga_o_que_ja_foi_alcancado():
    """Task em Doing que já tinha ido para In Test (histórico) conta nos dois."""
    tasks = [_Task(1, DOING)]
    d = compute_stages(tasks, COLS, history_rows=[(1, "In Test -> Doing")])
    por_estagio = {x["stage"]: x for x in d["stages"]}
    assert por_estagio["in-test"]["reached"] == 1
    assert por_estagio["in-test"]["current"] == 0
    assert por_estagio["doing"]["current"] == 1


def test_pct_do_estagio_e_sobre_o_board():
    tasks = [_Task(1, DEV_BOX), _Task(2, DEV_BOX), _Task(3, TO_DO), _Task(4, TO_DO)]
    d = compute_stages(tasks, COLS)
    por_estagio = {x["stage"]: x for x in d["stages"]}
    assert por_estagio["dev-box"]["reached"] == 2
    assert por_estagio["dev-box"]["pct"] == 50
    assert por_estagio["to-do"]["pct"] == 100


def test_fluxo_completo_nao_aumenta_a_contagem():
    """Quem fez o caminho inteiro conta 1 vez em cada estágio, não soma."""
    tasks = [_Task(1, DONE), _Task(2, DEV_BOX)]
    d = compute_stages(tasks, COLS)
    por_estagio = {x["stage"]: x for x in d["stages"]}
    assert por_estagio["done"]["reached"] == 1
    assert por_estagio["dev-box"]["reached"] == 2
    assert d["total"] == 2


# --------------------------------------------------------------------------
# corte por grupo: soma sempre 100%
# --------------------------------------------------------------------------

def test_pct_split_soma_100():
    assert sum(pct_split([1, 1, 1])) == 100
    assert pct_split([1, 1, 1]) == [34, 33, 33]
    assert sum(pct_split([58, 25, 14, 13, 5, 1, 1])) == 100
    assert sum(pct_split([1, 0, 0])) == 100
    assert pct_split([0, 0]) == [0, 0]


def test_breakdown_do_estagio_soma_100():
    tasks = [
        _Task(1, DEV_BOX, ["config"]),
        _Task(2, DEV_BOX, ["cfg-e2"]),        # só sub-entrega -> config
        _Task(3, DEV_BOX, ["cashier"]),
        _Task(4, DEV_BOX, ["vm", "fundacao"]),  # sem módulo
        _Task(5, TO_DO),                     # não chegou em dev box
    ]
    d = compute_stages(tasks, COLS)
    grupos = d["breakdown"]["dev-box"]
    assert sum(g["total"] for g in grupos) == 4
    assert sum(g["pct"] for g in grupos) == 100
    por_grupo = {g["group"]: g for g in grupos}
    assert por_grupo["config"]["total"] == 2
    assert por_grupo["cashier"]["total"] == 1
    assert por_grupo["sem-modulo"]["total"] == 1


def test_cada_card_entra_em_um_grupo_so():
    """Card com dois módulos não é contado duas vezes (senão não fecha 100%)."""
    tasks = [_Task(1, DEV_BOX, ["cashier", "config"])]
    d = compute_stages(tasks, COLS)
    grupos = d["breakdown"]["dev-box"]
    assert sum(g["total"] for g in grupos) == 1
    assert grupos[0]["group"] == "config"  # primeiro na ordem do plano


def test_primary_group():
    assert primary_group(["cfg-e3"]) == "config"
    assert primary_group(["vm", "fundacao"]) == "sem-modulo"
    assert primary_group(["cashier", "config"]) == "config"
    assert primary_group([]) == "sem-modulo"


def test_slug_do_estagio():
    assert slug("Dev Box") == "dev-box"
    assert slug("In Test") == "in-test"
    assert slug("Ready for Dev") == "ready-for-dev"


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

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


def test_api_stages_e_recorte_do_estagio(client):
    pid = client.post("/api/projects", json={"name": "Fluxo", "key": "FLX"}).json()["id"]
    # template com as colunas do fluxo de desenvolvimento (to do -> done)
    assert client.post(f"/api/projects/{pid}/columns/template").status_code == 200
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}

    # duas tasks: uma em Dev Box, uma em To do
    client.post("/api/tasks", json={"projectId": pid, "columnId": cols["Dev Box"], "title": "a"})
    client.post("/api/tasks", json={"projectId": pid, "columnId": cols["To do"], "title": "b"})

    r = client.get(f"/api/projects/{pid}/metrics/stages")
    assert r.status_code == 200
    d = r.json()
    estagios = {x["stage"]: x for x in d["stages"]}
    assert estagios["dev-box"]["reached"] == 1
    assert estagios["to-do"]["reached"] == 2
    assert estagios["done"]["reached"] == 0
    # a soma dos grupos do estágio fecha em 100%
    assert sum(g["pct"] for g in d["breakdown"]["dev-box"]) == 100

    r2 = client.get(f"/api/projects/{pid}/metrics/stages", params={"stage": "dev-box"})
    assert r2.status_code == 200
    sel = r2.json()["selected"]
    assert sel["stage"] == "dev-box"
    assert sel["reached"] == 1
    assert sum(g["pct"] for g in sel["groups"]) == 100

    assert client.get(
        f"/api/projects/{pid}/metrics/stages", params={"stage": "nao-existe"}
    ).status_code == 404
