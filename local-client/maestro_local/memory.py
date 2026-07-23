"""Agentic memory por workspace: armazenamento estruturado + busca híbrida
(semântica via embeddings OpenAI-compat + palavras-chave).

Escopo = SQLite do workspace ativo. Projetada para agentes: kinds tipados,
fontes rastreáveis, scores e formato JSON/markdown legível.
"""
from __future__ import annotations

import json
import logging
import math
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("maestro.memory")

MEMORY_KINDS = (
    "fact",
    "decision",
    "preference",
    "episode",
    "procedure",
    "context",
)

SOURCE_TYPES = (
    "manual",
    "task",
    "comment",
    "document",
    "daily",
    "recording",
    "sprint",
    "agent",
    "kb",
)

_STOP = {
    "a", "o", "e", "de", "da", "do", "que", "com", "para", "por", "os", "as",
    "um", "uma", "no", "na", "em", "the", "of", "to", "and", "is", "in", "on",
    "se", "ao", "dos", "das", "não", "nao", "mais", "como", "foi", "ser",
}

_EMBED_TIMEOUT = 30
_MAX_EMBED_CHARS = 6000

_ASK_SYSTEM = (
    "Você responde usando SOMENTE as memórias fornecidas como contexto. "
    "Se a resposta não estiver nelas, diga que não encontrou. "
    "Cite os títulos/ids usados. Responda em português, em Markdown."
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def get_memory_config() -> dict:
    from maestro_local.config import load_config
    cfg = load_config().get("settings", {}).get("memory", {}) or {}
    return {
        "enabled": bool(cfg.get("enabled", True)),
        "embedding_model": (cfg.get("embedding_model") or "").strip(),
        "auto_embed": bool(cfg.get("auto_embed", True)),
    }


def set_memory_config(
    enabled: bool | None = None,
    embedding_model: str | None = None,
    auto_embed: bool | None = None,
) -> dict:
    from maestro_local.config import load_config, save_config
    cfg = load_config()
    settings = cfg.setdefault("settings", {})
    mem = settings.setdefault("memory", {})
    if enabled is not None:
        mem["enabled"] = bool(enabled)
    if embedding_model is not None:
        mem["embedding_model"] = embedding_model.strip()
    if auto_embed is not None:
        mem["auto_embed"] = bool(auto_embed)
    save_config(cfg)
    return get_memory_config()


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _tokens(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-zA-Z0-9À-ÿ]{3,}", (text or "").lower())
        if w not in _STOP
    }


def _keyword_score(query: str, title: str, content: str, summary: str = "") -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    title_t = _tokens(title)
    body_t = _tokens(f"{summary} {content}")
    score = float(len(q & body_t))
    score += 2.0 * float(len(q & title_t))
    return score


def _embed_payload_text(title: str, content: str, summary: str = "", kind: str = "") -> str:
    parts = []
    if kind:
        parts.append(f"[{kind}]")
    if title:
        parts.append(title)
    if summary:
        parts.append(summary)
    if content:
        parts.append(content)
    text = "\n".join(parts).strip()
    if len(text) > _MAX_EMBED_CHARS:
        text = text[:_MAX_EMBED_CHARS]
    return text


# ---------------------------------------------------------------------------
# Embeddings (OpenAI-compatible /v1/embeddings)
# ---------------------------------------------------------------------------


def embed_text(text: str, model: str | None = None) -> tuple[Optional[list[float]], str]:
    """Gera embedding via provedor ativo. Retorna (vector|None, model_id)."""
    text = (text or "").strip()
    if not text:
        return None, ""

    mem_cfg = get_memory_config()
    if not mem_cfg.get("enabled", True) or not mem_cfg.get("auto_embed", True):
        return None, ""

    from maestro_local.config import get_active_ai_provider
    provider = get_active_ai_provider()
    if not provider or not provider.get("base_url"):
        return None, ""

    emb_model = (model or mem_cfg.get("embedding_model") or "").strip()
    if not emb_model:
        # Modelos comuns; o provedor pode rejeitar — aí caímos em keyword.
        emb_model = "text-embedding-3-small"

    base = provider["base_url"].rstrip("/")
    url = f"{base}/embeddings"
    body = json.dumps({"model": emb_model, "input": text}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {provider.get('api_key') or 'not-needed'}",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_EMBED_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = data.get("data") or []
        if not items:
            return None, emb_model
        vec = items[0].get("embedding")
        if not isinstance(vec, list) or not vec:
            return None, emb_model
        return [float(x) for x in vec], emb_model
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        logger.debug("embed indisponível (%s): %s", emb_model, e)
        return None, emb_model


def _parse_embedding(raw: str | None) -> Optional[list[float]]:
    if not raw:
        return None
    try:
        vec = json.loads(raw)
        if isinstance(vec, list) and vec:
            return [float(x) for x in vec]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def _dump_embedding(vec: list[float] | None) -> str | None:
    if not vec:
        return None
    return json.dumps(vec)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    try:
        import numpy as np
        va = np.asarray(a, dtype=np.float64)
        vb = np.asarray(b, dtype=np.float64)
        na = float(np.linalg.norm(va))
        nb = float(np.linalg.norm(vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))
    except Exception:  # noqa: BLE001
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def entry_to_dict(entry, *, score: float | None = None, include_embedding: bool = False) -> dict:
    d = {
        "id": entry.id,
        "kind": entry.kind,
        "title": entry.title or "",
        "content": entry.content or "",
        "summary": entry.summary or "",
        "tags": _tags_list(entry.tags),
        "projectId": entry.project_id,
        "taskId": entry.task_id,
        "sourceType": entry.source_type or "manual",
        "sourceId": entry.source_id,
        "importance": float(entry.importance or 0.5),
        "embeddingModel": entry.embedding_model or "",
        "hasEmbedding": bool(entry.embedding),
        "accessCount": int(entry.access_count or 0),
        "lastAccessedAt": entry.last_accessed_at.isoformat() if entry.last_accessed_at else None,
        "createdAt": entry.created_at.isoformat() if entry.created_at else None,
        "updatedAt": entry.updated_at.isoformat() if entry.updated_at else None,
    }
    if score is not None:
        d["score"] = round(float(score), 4)
    if include_embedding and entry.embedding:
        d["embedding"] = _parse_embedding(entry.embedding)
    return d


def _tags_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _tags_str(tags: list[str] | str | None) -> str:
    if tags is None:
        return ""
    if isinstance(tags, str):
        return tags.strip()
    return ", ".join(t.strip() for t in tags if t and str(t).strip())


def format_for_agent(entries: list[dict], *, max_chars: int = 4000) -> str:
    """Markdown compacto para injetar no contexto do agente."""
    if not entries:
        return "Nenhuma memória relevante."
    lines = ["# Memórias do workspace", ""]
    used = 0
    for e in entries:
        block = (
            f"## [{e.get('kind', 'fact')}] {e.get('title') or '(sem título)'} "
            f"(id={e.get('id')})\n"
        )
        if e.get("score") is not None:
            block += f"score={e['score']}  "
        if e.get("projectId"):
            block += f"project={e['projectId']}  "
        if e.get("taskId"):
            block += f"task={e['taskId']}  "
        if e.get("tags"):
            block += f"tags={', '.join(e['tags'])}"
        block += "\n"
        body = (e.get("summary") or e.get("content") or "").strip()
        if len(body) > 600:
            body = body[:600] + "…"
        block += body + "\n\n"
        if used + len(block) > max_chars and used > 0:
            break
        lines.append(block)
        used += len(block)
    return "".join(lines).rstrip()


# ---------------------------------------------------------------------------
# CRUD / remember
# ---------------------------------------------------------------------------


def remember(
    session,
    *,
    title: str,
    content: str,
    kind: str = "fact",
    summary: str = "",
    tags: list[str] | str | None = None,
    project_id: int | None = None,
    task_id: int | None = None,
    source_type: str = "manual",
    source_id: int | None = None,
    importance: float = 0.5,
    embed: bool = True,
):
    """Cria uma entrada de memória. Retorna o ORM MemoryEntry."""
    from maestro_local.db.models import MemoryEntry

    kind = (kind or "fact").lower().strip()
    if kind not in MEMORY_KINDS:
        kind = "fact"
    source_type = (source_type or "manual").lower().strip()
    if source_type not in SOURCE_TYPES:
        source_type = "manual"
    importance = max(0.0, min(1.0, float(importance if importance is not None else 0.5)))

    title = (title or "").strip() or (content or "")[:80]
    content = (content or "").strip()
    if not content:
        raise ValueError("content vazio")

    entry = MemoryEntry(
        kind=kind,
        title=title,
        content=content,
        summary=(summary or "").strip(),
        tags=_tags_str(tags),
        project_id=project_id,
        task_id=task_id,
        source_type=source_type,
        source_id=source_id,
        importance=importance,
    )

    if embed:
        vec, model = embed_text(_embed_payload_text(title, content, summary, kind))
        if vec:
            entry.embedding = _dump_embedding(vec)
            entry.embedding_model = model

    session.add(entry)
    session.flush()
    return entry


def update_entry(
    session,
    entry,
    *,
    title: str | None = None,
    content: str | None = None,
    kind: str | None = None,
    summary: str | None = None,
    tags: list[str] | str | None = None,
    project_id: Any = ...,
    task_id: Any = ...,
    importance: float | None = None,
    reembed: bool = True,
):
    changed_text = False
    if title is not None:
        entry.title = title.strip()
        changed_text = True
    if content is not None:
        entry.content = content.strip()
        changed_text = True
    if summary is not None:
        entry.summary = summary.strip()
        changed_text = True
    if kind is not None:
        k = kind.lower().strip()
        if k in MEMORY_KINDS:
            entry.kind = k
            changed_text = True
    if tags is not None:
        entry.tags = _tags_str(tags)
    if project_id is not ...:
        entry.project_id = project_id
    if task_id is not ...:
        entry.task_id = task_id
    if importance is not None:
        entry.importance = max(0.0, min(1.0, float(importance)))
    entry.updated_at = datetime.utcnow()

    if reembed and changed_text:
        vec, model = embed_text(
            _embed_payload_text(entry.title, entry.content or "", entry.summary or "", entry.kind)
        )
        if vec:
            entry.embedding = _dump_embedding(vec)
            entry.embedding_model = model
    session.flush()
    return entry


def soft_delete(session, entry) -> None:
    entry.deleted_at = datetime.utcnow()
    session.flush()


def touch_access(session, entries: list) -> None:
    now = datetime.utcnow()
    for e in entries:
        e.access_count = int(e.access_count or 0) + 1
        e.last_accessed_at = now
    session.flush()


# ---------------------------------------------------------------------------
# Search (hybrid)
# ---------------------------------------------------------------------------


def _base_query(session, *, kind=None, project_id=None, task_id=None, tags=None):
    from maestro_local.db.models import MemoryEntry
    q = session.query(MemoryEntry).filter(MemoryEntry.deleted_at.is_(None))
    if kind:
        kinds = [k.strip().lower() for k in kind.split(",") if k.strip()]
        if len(kinds) == 1:
            q = q.filter(MemoryEntry.kind == kinds[0])
        elif kinds:
            q = q.filter(MemoryEntry.kind.in_(kinds))
    if project_id is not None:
        q = q.filter(MemoryEntry.project_id == project_id)
    if task_id is not None:
        q = q.filter(MemoryEntry.task_id == task_id)
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        for t in tag_list:
            q = q.filter(MemoryEntry.tags.ilike(f"%{t}%"))
    return q


def search(
    session,
    query: str,
    *,
    kind: str | None = None,
    project_id: int | None = None,
    task_id: int | None = None,
    tags: str | None = None,
    top_k: int = 8,
    min_score: float = 0.0,
    mark_accessed: bool = True,
) -> list[dict]:
    """Busca híbrida: coseno (se embedding) + keyword, ponderado por importance."""
    top_k = max(1, min(50, int(top_k or 8)))
    query = (query or "").strip()
    rows = _base_query(
        session, kind=kind, project_id=project_id, task_id=task_id, tags=tags
    ).all()

    if not rows:
        return []

    if not query:
        rows.sort(key=lambda e: (
            -(e.importance or 0.5),
            -(e.access_count or 0),
            e.updated_at or datetime.min,
        ), reverse=False)
        # sort above is messy — prefer importance then recent
        rows = sorted(
            rows,
            key=lambda e: (
                float(e.importance or 0.5),
                e.updated_at or datetime.min,
            ),
            reverse=True,
        )[:top_k]
        return [entry_to_dict(e) for e in rows]

    q_vec, _ = embed_text(query)
    scored: list[tuple[float, Any]] = []
    kw_scores = []
    for e in rows:
        kw = _keyword_score(query, e.title or "", e.content or "", e.summary or "")
        kw_scores.append(kw)

    max_kw = max(kw_scores) if kw_scores else 0.0

    for e, kw in zip(rows, kw_scores):
        kw_n = (kw / max_kw) if max_kw > 0 else 0.0
        sem = 0.0
        e_vec = _parse_embedding(e.embedding)
        if q_vec and e_vec:
            # map cosine [-1,1] -> [0,1]
            sem = (cosine_similarity(q_vec, e_vec) + 1.0) / 2.0

        if q_vec and e_vec:
            base = 0.72 * sem + 0.28 * kw_n
        else:
            base = kw_n

        if base <= 0 and kw <= 0:
            continue
        imp = float(e.importance or 0.5)
        score = base * (0.7 + 0.3 * imp)
        if score >= min_score:
            scored.append((score, e))

    scored.sort(key=lambda x: -x[0])
    top = scored[:top_k]
    if mark_accessed and top:
        touch_access(session, [e for _, e in top])
        try:
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()

    return [entry_to_dict(e, score=sc) for sc, e in top]


def list_entries(
    session,
    *,
    kind: str | None = None,
    project_id: int | None = None,
    task_id: int | None = None,
    tags: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    from maestro_local.db.models import MemoryEntry

    limit = max(1, min(200, int(limit or 50)))
    offset = max(0, int(offset or 0))
    query = _base_query(
        session, kind=kind, project_id=project_id, task_id=task_id, tags=tags
    ).order_by(MemoryEntry.updated_at.desc())
    if q and q.strip():
        ql = f"%{q.strip().lower()}%"
        query = query.filter(
            (MemoryEntry.title.ilike(ql))
            | (MemoryEntry.content.ilike(ql))
            | (MemoryEntry.summary.ilike(ql))
            | (MemoryEntry.tags.ilike(ql))
        )
    rows = query.offset(offset).limit(limit).all()
    return [entry_to_dict(e) for e in rows]


def stats(session) -> dict:
    from maestro_local.db.models import MemoryEntry
    from sqlalchemy import func
    base = session.query(MemoryEntry).filter(MemoryEntry.deleted_at.is_(None))
    total = base.count()
    with_emb = base.filter(MemoryEntry.embedding.isnot(None)).count()
    by_kind = dict(
        session.query(MemoryEntry.kind, func.count(MemoryEntry.id))
        .filter(MemoryEntry.deleted_at.is_(None))
        .group_by(MemoryEntry.kind)
        .all()
    )
    by_source = dict(
        session.query(MemoryEntry.source_type, func.count(MemoryEntry.id))
        .filter(MemoryEntry.deleted_at.is_(None))
        .group_by(MemoryEntry.source_type)
        .all()
    )
    return {
        "total": total,
        "withEmbedding": with_emb,
        "byKind": by_kind,
        "bySource": by_source,
        "config": get_memory_config(),
    }


def reembed_all(session, *, only_missing: bool = True, limit: int = 200) -> dict:
    from maestro_local.db.models import MemoryEntry
    q = session.query(MemoryEntry).filter(MemoryEntry.deleted_at.is_(None))
    if only_missing:
        q = q.filter((MemoryEntry.embedding.is_(None)) | (MemoryEntry.embedding == ""))
    rows = q.order_by(MemoryEntry.id).limit(max(1, min(1000, limit))).all()
    ok = 0
    fail = 0
    for e in rows:
        vec, model = embed_text(
            _embed_payload_text(e.title or "", e.content or "", e.summary or "", e.kind or "")
        )
        if vec:
            e.embedding = _dump_embedding(vec)
            e.embedding_model = model
            e.updated_at = datetime.utcnow()
            ok += 1
        else:
            fail += 1
    session.commit()
    return {"processed": len(rows), "embedded": ok, "failed": fail}


# ---------------------------------------------------------------------------
# Ingest from workspace entities
# ---------------------------------------------------------------------------


def ingest(session, source_type: str, source_id: int, *, project_id: int | None = None) -> list[dict]:
    """Extrai memórias de uma entidade existente. Evita duplicar mesma source."""
    source_type = (source_type or "").lower().strip()
    if source_type not in SOURCE_TYPES or source_type in ("manual", "agent"):
        raise ValueError(f"sourceType inválido para ingest: {source_type}")

    from maestro_local.db.models import MemoryEntry
    existing = (
        session.query(MemoryEntry)
        .filter(
            MemoryEntry.source_type == source_type,
            MemoryEntry.source_id == source_id,
            MemoryEntry.deleted_at.is_(None),
        )
        .all()
    )
    # re-ingest: soft-delete previous auto entries for this source
    for e in existing:
        e.deleted_at = datetime.utcnow()

    builders = {
        "task": _ingest_task,
        "comment": _ingest_comment,
        "document": _ingest_document,
        "daily": _ingest_daily,
        "recording": _ingest_recording,
        "sprint": _ingest_sprint,
        "kb": _ingest_kb,
    }
    fn = builders.get(source_type)
    if not fn:
        raise ValueError(f"ingest não suportado: {source_type}")

    payloads = fn(session, source_id, project_id=project_id)
    created = []
    for p in payloads:
        entry = remember(session, **p)
        created.append(entry)
    session.commit()
    return [entry_to_dict(e) for e in created]


def _ingest_task(session, source_id: int, project_id: int | None = None) -> list[dict]:
    from maestro_local.db.models import Task
    t = session.query(Task).filter(Task.id == source_id, Task.deleted_at.is_(None)).first()
    if not t:
        return []
    code = t.code
    parts = [f"Tarefa {code}: {t.title}"]
    if t.objective:
        parts.append(f"Objetivo: {t.objective}")
    if t.description:
        parts.append(f"Descrição: {t.description}")
    if t.acceptance:
        parts.append(f"Aceite: {t.acceptance}")
    content = "\n\n".join(parts)
    return [{
        "title": f"{code}: {t.title}",
        "content": content,
        "summary": (t.objective or t.title or "")[:300],
        "kind": "context",
        "tags": ["task", (t.type or "").lower()],
        "project_id": project_id or t.project_id,
        "task_id": t.id,
        "source_type": "task",
        "source_id": t.id,
        "importance": 0.55 if t.priority in ("HIGH", "URGENT") else 0.45,
    }]


def _ingest_comment(session, source_id: int, project_id: int | None = None) -> list[dict]:
    from maestro_local.db.models import Comment, Task
    c = session.query(Comment).filter(Comment.id == source_id).first()
    if not c or not (c.body or "").strip():
        return []
    task = session.query(Task).get(c.task_id) if c.task_id else None
    code = task.code if task else f"task-{c.task_id}"
    kind = "decision" if (c.type or "").upper() == "CODE_REVIEW" else "episode"
    return [{
        "title": f"Comentário em {code}",
        "content": c.body.strip(),
        "summary": c.body.strip()[:200],
        "kind": kind,
        "tags": ["comment", (c.type or "COMMENT").lower()],
        "project_id": project_id or (task.project_id if task else None),
        "task_id": c.task_id,
        "source_type": "comment",
        "source_id": c.id,
        "importance": 0.6 if kind == "decision" else 0.4,
    }]


def _ingest_document(session, source_id: int, project_id: int | None = None) -> list[dict]:
    from maestro_local.db.models import Document
    d = session.query(Document).filter(Document.id == source_id).first()
    if not d or not (d.body or "").strip():
        return []
    dtype = (d.type or "NOTES").upper()
    kind_map = {
        "ADR": "decision",
        "SPEC": "procedure",
        "PLAN": "context",
        "KB": "fact",
        "NOTES": "context",
    }
    return [{
        "title": d.title or f"Documento {d.id}",
        "content": d.body.strip(),
        "summary": (d.body or "")[:250],
        "kind": kind_map.get(dtype, "context"),
        "tags": ["document", dtype.lower()],
        "project_id": project_id or d.project_id,
        "task_id": d.task_id,
        "source_type": "document" if dtype != "KB" else "kb",
        "source_id": d.id,
        "importance": 0.75 if dtype == "ADR" else 0.55,
    }]


def _ingest_kb(session, source_id: int, project_id: int | None = None) -> list[dict]:
    return _ingest_document(session, source_id, project_id=project_id)


def _ingest_daily(session, source_id: int, project_id: int | None = None) -> list[dict]:
    from maestro_local.db.models import DailyNote
    n = session.query(DailyNote).filter(DailyNote.id == source_id).first()
    if not n:
        return []
    chunks = []
    if (n.body or "").strip():
        chunks.append({
            "title": f"Diário {n.date} — notas",
            "content": n.body.strip(),
            "summary": n.body.strip()[:200],
            "kind": "episode",
            "tags": ["daily", "notes", n.date],
            "project_id": project_id,
            "task_id": None,
            "source_type": "daily",
            "source_id": n.id,
            "importance": 0.5,
        })
    if (n.report or "").strip():
        chunks.append({
            "title": f"Diário {n.date} — relatório",
            "content": n.report.strip(),
            "summary": n.report.strip()[:200],
            "kind": "episode",
            "tags": ["daily", "report", n.date],
            "project_id": project_id,
            "task_id": None,
            "source_type": "daily",
            "source_id": n.id,
            "importance": 0.55,
        })
    return chunks


def _ingest_recording(session, source_id: int, project_id: int | None = None) -> list[dict]:
    from maestro_local.db.models import Recording
    r = session.query(Recording).filter(Recording.id == source_id).first()
    if not r:
        return []
    body = (r.markdown or "").strip()
    if not body and r.summary_json:
        body = r.summary_json.strip()
    if not body and r.transcript:
        body = (r.transcript or "")[:4000]
    if not body:
        return []
    title = r.title or r.topic or f"Reunião {r.id}"
    return [{
        "title": title,
        "content": body,
        "summary": (r.topic or title)[:250],
        "kind": "episode",
        "tags": ["recording", r.kind or "meeting"],
        "project_id": project_id,
        "task_id": None,
        "source_type": "recording",
        "source_id": r.id,
        "importance": 0.65,
    }]


def _ingest_sprint(session, source_id: int, project_id: int | None = None) -> list[dict]:
    from maestro_local.db.models import Sprint
    sp = session.query(Sprint).filter(Sprint.id == source_id).first()
    if not sp:
        return []
    parts = [f"Sprint: {sp.name}"]
    if sp.goal:
        parts.append(f"Meta: {sp.goal}")
    if sp.retro_json:
        parts.append(f"Retrospectiva: {sp.retro_json}")
    content = "\n\n".join(parts)
    return [{
        "title": f"Sprint {sp.name}",
        "content": content,
        "summary": (sp.goal or sp.name or "")[:250],
        "kind": "decision" if sp.retro_json else "context",
        "tags": ["sprint", (sp.status or "").lower()],
        "project_id": project_id or sp.project_id,
        "task_id": None,
        "source_type": "sprint",
        "source_id": sp.id,
        "importance": 0.6,
    }]


# ---------------------------------------------------------------------------
# Q&A over memories
# ---------------------------------------------------------------------------


def answer(session, question: str, *, project_id: int | None = None, top_k: int = 6) -> dict:
    from maestro_local.ai.llm import invoke_text

    hits = search(session, question, project_id=project_id, top_k=top_k, mark_accessed=True)
    if not hits:
        return {"answer": "Não encontrei memórias relevantes.", "sources": []}

    context = "\n\n".join(
        f"### [{h.get('kind')}] {h.get('title')} (id={h.get('id')})\n"
        f"{(h.get('summary') or h.get('content') or '')[:2000]}"
        for h in hits
    )
    user = f"Memórias:\n{context}\n\nPergunta: {question}"
    text = invoke_text([("system", _ASK_SYSTEM), ("user", user)], temperature=0.2)
    return {
        "answer": text,
        "sources": [
            {"id": h["id"], "title": h["title"], "kind": h["kind"], "score": h.get("score")}
            for h in hits
        ],
    }
