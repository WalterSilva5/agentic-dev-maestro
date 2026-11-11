"""Resumo do avanço (ontem → hoje) a partir dos docs de daily do projeto.

O painel de métricas mostra o que andou: pega os registros de daily de ontem
e de hoje e resume com IA (texto curto, 2-4 frases). Sem provedor de IA — ou
se a chamada falhar — cai num modo **heurístico** que só relata fatos (nunca
inventa): quantos registros, tipos e minutos por dia.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

MAX_BODY = 6000

_SYSTEM = """Você resume o avanço de um projeto a partir dos registros de daily
de ONTEM e de HOJE. Responda em português do Brasil, 2 a 4 frases curtas,
direto ao ponto: o que avançou ontem, o que está em curso hoje e, se houver,
bloqueios ou decisões. Não invente nada além dos registros; se um dia estiver
vazio, diga isso em meia frase e siga."""

_USER = """Registros de ONTEM ({ontem}):
{corpo_ontem}

Registros de HOJE ({hoje}):
{corpo_hoje}

Resuma o avanço (texto puro, sem markdown, sem lista):"""

# cache curto: ler as métricas de novo não deve chamar a IA toda hora
_CACHE: dict[tuple, tuple[float, dict]] = {}
_TTL = 180


def _texto(entries, limite: int = MAX_BODY) -> str:
    blocos = []
    for e in entries or []:
        cabeca = f"[{e.kind or 'WORK'}]"
        if e.author:
            cabeca += f" {e.author}"
        if e.task_code:
            cabeca += f" ({e.task_code})"
        corpo = " ".join((e.body or "").split())
        blocos.append(f"{cabeca} {corpo}".strip())
    return "\n".join(blocos)[:limite]


def _fatos(entries) -> dict:
    por_tipo: dict[str, int] = {}
    minutos = 0
    for e in entries or []:
        por_tipo[e.kind or "WORK"] = por_tipo.get(e.kind or "WORK", 0) + 1
        minutos += e.minutes or 0
    return {"registros": len(entries or []), "tipos": por_tipo, "minutos": minutos}


def _heuristica(ontem_txt: str, hoje_txt: str, f_ontem: dict, f_hoje: dict) -> str:
    def parte(rotulo: str, fatos: dict) -> str:
        if not fatos["registros"]:
            return f"{rotulo}: sem registros"
        tipos = ", ".join(f"{v} {k.lower()}" for k, v in sorted(fatos["tipos"].items()))
        extra = f", {fatos['minutos']}min" if fatos["minutos"] else ""
        return f"{rotulo}: {fatos['registros']} registro(s) ({tipos}{extra})"
    return parte("Ontem", f_ontem) + ". " + parte("Hoje", f_hoje) + "."


def _via_llm(ontem_txt: str, hoje_txt: str, ontem: str, hoje: str) -> str:
    from relay.ai.llm import invoke_text

    texto = invoke_text(
        [("system", _SYSTEM),
         ("user", _USER.format(ontem=ontem, corpo_ontem=ontem_txt or "(sem registros)",
                               hoje=hoje, corpo_hoje=hoje_txt or "(sem registros)"))],
        temperature=0.3,
        timeout=60,
    )
    return " ".join(str(texto or "").split())


def summarize_advance(*, ontem: str, hoje: str, entries_ontem, entries_hoje,
                      use_ai: bool = True) -> dict:
    """Resume o avanço ontem → hoje. Devolve `summary` + `engine`."""
    f_ontem, f_hoje = _fatos(entries_ontem), _fatos(entries_hoje)
    if not f_ontem["registros"] and not f_hoje["registros"]:
        return {
            "summary": "",
            "engine": "empty",
            "yesterday": {"date": ontem, **f_ontem},
            "today": {"date": hoje, **f_hoje},
        }
    if use_ai:
        try:
            texto = _via_llm(_texto(entries_ontem), _texto(entries_hoje), ontem, hoje)
            if texto:
                return {
                    "summary": texto,
                    "engine": "llm",
                    "yesterday": {"date": ontem, **f_ontem},
                    "today": {"date": hoje, **f_hoje},
                }
        except Exception:  # noqa: BLE001
            pass
    return {
        "summary": _heuristica(_texto(entries_ontem), _texto(entries_hoje), f_ontem, f_hoje),
        "engine": "heuristic",
        "yesterday": {"date": ontem, **f_ontem},
        "today": {"date": hoje, **f_hoje},
    }


def project_advance(session, project_id: int, *, refresh: bool = False,
                    use_ai: bool = True) -> dict:
    """Busca os dailies de ontem/hoje e resume (com cache curto)."""
    from relay.db.models import ProjectDailyEntry

    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    s_ontem, s_hoje = ontem.isoformat(), hoje.isoformat()
    chave = (project_id, s_ontem, s_hoje)
    if not refresh and chave in _CACHE:
        ts, dados = _CACHE[chave]
        if time.monotonic() - ts < _TTL:
            return {"projectId": project_id, "cached": True, **dados}

    ent = (
        session.query(ProjectDailyEntry)
        .filter(ProjectDailyEntry.project_id == project_id,
                ProjectDailyEntry.date.in_([s_ontem, s_hoje]))
        .order_by(ProjectDailyEntry.date, ProjectDailyEntry.sort_order)
        .all()
    )
    dados = summarize_advance(
        ontem=s_ontem, hoje=s_hoje,
        entries_ontem=[e for e in ent if e.date == s_ontem],
        entries_hoje=[e for e in ent if e.date == s_hoje],
        use_ai=use_ai,
    )
    _CACHE[chave] = (time.monotonic(), dados)
    return {"projectId": project_id, "cached": False, **dados}
