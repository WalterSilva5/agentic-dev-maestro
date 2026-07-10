"""Prática de inglês conversacional (simples, porém eficaz).

Um parceiro de conversa por IA que: mantém o inglês no nível escolhido, faz uma
pergunta a cada turno, corrige com gentileza (em português), sugere um jeito mais
natural de dizer, oferece um exemplo de boa resposta e destaca vocabulário útil
com pronúncia "reescrita" em português (ex.: outside → áutsáid).

Ideias absorvidas do wsi-talk, sem o peso (sem créditos, papéis, microserviços).
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field

logger = logging.getLogger("maestro.english")


class _OpeningOut(BaseModel):
    reply: str = ""
    suggestion: str = ""


class _VocabItem(BaseModel):
    word: str = ""
    respell: str = ""
    meaning: str = ""


class _TurnOut(BaseModel):
    reply: str = ""
    feedback: str = ""
    correction: str = ""
    suggestion: str = ""
    vocab: list[_VocabItem] = Field(default_factory=list)

LEVELS = {
    "BEGINNER": "beginner (A1-A2): short, simple sentences; basic vocabulary; mostly present tense; speak slowly and clearly",
    "INTERMEDIATE": "intermediate (B1-B2): everyday fluent English; some phrasal verbs and idioms; varied tenses",
    "ADVANCED": "advanced (C1-C2): rich, nuanced, native-like English; idiomatic; challenge the learner",
    "FREE": "adapt to the level the learner demonstrates in their messages",
}

_SYSTEM = (
    "You are a warm, encouraging English conversation partner and coach for a "
    "Brazilian Portuguese speaker. You chat in English at the requested level and "
    "gently coach the learner. You ALWAYS reply with valid JSON only, no text "
    "outside the JSON."
)

_TURN_INSTRUCTIONS = (
    "Level: {level_desc}\n"
    "Topic: {topic}\n\n"
    "The learner just said:\n\"\"\"\n{message}\n\"\"\"\n\n"
    "Continue the conversation. Respond with JSON in this EXACT shape:\n"
    "{{\n"
    '  "reply": "your natural English response (1-3 sentences) reacting to what '
    'they said, ending with ONE follow-up question, at the given level",\n'
    '  "feedback": "a short, kind note IN BRAZILIAN PORTUGUESE about any grammar/'
    'vocabulary mistakes in their message; empty string if it was already good",\n'
    '  "correction": "a corrected, more natural version of their message in '
    'English; empty string if no change needed",\n'
    '  "suggestion": "an example of a good answer the learner could give to your '
    'follow-up question, in English (a hint)",\n'
    '  "vocab": [{{"word": "englishWord", "respell": "pronúncia aproximada em '
    'português", "meaning": "significado em português"}}]\n'
    "}}\n"
    "Include 0-3 genuinely useful words in vocab (from your reply or theirs). "
    "Keep everything at the learner's level."
)

_OPENING_INSTRUCTIONS = (
    "Level: {level_desc}\n"
    "Topic: {topic}\n\n"
    "Start a friendly conversation to practice English. Respond with JSON:\n"
    "{{\n"
    '  "reply": "a warm greeting + ONE simple opening question at the level",\n'
    '  "suggestion": "an example of a good answer to your question, in English"\n'
    "}}"
)


def _level_desc(level: str) -> str:
    return LEVELS.get((level or "FREE").upper(), LEVELS["FREE"])


def _clean_vocab(raw) -> list[dict]:
    out = []
    for v in (raw or []):
        if isinstance(v, dict) and str(v.get("word", "")).strip():
            out.append({
                "word": str(v.get("word", "")).strip(),
                "respell": str(v.get("respell", "")).strip(),
                "meaning": str(v.get("meaning", "")).strip(),
            })
    return out[:3]


def start(level: str, topic: str = "") -> dict:
    """Primeira fala da IA para abrir a conversa."""
    from maestro_local.ai.llm import invoke_json

    user = _OPENING_INSTRUCTIONS.format(
        level_desc=_level_desc(level), topic=topic.strip() or "free conversation")
    parsed = invoke_json([("system", _SYSTEM), ("user", user)],
                         schema=_OpeningOut, temperature=0.6)
    if not isinstance(parsed, dict):
        parsed = {}
    return {
        "reply": str(parsed.get("reply") or "Hi! How are you today?"),
        "suggestion": str(parsed.get("suggestion") or ""),
    }


def converse(level: str, topic: str, history: list[dict], message: str) -> dict:
    """Um turno da conversa. `history`: lista de {role: 'user'|'assistant', text}."""
    from maestro_local.ai.llm import invoke_json

    msgs = [("system", _SYSTEM)]
    for h in (history or [])[-12:]:  # janela curta de contexto
        role = "assistant" if h.get("role") == "assistant" else "user"
        msgs.append((role, str(h.get("text") or "")))
    msgs.append(("user", _TURN_INSTRUCTIONS.format(
        level_desc=_level_desc(level),
        topic=(topic or "").strip() or "free conversation",
        message=message.strip())))
    parsed = invoke_json(msgs, schema=_TurnOut, temperature=0.6)
    if not isinstance(parsed, dict):
        raise ValueError("Resposta da IA não é um objeto JSON")
    return {
        "reply": str(parsed.get("reply") or ""),
        "feedback": str(parsed.get("feedback") or ""),
        "correction": str(parsed.get("correction") or ""),
        "suggestion": str(parsed.get("suggestion") or ""),
        "vocab": _clean_vocab(parsed.get("vocab")),
    }
