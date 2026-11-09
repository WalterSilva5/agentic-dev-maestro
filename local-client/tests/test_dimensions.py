"""Testes da classificação de dimensões (módulo × submódulo × sprint × tag)."""
import pytest
from fastapi.testclient import TestClient

from relay.api.app import app
from relay.db.models import init_db
from relay.dimensions import aggregate_dimensions, classify_label


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


# --------------------------------------------------------------------------
# classificação
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label,kind,module,rotulo", [
    ("cashier", "MODULE", "cashier", "cashier"),
    ("config", "MODULE", "config", "config"),
    ("venda", "MODULE", "venda", "venda"),
    # sub-entregas usam os nomes da taxonomia de rótulos
    ("cfg-e1", "SUBMODULE", "config", "E1 · loja"),
    ("fin-e2", "SUBMODULE", "financeiro", "E2 · adesão e termos"),
    ("tro-e4", "SUBMODULE", "troca", "E4 · fechamento"),
    ("ven-e3", "SUBMODULE", "venda", "E3 · fechamento e TEF"),
    ("onda-1", "SUBMODULE", "cashier", "O1 · abrir e carregar"),
    ("onda-3", "SUBMODULE", "cashier", "O3 · fechar e acertar"),
    ("sprint-4", "SPRINT", None, "Sprint 4"),
    ("vm", "PLATFORM", None, "vm"),
    ("var3-app", "PLATFORM", None, "var3-app"),
    ("fundacao", "PROCESS", None, "Fundação"),
    ("despriorizado", "PROCESS", None, "Despriorizado"),
    ("bug", "PROCESS", None, "Bug"),
    ("etiqueta-livre", "OTHER", None, "etiqueta-livre"),
])
def test_classifica_labels(label, kind, module, rotulo):
    info = classify_label(label)
    assert info["kind"] == kind
    assert info["module"] == module
    assert info["label"] == rotulo


def test_sprint_nao_eh_modulo():
    assert classify_label("sprint-1")["kind"] != "MODULE"
    assert classify_label("vm")["kind"] != "MODULE"
    assert classify_label("fundacao")["kind"] != "MODULE"


# --------------------------------------------------------------------------
# agregação
# --------------------------------------------------------------------------

class _T:
    """Task fake para testar a agregação sem banco."""

    def __init__(self, tid, labels, column_id=1):
        self.id = tid
        self.column_id = column_id

        class _L:
            def __init__(self, name):
                self.name = name

        self.labels = [_L(n) for n in labels]


def test_agrega_modulo_com_submodulos_e_ondas():
    tasks = [
        _T(1, ["config", "cfg-e1"], column_id=9),   # concluída
        _T(2, ["cfg-e2"], column_id=2),             # só submódulo -> conta no módulo
        _T(3, ["cashier", "onda-1"], column_id=2),
        _T(4, ["onda-2"], column_id=2),
        _T(5, ["sprint-1"], column_id=2),           # sprint não é módulo
        _T(6, ["vm", "fundacao"], column_id=2),     # plataforma/natureza não são módulo
    ]
    d = aggregate_dimensions(tasks, done_ids={9})

    modulos = {m["name"]: m for m in d["modules"]}
    # só aparecem grupos com cards — sem metas nem grupos zerados
    assert set(modulos) == {"config", "cashier"}

    assert modulos["config"]["total"] == 2
    assert modulos["config"]["done"] == 1
    # só as sub-entregas observadas, em ordem, com nome da taxonomia
    subs_cfg = [(s["name"], s["label"]) for s in modulos["config"]["submodules"]]
    assert subs_cfg == [("cfg-e1", "E1 · loja"), ("cfg-e2", "E2 · monitor e estação")]

    assert modulos["cashier"]["total"] == 2
    assert [s["label"] for s in modulos["cashier"]["submodules"]] == [
        "O1 · abrir e carregar", "O2 · movimentar"
    ]

    # dimensões separadas
    assert [(x["name"], x["label"], x["total"], x["done"], x["pct"]) for x in d["sprints"]] == [
        ("sprint-1", "Sprint 1", 1, 0, 0)
    ]
    assert [p["name"] for p in d["platforms"]] == ["vm"]
    assert [p["name"] for p in d["process"]] == ["fundacao"]

    # sem módulo: cards 5 e 6
    assert d["with_module"] == 4
    assert d["unlabeled"]["total"] == 2


def test_soma_de_modulos_pode_exceder_cards():
    """Card com dois módulos conta nos dois (por isso a nota no PDF)."""
    tasks = [_T(1, ["config", "cashier"])]
    d = aggregate_dimensions(tasks, done_ids=set())
    assert d["with_module"] == 1
    assert sum(m["total"] for m in d["modules"]) == 2
    # sem metas planejadas: só os grupos observados
    assert {m["name"] for m in d["modules"]} == {"config", "cashier"}
    assert "plan" not in d


def test_taxonomia_de_modulos_e_subentregas():
    """Nomes/ordem vêm da taxonomia de rótulos (sem metas nem endpoints)."""
    from relay.module_plan import (
        MODULE_PLAN,
        PLAN_ORDER,
        delivery_label,
    )

    assert PLAN_ORDER[0] == "auth"
    assert delivery_label("cfg-e3") == "E3 · parâmetros e utilitários"
    assert delivery_label("onda-2") == "O2 · movimentar"

    # 5 módulos com sub-entregas: config, cashier, financeiro, troca, venda
    com_subs = {n for n, m in MODULE_PLAN.items() if m["deliveries"]}
    assert com_subs == {"config", "cashier", "financeiro", "troca", "venda"}


def test_modulo_qualquer_conta_como_modulo():
    tasks = [_T(1, ["nfce"])]
    d = aggregate_dimensions(tasks, done_ids=set())
    assert [x["name"] for x in d["modules"]] == ["nfce"]
    assert "discontinued" not in d


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def test_api_dimensions_separa_dimensoes(client):
    pid = client.post("/api/projects", json={"name": "Dim", "key": "DIM"}).json()["id"]
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}

    def tarefa(col, title, labels):
        r = client.post("/api/tasks", json={"projectId": pid, "columnId": col, "title": title})
        tid = r.json()["id"]
        for nome in labels:
            client.post("/api/labels", json={"name": nome})
        # associa labels via PATCH não existe; usa o endpoint de labels da task
        return tid

    # cria labels e tarefas
    tarefa(cols["A fazer"], "config e1", ["config", "cfg-e1", "sprint-1", "vm"])
    tarefa(cols["Feito"], "config e2", ["cfg-e2", "sprint-1"])
    tarefa(cols["A fazer"], "cashier onda", ["cashier", "onda-1", "fundacao"])

    r = client.get(f"/api/projects/{pid}/metrics/dimensions")
    assert r.status_code == 200
    d = r.json()
    assert d["projectId"] == pid
    assert d["cards"] == 3
    assert "modules" in d and "sprints" in d and "platforms" in d and "process" in d
    # nenhum módulo aparece com nome de sprint/tag
    nomes_modulo = {m["name"] for m in d["modules"]}
    assert not ({"sprint-1", "vm", "fundacao"} & nomes_modulo)


def test_api_dimensions_404(client):
    assert client.get("/api/projects/9999/metrics/dimensions").status_code == 404


# --------------------------------------------------------------------------
# desenvolvimento concluído (Dev Box ou depois) x aceite (Done)
# --------------------------------------------------------------------------

class _Col:
    def __init__(self, cid, nome, ordem, done=False):
        self.id, self.name, self.order, self.is_done = cid, nome, ordem, done


class _T2:
    """Task fake mínima para os testes de desenvolvimento/aceite."""

    def __init__(self, tid, coluna_id, labels=("config",)):
        class _L:
            def __init__(self, nome):
                self.name = nome

        self.id = tid
        self.column_id = coluna_id
        self.labels = [_L(n) for n in labels]
        self.is_local = False


def _tarefa(tid, coluna_id, labels=("config",)):
    return _T2(tid, coluna_id, labels)


COLS_FLUXO = [
    _Col(1, "To do", 0),
    _Col(2, "Dev Review", 5),
    _Col(3, "Dev Box", 6),
    _Col(4, "In Test", 7),
    _Col(5, "Done", 8, done=True),
]


def test_dev_box_conta_como_desenvolvimento_concluido():
    """Card em Dev Box já é dev concluído; não precisa estar em Done."""
    tasks = [
        _tarefa(1, 3),   # Dev Box
        _tarefa(2, 5),   # Done
        _tarefa(3, 2),   # Dev Review (antes do Dev Box)
    ]
    d = aggregate_dimensions(tasks, done_ids={5}, columns=COLS_FLUXO)
    config = next(m for m in d["modules"] if m["name"] == "config")

    assert d["developmentColumn"] == "Dev Box"
    assert config["total"] == 3
    assert config["developed"] == 2       # Dev Box + Done
    assert config["developedPct"] == 67
    assert config["done"] == 1            # só o aceito
    assert config["pct"] == 33


def test_sem_dev_box_cai_na_coluna_de_conclusao():
    cols = [_Col(1, "To do", 0), _Col(2, "Feito", 1, done=True)]
    tasks = [_tarefa(1, 2), _tarefa(2, 1)]
    d = aggregate_dimensions(tasks, done_ids={2}, columns=cols)
    config = next(m for m in d["modules"] if m["name"] == "config")
    assert d["developmentColumn"] is None
    assert config["developed"] == 1
    assert config["developedPct"] == config["pct"] == 50
