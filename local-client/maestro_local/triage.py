"""Triagem de bugs por IA: recebe um relato/stacktrace e devolve uma
classificação estruturada (título, tipo, severidade, resumo, passos)."""
from __future__ import annotations

import logging

logger = logging.getLogger("maestro.triage")

_SYSTEM = (
    "Você é um engenheiro de software que faz triagem de bugs. "
    "Responda SEMPRE apenas com JSON válido, sem texto fora do JSON."
)

_PROMPT = (
    "Analise o relato de problema abaixo (pode conter stacktrace, logs ou "
    "descrição livre) e produza uma triagem. Responda em português do Brasil.\n\n"
    "Relato:\n\"\"\"\n{text}\n\"\"\"\n\n"
    "Responda com JSON no formato exato:\n"
    "{{\n"
    '  "title": "título curto e específico do bug (máx. 80 chars)",\n'
    '  "severity": "LOW|MEDIUM|HIGH|URGENT",\n'
    '  "type": "BUG",\n'
    '  "summary": "resumo do problema em 1-3 frases",\n'
    '  "probable_cause": "hipótese da causa provável, se houver",\n'
    '  "steps": ["passo sugerido 1", "passo sugerido 2"]\n'
    "}}"
)

_SEVERITY_TO_PRIORITY = {
    "LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH", "URGENT": "URGENT",
}


def triage_bug(text: str) -> dict:
    """Classifica um relato de bug via IA. Levanta exceção se o provedor não
    estiver configurado ou a IA falhar."""
    from maestro_local.ai.providers import build_chat_model
    from maestro_local.transcricoes.summarizer import _parse_json_response

    llm = build_chat_model(temperature=0.2)
    resp = llm.invoke([("system", _SYSTEM), ("user", _PROMPT.format(text=text.strip()))])
    parsed = _parse_json_response(getattr(resp, "content", str(resp)))
    if not isinstance(parsed, dict):
        raise ValueError("Resposta da IA não é um objeto JSON")

    severity = str(parsed.get("severity", "MEDIUM")).upper()
    if severity not in _SEVERITY_TO_PRIORITY:
        severity = "MEDIUM"
    steps = parsed.get("steps") or []
    if not isinstance(steps, list):
        steps = [str(steps)]
    return {
        "title": str(parsed.get("title") or "Bug sem título")[:80],
        "severity": severity,
        "priority": _SEVERITY_TO_PRIORITY[severity],
        "type": "BUG",
        "summary": str(parsed.get("summary") or ""),
        "probable_cause": str(parsed.get("probable_cause") or ""),
        "steps": [str(s) for s in steps],
    }


def build_task_description(text: str, triage: dict) -> str:
    """Monta a descrição da tarefa a partir do relato e da triagem."""
    parts = []
    if triage.get("summary"):
        parts.append(f"**Resumo:** {triage['summary']}")
    if triage.get("probable_cause"):
        parts.append(f"**Causa provável:** {triage['probable_cause']}")
    if triage.get("steps"):
        steps = "\n".join(f"- {s}" for s in triage["steps"])
        parts.append(f"**Passos sugeridos:**\n{steps}")
    parts.append(f"**Relato original:**\n```\n{text.strip()}\n```")
    return "\n\n".join(parts)
