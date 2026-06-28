"""Sumarização de transcrições via IA, reusando o provedor do Maestro."""
from __future__ import annotations

import json
import logging

from maestro_local.ai.providers import build_chat_model

logger = logging.getLogger("maestro.cronista.ai")

MAX_CHUNK_WORDS = 2000
OVERLAP_WORDS = 200


def _chunk_text(text: str, max_words: int = MAX_CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks, start = [], 0
    while start < len(words):
        end = start + max_words
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks


def _invoke(llm, system_prompt: str, user_prompt: str) -> str:
    resp = llm.invoke([("system", system_prompt), ("user", user_prompt)])
    return getattr(resp, "content", str(resp))


def _parse_json_response(response: str) -> dict:
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("JSON inválido da IA: %s", e)
        return {"raw_response": response, "parse_error": str(e)}


def summarize(text: str, system_prompt: str, user_prompt_template: str, **template_kwargs) -> dict:
    """Gera resumo estruturado. Two-pass para textos longos."""
    llm = build_chat_model(temperature=0.2)
    chunks = _chunk_text(text)

    if len(chunks) == 1:
        user_prompt = user_prompt_template.format(transcript=text, content=text, **template_kwargs)
        return _parse_json_response(_invoke(llm, system_prompt, user_prompt))

    logger.info("Texto longo (%d chunks), two-pass...", len(chunks))
    partials = []
    for i, chunk in enumerate(chunks):
        up = user_prompt_template.format(transcript=chunk, content=chunk, **template_kwargs)
        partials.append(_invoke(llm, system_prompt, up))

    combined = "\n\n---\n\n".join(partials)
    synthesis = (
        "Os seguintes são resumos parciais de uma mesma sessão. "
        "Combine-os em um único JSON coerente, eliminando duplicatas "
        "e mantendo todos os pontos únicos.\n\n" + combined
    )
    return _parse_json_response(_invoke(llm, system_prompt, synthesis))
