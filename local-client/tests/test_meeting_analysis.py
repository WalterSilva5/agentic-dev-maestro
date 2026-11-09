"""Análise de reunião com contexto: heurística, mescla e API."""
import json
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from relay.api.app import app
from relay.db.models import init_db
from relay.meeting_analysis import analyze_meeting, merge_live_state

CONTEXTO = """## Projeto — MIG · Migração
- Board: 200 cards · 55 concluídos (28%) · 145 em aberto · 66 sem responsável

### Em andamento (mais parados primeiro)
- MIG-13720 · Cache das feature flags — Dev Box · Walter · parado há 6d
- MIG-13681 · Validar mapeamento — Doing · Walter

### Atrasados
- MIG-14096 · bug GX #4 — venceu 05/11 · Jeferson

### Progresso por módulo
- auth 4/13 (31%) · financeiro 0/20 (0%)

### Registros recentes (daily do projeto)
- 2026-11-04 · WORK · cashier — Fechamos a onda 1 do cashier.
"""


# --------------------------------------------------------------------------
# heurística (sem IA)
# --------------------------------------------------------------------------

def test_heuristica_aponta_card_parado_e_atraso():
    d = analyze_meeting(transcript="falamos do cashier", context=CONTEXTO, use_ai=False)
    assert d["engine"] == "heuristic"
    texto = " ".join(d["tips"])
    assert "MIG-13720" in texto and "6 dia" in texto
    assert "MIG-14096" in texto and "venceu em 05/11" in texto
    assert "financeiro (0/20)" in texto
    assert "daily" in texto.lower()
    # não inventa ação sem base
    assert d["actionItems"] == []
    assert d["plan"]


def test_heuristica_sem_contexto_nao_quebra():
    d = analyze_meeting(transcript="reunião rápida", context="", use_ai=False)
    assert d["engine"] == "heuristic"
    assert d["tips"] == []
    assert d["plan"]


def test_analise_usa_ia_quando_disponivel(monkeypatch):
    def falso(titulo, transcricao, contexto):
        return {"tips": ["dica da IA"], "plan": ["passo"], "actionItems": [],
                "decisions": ["decidido"], "questions": []}

    monkeypatch.setattr("relay.meeting_analysis._via_llm", falso)
    d = analyze_meeting(transcript="x", context=CONTEXTO, use_ai=True)
    assert d["engine"] == "llm"
    assert d["tips"] == ["dica da IA"]


def test_ia_falhando_cai_na_heuristica(monkeypatch):
    def explode(*a, **k):
        raise RuntimeError("sem provedor")

    monkeypatch.setattr("relay.meeting_analysis._via_llm", explode)
    d = analyze_meeting(transcript="x", context=CONTEXTO, use_ai=True)
    assert d["engine"] == "heuristic"
    assert any("MIG-13720" in t for t in d["tips"])


# --------------------------------------------------------------------------
# mescla
# --------------------------------------------------------------------------

def test_merge_nao_duplica():
    estado = {"tips": ["já existia"], "plan": [], "action_items": [], "decisions": [], "questions": []}
    analise = {"tips": ["já existia", "nova"], "plan": ["p1"],
               "actionItems": [{"description": "revisar PR", "assignee": "Ana"}],
               "decisions": ["d1"], "questions": [{"question": "q1"}]}

    novo = merge_live_state(estado, analise)
    assert novo["tips"] == ["já existia", "nova"]
    assert novo["plan"] == ["p1"]
    assert novo["action_items"] == [{"description": "revisar PR", "assignee": "Ana"}]
    assert novo["questions"][0]["question"] == "q1"

    # mesclar de novo não muda nada
    repetido = merge_live_state(novo, analise)
    assert repetido == novo


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


@pytest.fixture
def dados(client):
    pid = client.post("/api/projects", json={"name": "Migração", "key": "MIG"}).json()["id"]
    client.post(f"/api/projects/{pid}/columns/template")
    cols = {c["name"]: c["id"] for c in client.get(f"/api/projects/{pid}/columns").json()}
    from relay.db.models import ProjectDailyEntry, Task, get_session

    s = get_session()
    s.add(Task(project_id=pid, column_id=cols["Dev Box"], number=1,
               title="Cache das feature flags", assignee="Walter",
               updated_at=datetime.now() - timedelta(days=6)))
    s.add(ProjectDailyEntry(project_id=pid, date=date.today().isoformat(), kind="WORK",
                            title="cashier", body="Fechamos a onda 1 do cashier."))
    s.commit()
    s.close()

    from relay.db.models import Recording
    s = get_session()
    r = Recording(title="Daily da migração", transcript="Walter: o cache está travado.",
                  live_state_json=json.dumps({"tips": ["dica antiga"], "plan": [], "action_items": [],
                                              "decisions": [], "questions": []}, ensure_ascii=False),
                  tags="[]")
    s.add(r)
    s.commit()
    rid = r.id
    s.close()
    return {"pid": pid, "rid": rid}


def test_api_analisa_com_contexto_do_projeto(client, dados, monkeypatch):
    monkeypatch.setattr("relay.config.get_active_ai_provider", lambda: None)

    r = client.post(f"/api/recordings/{dados['rid']}/analyze", json={"projectId": dados["pid"]})
    assert r.status_code == 200
    d = r.json()
    assert d["usedProjectContext"] is True
    assert d["engine"] == "heuristic"
    assert d["aiAvailable"] is False
    assert any("MIG-1" in t for t in d["tips"])
    assert d["saved"] is False
    assert d["sections"] is None


def test_api_analisa_e_salva_no_estado(client, dados, monkeypatch):
    monkeypatch.setattr("relay.config.get_active_ai_provider", lambda: None)

    r = client.post(f"/api/recordings/{dados['rid']}/analyze",
                    json={"projectId": dados["pid"], "save": True})
    assert r.status_code == 200
    d = r.json()
    assert d["saved"] is True
    assert d["sections"]["tips"]           # devolve o estado já mesclado

    detalhe = client.get(f"/api/recordings/{dados['rid']}").json()
    tips = detalhe["sections"]["tips"]
    assert "dica antiga" in tips           # preservou o que existia
    assert any("MIG-1" in t for t in tips) # somou a análise


def test_api_sem_projeto_analisa_a_transcricao(client, dados, monkeypatch):
    monkeypatch.setattr("relay.config.get_active_ai_provider", lambda: None)
    r = client.post(f"/api/recordings/{dados['rid']}/analyze", json={})
    assert r.status_code == 200
    assert r.json()["usedProjectContext"] is False


def test_api_404(client, dados):
    assert client.post("/api/recordings/999/analyze", json={}).status_code == 404
    assert client.post(f"/api/recordings/{dados['rid']}/analyze",
                       json={"projectId": 999}).status_code == 404
