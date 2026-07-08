"""Digest proativo (standup automático): gera "feito / fazendo / bloqueios"
a partir do board, atividade recente e notas do dia, via provedor de IA."""
from __future__ import annotations

import logging

logger = logging.getLogger("maestro.digest")

_SYSTEM = (
    "Você é um facilitador que escreve um standup diário conciso para um "
    "desenvolvedor. Responda SEMPRE apenas com JSON válido, em português."
)

_PROMPT = (
    "Com base nos dados abaixo, escreva um standup objetivo.\n\n"
    "{context}\n\n"
    "Responda com JSON no formato exato:\n"
    "{{\n"
    '  "done": ["item concluído recentemente"],\n'
    '  "doing": ["item em andamento"],\n'
    '  "blockers": ["possível bloqueio ou risco"],\n'
    '  "summary": "resumo curto (1-2 frases) do momento do trabalho"\n'
    "}}"
)


def generate_digest(context: str) -> dict:
    """Gera o digest a partir de um resumo textual do estado do trabalho."""
    from maestro_local.ai.providers import build_chat_model
    from maestro_local.transcricoes.summarizer import _parse_json_response

    llm = build_chat_model(temperature=0.3)
    resp = llm.invoke([("system", _SYSTEM), ("user", _PROMPT.format(context=context))])
    parsed = _parse_json_response(getattr(resp, "content", str(resp)))
    if not isinstance(parsed, dict):
        raise ValueError("Resposta da IA não é um objeto JSON")

    def _strlist(v):
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
        return [str(v)] if v else []

    return {
        "done": _strlist(parsed.get("done")),
        "doing": _strlist(parsed.get("doing")),
        "blockers": _strlist(parsed.get("blockers")),
        "summary": str(parsed.get("summary") or ""),
    }
