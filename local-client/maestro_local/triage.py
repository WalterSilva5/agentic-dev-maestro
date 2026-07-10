"""Triagem de bugs por IA: recebe um relato/stacktrace e devolve uma
classificação estruturada (título, tipo, severidade, resumo, passos)."""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field

logger = logging.getLogger("maestro.triage")


class _TriageOut(BaseModel):
    title: str = ""
    severity: str = "MEDIUM"
    type: str = "BUG"
    summary: str = ""
    probable_cause: str = ""
    steps: list[str] = Field(default_factory=list)


class _RetroAction(BaseModel):
    title: str = ""


class _RetroOut(BaseModel):
    well: list[str] = Field(default_factory=list)
    badly: list[str] = Field(default_factory=list)
    actions: list[_RetroAction] = Field(default_factory=list)

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
    from maestro_local.ai.llm import invoke_json

    parsed = invoke_json([("system", _SYSTEM), ("user", _PROMPT.format(text=text.strip()))],
                         schema=_TriageOut, temperature=0.2)
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


_RETRO_SYSTEM = (
    "Você é um facilitador ágil conduzindo a retrospectiva de uma sprint. "
    "Responda SEMPRE apenas com JSON válido, sem texto fora do JSON. Em português."
)

_RETRO_PROMPT = (
    "Com base nos dados da sprint abaixo, gere uma retrospectiva objetiva.\n\n"
    "{context}\n\n"
    "Responda com JSON no formato exato:\n"
    "{{\n"
    '  "well": ["o que foi bem 1", "o que foi bem 2"],\n'
    '  "badly": ["o que foi mal / pode melhorar 1", "..."],\n'
    '  "actions": [{{"title": "ação de melhoria acionável"}}]\n'
    "}}"
)


def generate_sprint_retro(context: str) -> dict:
    """Gera a retrospectiva de uma sprint via IA a partir de um resumo textual."""
    from maestro_local.ai.llm import invoke_json

    parsed = invoke_json([("system", _RETRO_SYSTEM),
                          ("user", _RETRO_PROMPT.format(context=context))],
                         schema=_RetroOut, temperature=0.4)
    if not isinstance(parsed, dict):
        raise ValueError("Resposta da IA não é um objeto JSON")

    def _strlist(v):
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
        return [str(v)] if v else []

    actions = []
    for a in (parsed.get("actions") or []):
        if isinstance(a, dict):
            title = str(a.get("title") or "").strip()
        else:
            title = str(a).strip()
        if title:
            actions.append({"title": title[:255]})
    return {
        "well": _strlist(parsed.get("well")),
        "badly": _strlist(parsed.get("badly")),
        "actions": actions,
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
