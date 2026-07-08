"""Tradutor simples (estilo Google Tradutor) via provedor de IA ativo.

Traduz texto entre idiomas, com detecção automática do idioma de origem.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("maestro.translate")

# código -> nome do idioma (o "auto" pede detecção)
LANGUAGES = {
    "auto": "auto-detect",
    "pt": "Portuguese (Brazil)",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "ko": "Korean",
    "ru": "Russian",
}

_SYSTEM = (
    "You are a professional translator. Translate accurately and naturally, "
    "preserving tone, meaning and formatting (line breaks, lists). Do not add "
    "explanations. Reply with valid JSON only, no text outside the JSON."
)

_PROMPT = (
    "Translate the text below from {source} to {target}.\n"
    "If the source is 'auto-detect', identify the source language yourself.\n\n"
    "Text:\n\"\"\"\n{text}\n\"\"\"\n\n"
    "Reply with JSON in this exact shape:\n"
    "{{\n"
    '  "translated": "the translation only",\n'
    '  "detected_source": "the source language name you detected (or used)"\n'
    "}}"
)


def _lang_name(code: str) -> str:
    return LANGUAGES.get((code or "auto").lower(), code or "auto-detect")


def translate(text: str, source: str = "auto", target: str = "en") -> dict:
    """Traduz `text` de `source` (código; 'auto' detecta) para `target` (código)."""
    from maestro_local.ai.providers import build_chat_model
    from maestro_local.transcricoes.summarizer import _parse_json_response

    if not text.strip():
        raise ValueError("Texto vazio")
    llm = build_chat_model(temperature=0.2)
    user = _PROMPT.format(
        source=_lang_name(source), target=_lang_name(target), text=text.strip())
    resp = llm.invoke([("system", _SYSTEM), ("user", user)])
    parsed = _parse_json_response(getattr(resp, "content", str(resp)))
    if not isinstance(parsed, dict):
        # fallback: usa a resposta crua como tradução
        return {"translated": getattr(resp, "content", str(resp)).strip(),
                "detectedSource": _lang_name(source)}
    return {
        "translated": str(parsed.get("translated") or "").strip(),
        "detectedSource": str(parsed.get("detected_source") or _lang_name(source)),
    }
