"""Testes da classificação de dimensões (módulo × submódulo × sprint × tag)."""
import pytest
from fastapi.testclient import TestClient

from maestro_local.api.app import app
from maestro_local.db.models import init_db
from maestro_local.dimensions import aggregate_dimensions, classify_label


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
# classificação
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label,kind,module,rotulo", [
    ("cashier", "MODULE", "cashier", "cashier"),
    ("config", "MODULE", "config", "config"),
    ("venda", "MODULE", "venda", "venda"),
    # sub-entregas usam os nomes do plano oficial (10-progresso-entrega.svg)
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
    # o plano completo aparece (17 modulos), mesmo sem card
    assert len(modulos) == 17
    assert {"config", "cashier", "tef", "crm"} <= set(modulos)
    # modulo sem nenhum card aparece zerado, com os endpoints do plano
    assert modulos["tef"]["total"] == 0
    assert modulos["tef"]["endpoints"] == 5

    assert modulos["config"]["total"] == 2
    assert modulos["config"]["done"] == 1
    assert modulos["config"]["endpoints"] == 26
    # sub-entregas do plano, em ordem, com nome oficial e endpoints
    subs_cfg = [(s["name"], s["label"], s["endpoints"]) for s in modulos["config"]["submodules"]]
    assert subs_cfg[:2] == [("cfg-e1", "E1 · loja", 4), ("cfg-e2", "E2 · monitor e estação", 5)]
    assert len(subs_cfg) == 4

    assert modulos["cashier"]["total"] == 2
    assert [s["label"] for s in modulos["cashier"]["submodules"]] == [
        "O1 · abrir e carregar", "O2 · movimentar", "O3 · fechar e acertar"
    ]

    # dimensões separadas
    assert d["sprints"] == [{"name": "sprint-1", "label": "Sprint 1",
                             "total": 1, "done": 0, "pct": 0}]
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
    # mas o plano tem sempre os 17 módulos
    assert d["plan"]["modules"] == 17
    assert d["plan"]["endpoints"] == 156


def test_plano_oficial_de_modulos_e_subentregas():
    """Nomes/ordem/endpoints vêm do 10-progresso-entrega.svg."""
    from maestro_local.module_plan import (
        MODULE_PLAN,
        PLAN_ORDER,
        TOTAL_ENDPOINTS,
        delivery_endpoints,
        delivery_label,
        module_of_delivery,
    )

    assert len(MODULE_PLAN) == 17
    assert TOTAL_ENDPOINTS == 156
    assert PLAN_ORDER[0] == "auth" and PLAN_ORDER[-1] == "crm"
    assert delivery_label("cfg-e3") == "E3 · parâmetros e utilitários"
    assert delivery_endpoints("cfg-e3") == 15
    assert module_of_delivery("cfg-e3") == "config"
    assert delivery_endpoints("onda-2") == 11

    # 5 módulos com sub-entregas: config, cashier, financeiro, troca, venda
    com_subs = {n for n, m in MODULE_PLAN.items() if m["deliveries"]}
    assert com_subs == {"config", "cashier", "financeiro", "troca", "venda"}


def test_descontinuados_ficam_fora_do_plano_mas_sao_visiveis():
    tasks = [_T(1, ["nfce"])]
    d = aggregate_dimensions(tasks, done_ids=set())
    assert [x["name"] for x in d["discontinued"]] == ["nfce"]
    # nao entram na lista de modulos do plano
    assert "nfce" not in {m["name"] for m in d["modules"]}


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
