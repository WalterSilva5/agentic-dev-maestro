"""Exportação de reuniões (markdown / texto) — usada pela API e pela web.

O desktop grava `markdown` quando o resumo da IA é gerado; quando não há, o
documento é remontado a partir do estado do assistente ao vivo + transcrição,
para nenhuma reunião ficar sem exportação.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

HEADINGS = {
    "plan": "Plano",
    "tips": "Dicas",
    "action_items": "Ações",
    "decisions": "Decisões",
    "questions": "Perguntas",
}

ICONS = {"plan": "🗺", "tips": "💡", "action_items": "✅", "decisions": "📌", "questions": "❓"}


def parse_json(texto: str | None, padrao):
    """JSON tolerante: devolve o padrão quando vazio/inválido."""
    if not texto:
        return padrao
    try:
        return json.loads(texto)
    except Exception:  # noqa: BLE001
        return padrao


def _quando(rec: dict) -> datetime:
    valor = rec.get("created_at")
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor.replace("Z", ""))
        except ValueError:
            return datetime.now()
    return datetime.now()


def _estado(rec: dict) -> dict:
    """Aceita `live_state` (banco) e `liveState` (resposta da API)."""
    return rec.get("live_state") or rec.get("liveState") or {}


def to_markdown(rec: dict) -> str:
    """Documento markdown da reunião (usa o resumo salvo quando existe)."""
    salvo = (rec.get("markdown") or "").strip()
    if salvo:
        return salvo + "\n"

    from maestro_local.transcricoes.markdown_gen import live_meeting_to_markdown

    return live_meeting_to_markdown(
        title=rec.get("title") or rec.get("topic") or "",
        kind=rec.get("kind") or "meeting",
        date_str=_quando(rec).strftime("%d/%m/%Y %H:%M"),
        duration=rec.get("duration") or 0.0,
        topic=rec.get("topic") or "",
        state=_estado(rec),
        transcript=rec.get("transcript") or "",
        summary_md="",
    )


def to_text(rec: dict) -> str:
    """Versão texto puro: tira marcação, mantém a leitura linear."""
    md = to_markdown(rec)
    linhas = []
    for linha in md.splitlines():
        bruta = linha.rstrip()
        if not bruta.strip():
            linhas.append("")
            continue
        if bruta.startswith("#"):
            titulo = bruta.lstrip("#").strip()
            linhas.append(titulo.upper())
            linhas.append("=" * len(titulo))
            continue
        limpa = re.sub(r"\*\*(.+?)\*\*", r"\1", bruta)
        limpa = re.sub(r"`(.+?)`", r"\1", limpa)
        limpa = re.sub(r"^\s*[-*]\s+", "• ", limpa)
        limpa = limpa.replace("  ", "")
        linhas.append(limpa)
    return "\n".join(linhas).strip() + "\n"


def sections(rec: dict) -> dict:
    """Seções do assistente ao vivo, já normalizadas para a web."""
    estado = _estado(rec)
    if isinstance(estado, str):
        estado = parse_json(estado, {})

    acoes = []
    for item in estado.get("action_items") or []:
        if isinstance(item, dict):
            acoes.append({
                "description": item.get("description") or item.get("desc") or "",
                "assignee": item.get("assignee") or "",
            })
        else:
            acoes.append({"description": str(item), "assignee": ""})

    perguntas = []
    for item in estado.get("questions") or []:
        if isinstance(item, dict):
            perguntas.append({
                "question": item.get("question") or item.get("q") or "",
                "answer": item.get("answer") or item.get("a") or "",
                "resolved": bool(item.get("resolved")),
            })
        else:
            perguntas.append({"question": str(item), "answer": "", "resolved": False})

    return {
        "plan": [str(x) for x in (estado.get("plan") or [])],
        "tips": [str(x) for x in (estado.get("tips") or [])],
        "actionItems": acoes,
        "decisions": [str(x) for x in (estado.get("decisions") or [])],
        "questions": perguntas,
    }
