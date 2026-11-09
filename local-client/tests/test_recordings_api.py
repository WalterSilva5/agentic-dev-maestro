"""API de reuniões: listar, ver, editar, arquivar, exportar e excluir."""
import json

import pytest
from fastapi.testclient import TestClient

from relay.api.app import app
from relay.db.models import Recording, init_db
from relay.meetings_export import sections, to_markdown, to_text


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
def reuniao(client):
    """Cria uma reunião direto no banco (a gravação em si é do desktop)."""
    from relay.db.models import get_session

    estado = {
        "plan": ["Alinhar migração", "Fechar pendências"],
        "tips": ["Confirmar prazo com o PO"],
        "action_items": [
            {"description": "Revisar o PR do dev", "assignee": "Walter"},
            {"description": "Rodar o plano de teste", "assignee": ""},
        ],
        "decisions": ["Entregar cashier na quinta"],
        "questions": [
            {"question": "Quem valida o teste?", "answer": "Jeferson", "resolved": True},
            {"question": "Vai ter rollback?", "answer": "", "resolved": False},
        ],
    }
    s = get_session()
    r = Recording(
        kind="meeting", title="Daily da migração", topic="migração GX",
        transcript="Walter: precisamos revisar o PR do dev hoje.",
        live_state_json=json.dumps(estado, ensure_ascii=False),
        tags=json.dumps(["migração", "daily"], ensure_ascii=False),
        duration=1830.0,
    )
    s.add(r)
    s.commit()
    rid = r.id
    s.close()
    return rid


# --------------------------------------------------------------------------
# export (helpers)
# --------------------------------------------------------------------------

def test_markdown_monta_a_partir_do_estado_ao_vivo(reuniao):
    from relay.db.models import get_session

    s = get_session()
    r = s.get(Recording, reuniao)
    md = to_markdown({
        "title": r.title, "kind": r.kind, "created_at": r.created_at,
        "duration": r.duration, "topic": r.topic,
        "live_state": json.loads(r.live_state_json),
        "transcript": r.transcript, "markdown": "",
    })
    s.close()

    assert md.startswith("# Daily da migração")
    for trecho in ("## 🗺 Plano", "## 💡 Dicas", "## ✅ Ações",
                   "## 📌 Decisões", "## ❓ Perguntas", "Revisar o PR do dev"):
        assert trecho in md


def test_texto_puro_sem_marcacao(reuniao):
    from relay.db.models import get_session

    s = get_session()
    r = s.get(Recording, reuniao)
    txt = to_text({
        "title": r.title, "kind": r.kind, "created_at": r.created_at,
        "live_state": json.loads(r.live_state_json), "transcript": r.transcript,
    })
    s.close()
    assert md_heading_ausente(txt)
    assert "PLANO" in txt
    assert "• " in txt


def md_heading_ausente(txt: str) -> bool:
    return "## " not in txt and "**" not in txt


def test_sections_normaliza_acoes_e_perguntas():
    dados = sections({"live_state": json.dumps({
        "action_items": [{"description": "fazer X", "assignee": "Ana"}, "solta"],
        "questions": [{"question": "q1", "answer": "a1", "resolved": True}, "q2"],
        "plan": ["p"], "tips": [], "decisions": ["d"],
    })})
    assert dados["actionItems"][0] == {"description": "fazer X", "assignee": "Ana"}
    assert dados["actionItems"][1] == {"description": "solta", "assignee": ""}
    assert dados["questions"][0]["resolved"] is True
    assert dados["questions"][1] == {"question": "q2", "answer": "", "resolved": False}


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def test_lista_reunioes(client, reuniao):
    r = client.get("/api/recordings")
    assert r.status_code == 200
    itens = r.json()
    assert len(itens) == 1
    item = itens[0]
    assert item["id"] == reuniao
    assert item["title"] == "Daily da migração"
    assert item["tags"] == ["migração", "daily"]
    assert item["hasTranscript"] is True
    assert item["hasSummary"] is False     # sem resumo salvo ainda
    assert item["duration"] == 1830.0
    # a lista não carrega a transcrição inteira
    assert "transcript" not in item


def test_detalhe_traz_transcricao_secoes_e_estado(client, reuniao):
    r = client.get(f"/api/recordings/{reuniao}")
    assert r.status_code == 200
    d = r.json()
    assert d["transcript"].startswith("Walter:")
    assert d["sections"]["plan"] == ["Alinhar migração", "Fechar pendências"]
    assert len(d["sections"]["actionItems"]) == 2
    assert d["sections"]["questions"][0]["resolved"] is True
    assert d["liveState"]["decisions"] == ["Entregar cashier na quinta"]


def test_edita_titulo_topic_tags_e_transcricao(client, reuniao):
    r = client.patch(f"/api/recordings/{reuniao}", json={
        "title": "Daily 08/11", "topic": "migração", "tags": ["daily"],
        "transcript": "transcrição corrigida à mão",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["title"] == "Daily 08/11"
    assert d["tags"] == ["daily"]
    assert d["transcript"] == "transcrição corrigida à mão"

    # persistiu
    assert client.get(f"/api/recordings/{reuniao}").json()["title"] == "Daily 08/11"


def test_edita_markdown_do_resumo(client, reuniao):
    r = client.patch(f"/api/recordings/{reuniao}", json={"markdown": "# Resumo\n\nfeito à mão"})
    assert r.status_code == 200
    assert r.json()["hasSummary"] is True
    md = client.get(f"/api/recordings/{reuniao}/export", params={"format": "md"})
    assert md.text.startswith("# Resumo")


def test_arquiva_e_filtra(client, reuniao):
    assert client.post(f"/api/recordings/{reuniao}/archive", json={"archived": True}).status_code == 200
    assert client.get("/api/recordings").json() == []
    assert len(client.get("/api/recordings", params={"archived": "only"}).json()) == 1
    assert len(client.get("/api/recordings", params={"archived": "all"}).json()) == 1

    assert client.post(f"/api/recordings/{reuniao}/archive", json={"archived": False}).status_code == 200
    assert len(client.get("/api/recordings").json()) == 1


def test_busca_por_texto(client, reuniao):
    assert len(client.get("/api/recordings", params={"q": "migração"}).json()) == 1
    assert len(client.get("/api/recordings", params={"q": "PR do dev"}).json()) == 1
    assert client.get("/api/recordings", params={"q": "inexistente"}).json() == []


def test_export_md_txt_json(client, reuniao):
    md = client.get(f"/api/recordings/{reuniao}/export", params={"format": "md"})
    assert md.status_code == 200
    assert md.headers["content-type"].startswith("text/markdown")
    assert "attachment" in md.headers["content-disposition"]
    assert "# Daily da migração" in md.text
    # o documento sai completo: seções do assistente + transcrição
    for trecho in ("## 🗺 Plano", "## ✅ Ações", "## 📌 Decisões", "## 🎙 Transcrição"):
        assert trecho in md.text

    txt = client.get(f"/api/recordings/{reuniao}/export", params={"format": "txt"})
    assert txt.status_code == 200
    assert txt.text.startswith("DAILY DA MIGRAÇÃO")
    assert "## " not in txt.text

    js = client.get(f"/api/recordings/{reuniao}/export", params={"format": "json"})
    assert js.status_code == 200
    assert js.json()["title"] == "Daily da migração"
    assert js.json()["sections"]["decisions"] == ["Entregar cashier na quinta"]

    ru = client.get(f"/api/recordings/{reuniao}/export", params={"format": "xml"})
    assert ru.status_code == 400


def test_exclui_reuniao(client, reuniao):
    assert client.delete(f"/api/recordings/{reuniao}").status_code == 200
    assert client.get(f"/api/recordings/{reuniao}").status_code == 404
    assert client.get("/api/recordings").json() == []


def test_404s(client):
    assert client.get("/api/recordings/999").status_code == 404
    assert client.patch("/api/recordings/999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/recordings/999").status_code == 404
    assert client.get("/api/recordings/999/export").status_code == 404
    assert client.get("/api/recordings/999/audio").status_code == 404


def test_filtra_por_tipo(client, reuniao):
    assert len(client.get("/api/recordings", params={"kind": "meeting"}).json()) == 1
    assert client.get("/api/recordings", params={"kind": "study"}).json() == []
