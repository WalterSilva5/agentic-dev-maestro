"""Base de conhecimento (2º cérebro): recuperação simples por palavras-chave
sobre as notas e resposta da IA com citações (RAG-lite, sem vetor)."""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("maestro.kb")

_STOP = {
    "a", "o", "e", "de", "da", "do", "que", "com", "para", "por", "os", "as",
    "um", "uma", "no", "na", "em", "the", "of", "to", "and", "is", "in", "on",
}

_SYSTEM = (
    "Você responde perguntas usando SOMENTE as notas fornecidas como contexto. "
    "Se a resposta não estiver nas notas, diga que não encontrou. Cite os títulos "
    "das notas usadas. Responda em português, em Markdown."
)


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z0-9À-ÿ]{3,}", (text or "").lower())
            if w not in _STOP}


def retrieve(notes: list[dict], question: str, top_k: int = 5) -> list[dict]:
    """Pontua notas por sobreposição de palavras com a pergunta. `notes`:
    lista de {id, title, body}. Retorna as top_k com score > 0."""
    q = _tokens(question)
    if not q:
        return notes[:top_k]
    scored = []
    for n in notes:
        hay = _tokens(f"{n.get('title', '')} {n.get('body', '')}")
        score = len(q & hay)
        # peso extra para termos no título
        score += len(q & _tokens(n.get("title", "")))
        if score > 0:
            scored.append((score, n))
    scored.sort(key=lambda x: -x[0])
    return [n for _, n in scored[:top_k]]


def answer(notes: list[dict], question: str) -> dict:
    """Responde à pergunta usando as notas mais relevantes via IA."""
    from maestro_local.ai.llm import invoke_text

    relevant = retrieve(notes, question)
    if not relevant:
        return {"answer": "Não encontrei notas relevantes para responder.", "sources": []}

    context = "\n\n".join(
        f"### {n.get('title', 'Sem título')}\n{(n.get('body') or '')[:2000]}"
        for n in relevant
    )
    user = f"Notas:\n{context}\n\nPergunta: {question}"
    text = invoke_text([("system", _SYSTEM), ("user", user)], temperature=0.2)
    return {
        "answer": text,
        "sources": [{"id": n.get("id"), "title": n.get("title")} for n in relevant],
    }


def backlinks(notes: list[dict]) -> dict:
    """Mapeia título -> lista de ids que o referenciam via [[título]]."""
    by_title = {(n.get("title") or "").strip().lower(): n for n in notes}
    links: dict[str, list] = {}
    for n in notes:
        for ref in re.findall(r"\[\[([^\]]+)\]\]", n.get("body") or ""):
            key = ref.strip().lower()
            if key in by_title:
                target = by_title[key]
                links.setdefault(target["id"], []).append(
                    {"id": n["id"], "title": n.get("title")})
    return links
