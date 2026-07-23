"""Testes da memória agentic (sem rede — embed mockado)."""
from __future__ import annotations


def test_remember_and_keyword_search(temp_db, monkeypatch):
    from maestro_local import memory as mem
    from maestro_local.db.models import get_session

    monkeypatch.setattr(mem, "embed_text", lambda *a, **k: (None, ""))

    s = get_session()
    try:
        e = mem.remember(
            s,
            title="Usar SQLite por workspace",
            content="Cada workspace tem seu próprio arquivo maestro.db isolado.",
            kind="decision",
            tags=["arquitetura", "db"],
            importance=0.9,
            embed=True,
        )
        s.commit()
        mid = e.id
        assert mid

        hits = mem.search(s, "sqlite workspace isolado", top_k=5, mark_accessed=False)
        assert hits
        assert hits[0]["id"] == mid
        assert hits[0]["kind"] == "decision"
        assert "arquitetura" in hits[0]["tags"]

        listed = mem.list_entries(s, kind="decision")
        assert any(x["id"] == mid for x in listed)

        st = mem.stats(s)
        assert st["total"] >= 1
        assert st["byKind"].get("decision", 0) >= 1
    finally:
        s.close()


def test_semantic_search_with_fake_embeddings(temp_db, monkeypatch):
    from maestro_local import memory as mem
    from maestro_local.db.models import get_session

    # vetores simples: similaridade alta entre "auth jwt" e a memória de auth
    def fake_embed(text, model=None):
        t = (text or "").lower()
        if "auth" in t or "jwt" in t or "login" in t:
            return [1.0, 0.0, 0.0], "fake"
        if "cor" in t or "tema" in t or "dark" in t:
            return [0.0, 1.0, 0.0], "fake"
        return [0.0, 0.0, 1.0], "fake"

    monkeypatch.setattr(mem, "embed_text", fake_embed)

    s = get_session()
    try:
        a = mem.remember(
            s, title="Auth", content="Login via JWT Bearer token", kind="decision"
        )
        mem.remember(
            s, title="UI", content="Tema dark padrão na interface", kind="preference"
        )
        s.commit()

        hits = mem.search(s, "autenticação jwt login", top_k=2, mark_accessed=False)
        assert hits
        assert hits[0]["id"] == a.id
        assert hits[0]["score"] > 0
    finally:
        s.close()


def test_soft_delete_and_format(temp_db, monkeypatch):
    from maestro_local import memory as mem
    from maestro_local.db.models import get_session

    monkeypatch.setattr(mem, "embed_text", lambda *a, **k: (None, ""))

    s = get_session()
    try:
        e = mem.remember(s, title="X", content="conteúdo de teste", kind="fact")
        s.commit()
        mid = e.id
        mem.soft_delete(s, e)
        s.commit()

        hits = mem.search(s, "conteúdo", mark_accessed=False)
        assert all(h["id"] != mid for h in hits)

        md = mem.format_for_agent([
            {"id": 1, "kind": "fact", "title": "T", "content": "corpo", "score": 0.9}
        ])
        assert "Memórias" in md
        assert "corpo" in md
    finally:
        s.close()


def test_ingest_task(temp_db, monkeypatch):
    from maestro_local import memory as mem
    from maestro_local.db.models import (
        BoardColumn,
        Project,
        Task,
        get_session,
    )

    monkeypatch.setattr(mem, "embed_text", lambda *a, **k: (None, ""))

    s = get_session()
    try:
        p = Project(name="Demo", key="DEMO", task_seq=1)
        s.add(p)
        s.flush()
        col = BoardColumn(project_id=p.id, name="Backlog", order=0)
        s.add(col)
        s.flush()
        t = Task(
            project_id=p.id,
            column_id=col.id,
            number=1,
            title="Implementar memória",
            objective="Persistir contexto para agentes",
            description="Tabela memory_entries + busca híbrida",
            type="FEATURE",
            priority="HIGH",
        )
        s.add(t)
        s.commit()

        created = mem.ingest(s, "task", t.id)
        assert len(created) == 1
        assert "Implementar memória" in created[0]["title"]
        assert created[0]["sourceType"] == "task"
        assert created[0]["taskId"] == t.id
    finally:
        s.close()


def test_api_memory_endpoints(temp_db, monkeypatch):
    from fastapi.testclient import TestClient
    from maestro_local import memory as mem
    from maestro_local.api.app import app

    monkeypatch.setattr(mem, "embed_text", lambda *a, **k: (None, ""))

    client = TestClient(app)
    r = client.post("/api/memory", json={
        "title": "Preferência de commits",
        "content": "Commits e branches em português",
        "kind": "preference",
        "importance": 0.8,
        "tags": ["git", "convenção"],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "preference"
    mid = body["id"]

    r = client.post("/api/memory/search", json={"query": "commits português", "topK": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert "agentContext" in data

    r = client.get("/api/memory/stats")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = client.delete(f"/api/memory/{mid}")
    assert r.status_code == 200
    assert r.json()["ok"] is True
