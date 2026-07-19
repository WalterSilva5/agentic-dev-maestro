"""Persistência das reuniões.

Concentra todo o acesso ao banco que antes ficava espalhado pela view: abrir
e fechar a sessão, montar as consultas e gravar. As funções devolvem dicts
já desacoplados da sessão — a view nunca segura um objeto SQLAlchemy vivo,
então não há risco de acessar atributo de instância expirada.
"""
from __future__ import annotations

import json
from datetime import datetime

from maestro_local.db.models import Recording, get_session


def _tags(raw: str) -> list:
    try:
        return json.loads(raw) if raw else []
    except Exception:  # noqa: BLE001
        return []


def _to_dict(r: Recording) -> dict:
    """Snapshot de uma gravação, com os campos que a view usa."""
    return {
        "rec_id": r.id,
        "kind": r.kind or "meeting",
        "title": r.title or "",
        "topic": r.topic or "",
        "transcript": r.transcript or "",
        "markdown": r.markdown or "",
        "summary_json": r.summary_json or "",
        "live_state_json": r.live_state_json or "",
        "duration": r.duration or 0.0,
        "language": r.language or "",
        "audio_path": r.audio_path or "",
        "tags": _tags(r.tags),
        "created_at": r.created_at,
        "archived_at": r.archived_at,
    }


def get(rec_id) -> dict | None:
    """Uma gravação pelo id, ou None se não existir."""
    if not rec_id:
        return None
    s = get_session()
    try:
        r = s.get(Recording, rec_id)
        return _to_dict(r) if r is not None else None
    finally:
        s.close()


def list_recent(show_archived: bool = False, limit: int = 200) -> list[dict]:
    """Histórico na ordem manual (sort_order) e, empatando, mais recentes antes."""
    s = get_session()
    try:
        q = s.query(Recording)
        if not show_archived:
            q = q.filter(Recording.archived_at == None)  # noqa: E711
        recs = q.order_by(Recording.sort_order.asc(),
                          Recording.created_at.desc()).limit(limit).all()
        return [_to_dict(r) for r in recs]
    finally:
        s.close()


def save(rec_id, data: dict):
    """Cria ou atualiza uma gravação e devolve o id (novo, se foi criada).

    Só grava as chaves presentes em ``data`` — assim dá para salvar apenas a
    transcrição sem zerar o resumo já existente.
    """
    fields = ("kind", "title", "topic", "transcript", "markdown", "summary_json",
              "live_state_json", "duration", "language", "audio_path")
    s = get_session()
    try:
        rec = s.get(Recording, rec_id) if rec_id else None
        if rec is None:
            rec = Recording()
            s.add(rec)
        for f in fields:
            if f in data:
                setattr(rec, f, data[f])
        if "tags" in data:
            rec.tags = json.dumps(data["tags"] or [], ensure_ascii=False)
        s.commit()
        return rec.id
    finally:
        s.close()


def delete(rec_id) -> None:
    s = get_session()
    try:
        r = s.get(Recording, rec_id)
        if r is not None:
            s.delete(r)
            s.commit()
    finally:
        s.close()


def set_archived(rec_id, archived: bool) -> None:
    s = get_session()
    try:
        r = s.get(Recording, rec_id)
        if r is not None:
            r.archived_at = datetime.utcnow() if archived else None
            s.commit()
    finally:
        s.close()


def is_archived(rec_id) -> bool:
    rec = get(rec_id)
    return bool(rec and rec["archived_at"])


def save_order(rec_ids: list) -> None:
    """Grava a ordem manual do histórico numa única transação."""
    s = get_session()
    try:
        for i, rid in enumerate(rec_ids):
            r = s.get(Recording, rid)
            if r is not None:
                r.sort_order = i
        s.commit()
    finally:
        s.close()
