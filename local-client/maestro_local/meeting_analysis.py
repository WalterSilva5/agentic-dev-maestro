"""Análise de reunião com o contexto do projeto (web e API).

O desktop já tem o copiloto ao vivo. Na web a reunião é analisada depois:
pega a transcrição + o retrato do projeto (board, atrasos, módulos, dailies) e
devolve dicas, plano, ações, decisões e perguntas.

Sem provedor de IA (ou se a chamada falhar) a análise cai num modo **heurístico**
que só usa fatos do contexto — nunca inventa: card parado há N dias, card
atrasado, último registro da daily.
"""
from __future__ import annotations

import re

MAX_TRANSCRIPT = 12000

_SYSTEM = """Você é copiloto de reunião. Recebe o CONTEXTO do projeto (board, atrasos,
progresso por módulo, dailies recentes) e a TRANSCRIÇÃO da reunião.

Devolva JSON válido:
{
  "tips": ["dica objetiva"],
  "plan": ["passo do plano"],
  "action_items": [{"description": "ação", "assignee": "responsável ou null"}],
  "decisions": ["decisão tomada"],
  "questions": [{"question": "pergunta", "answer": "", "resolved": false}]
}

Regras:
- As dicas devem ser CONCRETAS e ancoradas no contexto quando ele existir: cite o card,
  a coluna, o módulo ou o registro da daily. Não invente dados.
- Se a transcrição não disser algo, não complete por conta própria; use o contexto para apontar risco.
- Português do Brasil, frases curtas."""

_USER = """CONTEXTO DO PROJETO:
{context}

TRANSCRIÇÃO:
{transcript}

Responda somente com o JSON."""

_RE_CARD = re.compile(r"^- ([A-Z][A-Z0-9]+-\d+) · (.+?) — (.+?)(?: · (.*?))?(?: · parado há (\d+)d)?$")
_RE_ATRASO = re.compile(r"^- ([A-Z][A-Z0-9]+-\d+) · (.+?) — venceu (\d{2}/\d{2})(?: · (.*))?$")
_RE_MODULO = re.compile(r"([a-zà-ú][a-zà-ú\-]*) (\d+)/(\d+) \((\d+)%\)")


def _limpar(texto: str, limite: int = MAX_TRANSCRIPT) -> str:
    return " ".join((texto or "").split())[:limite]


def _via_llm(titulo: str, transcricao: str, contexto: str) -> dict:
    from maestro_local.ai.llm import invoke_json

    dados = invoke_json(
        [("system", _SYSTEM),
         ("user", _USER.format(context=contexto or "(sem contexto de projeto)",
                              transcript=_limpar(transcricao)))],
        temperature=0.2,
        timeout=90,
    )
    return {
        "tips": [str(x) for x in (dados.get("tips") or [])][:8],
        "plan": [str(x) for x in (dados.get("plan") or [])][:8],
        "actionItems": [
            {"description": str(a.get("description", "")), "assignee": a.get("assignee")}
            for a in (dados.get("action_items") or []) if isinstance(a, dict) and a.get("description")
        ][:10],
        "decisions": [str(x) for x in (dados.get("decisions") or [])][:8],
        "questions": [
            {"question": str(q.get("question", "")), "answer": "", "resolved": False}
            for q in (dados.get("questions") or []) if isinstance(q, dict) and q.get("question")
        ][:8],
    }


def _heuristica(contexto: str) -> dict:
    """Dicas a partir dos fatos do contexto (sem IA)."""
    tips: list[str] = []
    cards_parados = 0
    atrasados = 0
    modulos_risco: list[str] = []

    for linha in (contexto or "").splitlines():
        linha = linha.strip()
        # atraso primeiro: a linha também casa com o formato de "em andamento"
        achado = _RE_ATRASO.match(linha)
        if achado:
            atrasados += 1
            codigo, titulo, venceu, dono = achado.groups()
            tips.append(f"{codigo} venceu em {venceu} ({titulo[:60]}) — renegociar prazo ou redistribuir.")
            continue
        achado = _RE_CARD.match(linha)
        if achado:
            codigo, titulo, coluna, dono, dias = achado.groups()
            if dias and int(dias) >= 3:
                cards_parados += 1
                tips.append(
                    f"{codigo} está em {coluna} há {dias} dia(s) ({titulo[:60]}) — vale destravar na reunião."
                )
            continue
        # uma linha pode listar vários módulos: "auth 4/13 (31%) · financeiro 0/20 (0%)"
        for achado in _RE_MODULO.finditer(linha):
            nome, feito, total, pct = achado.groups()
            if int(total) >= 10 and int(pct) == 0:
                modulos_risco.append(f"{nome} ({feito}/{total})")

    if modulos_risco:
        tips.append("Módulos sem entrega registrada: " + ", ".join(modulos_risco[:4]) + ".")

    daily = None
    for linha in (contexto or "").splitlines():
        if re.match(r"^- \d{4}-\d{2}-\d{2} ·", linha.strip()):
            daily = linha.strip()[2:]
            break
    if daily:
        tips.append("Último registro da daily: " + daily[:180])

    plano = []
    if cards_parados:
        plano.append(f"Destravar os {cards_parados} card(s) parados há 3+ dias.")
    if atrasados:
        plano.append(f"Redistribuir/renegociar os {atrasados} card(s) atrasados.")
    plano.append("Fechar as ações combinadas na reunião e registrar na daily.")

    return {"tips": tips[:6], "plan": plano[:5], "actionItems": [], "decisions": [], "questions": []}


def analyze_meeting(*, title: str = "", transcript: str = "", context: str = "",
                    use_ai: bool = True) -> dict:
    """Analisa a reunião; devolve itens + de onde vieram (llm|heuristic)."""
    if use_ai:
        try:
            dados = _via_llm(title, transcript, context)
            if any(dados.values()):
                dados["engine"] = "llm"
                return dados
        except Exception:  # noqa: BLE001
            pass
    dados = _heuristica(context)
    dados["engine"] = "heuristic"
    return dados


def merge_live_state(estado: dict, analise: dict) -> dict:
    """Mescla a análise no estado do assistente ao vivo (sem duplicar)."""
    estado = dict(estado or {})

    def _unico(lista, novos):
        atual = [str(x) for x in (lista or [])]
        vistos = {x.strip().lower() for x in atual}
        for item in novos or []:
            texto = str(item).strip()
            if texto and texto.lower() not in vistos:
                atual.append(texto)
                vistos.add(texto.lower())
        return atual

    estado["tips"] = _unico(estado.get("tips"), analise.get("tips"))
    estado["plan"] = _unico(estado.get("plan"), analise.get("plan"))
    estado["decisions"] = _unico(estado.get("decisions"), analise.get("decisions"))

    acoes = list(estado.get("action_items") or [])
    vistos = {str(a.get("description", "")).strip().lower() if isinstance(a, dict) else str(a).lower()
              for a in acoes}
    for a in analise.get("actionItems") or []:
        desc = str(a.get("description", "")).strip()
        if desc and desc.lower() not in vistos:
            acoes.append({"description": desc, "assignee": a.get("assignee") or ""})
            vistos.add(desc.lower())
    estado["action_items"] = acoes

    perguntas = list(estado.get("questions") or [])
    existentes = {str(q.get("question", "")).strip().lower() if isinstance(q, dict) else str(q).lower()
                  for q in perguntas}
    for q in analise.get("questions") or []:
        texto = str(q.get("question", "")).strip()
        if texto and texto.lower() not in existentes:
            perguntas.append({"question": texto, "answer": "", "resolved": False})
            existentes.add(texto.lower())
    estado["questions"] = perguntas
    return estado
