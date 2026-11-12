"""Resumo do avanço (ontem → hoje) a partir dos docs de daily do vault.

Fonte: o diretório raiz de dailies configurado no projeto (`daily_docs_path`),
no padrão `YYYY-MM/DD-MM-YYYY - Daily - <tema>.md` (aceita também `MM-YYYY/`).
Sem diretório configurado (ou ilegível), o recurso fica indisponível.

O resumo em si usa IA (texto curto, 2-4 frases) com fallback **heurístico**
que só relata fatos — nunca inventa.
"""
from __future__ import annotations

import re
import time
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

MAX_BODY = 6000

_SYSTEM = """Você prepara o texto que o desenvolvedor vai FALAR na daily de hoje.
Recebe os docs de daily de ONTEM e de HOJE. Devolva o relato completo em
primeira pessoa ("trabalhei", "estou"), cobrindo CADA tópico/seção de cada
documento, um parágrafo ou frase por tópico, com os detalhes que importam
para explicar em reunião: o que foi feito, como, por quê, números de
testes/casos, o que falta e bloqueios. Não resuma para 2 frases: mantenha os
detalhes do documento — a pessoa vai falar cada item. Não invente nada além
dos documentos; se um dia estiver vazio, diga isso em meia frase e siga.
Texto puro, sem markdown, sem listas."""

_USER = """Docs de daily de ONTEM ({ontem}):
{corpo_ontem}

Docs de daily de HOJE ({hoje}):
{corpo_hoje}

Relate em primeira pessoa o que foi feito (texto puro, sem markdown, sem
lista), cobrindo todos os tópicos de cada documento com seus detalhes:"""

_SYSTEM_DIA = """Você prepara o texto que o desenvolvedor vai FALAR na daily.
Recebe o doc de daily de um dia. Devolva o relato completo em primeira pessoa
("trabalhei", "estou"), cobrindo CADA tópico/seção do documento, um parágrafo
ou frase por tópico, com os detalhes que importam para explicar em reunião:
o que foi feito, como, por quê, números de testes/casos, o que falta e
bloqueios. Não resuma para 2 frases: mantenha os detalhes do documento.
Não invente nada além do documento. Texto puro, sem markdown, sem listas."""

# cache curto: ler as métricas de novo não deve chamar a IA toda hora
_CACHE: dict[tuple, tuple[float, dict]] = {}
_TTL = 180


def _generated_path(raiz: Path, dia: date) -> Path:
    """Doc padronizado do resumo gerado, junto das dailies."""
    return raiz / f"generated-daily-{dia.strftime('%d-%m-%Y')}.md"


def _render_generated(dia: str, summary: str, fontes: list[str]) -> str:
    from datetime import datetime as _dt
    linhas = [
        f"# Resumo gerado por IA — {dia[8:10]}/{dia[5:7]}/{dia[0:4]}",
        "",
        f"> Gerado automaticamente pelo Relay em {_dt.now().strftime('%d/%m/%Y %H:%M')}.",
        "> Edite à vontade — este arquivo não é lido de volta como fonte.",
        "",
        "## Resumo",
        "",
        summary,
        "",
        "## Fonte",
        "",
    ]
    linhas.extend(f"- {f}" for f in fontes)
    linhas.append("")
    return "\n".join(linhas)


def _arquivos_do_dia(raiz: Path, dia: date) -> list[Path]:
    """`DD-MM-YYYY - Daily - *.md` dentro de `YYYY-MM/` (ou legado `MM-YYYY/`)."""
    prefixo = dia.strftime("%d-%m-%Y")
    achados: list[Path] = []
    for sub in (dia.strftime("%Y-%m"), dia.strftime("%m-%Y")):
        pasta = raiz / sub
        if not pasta.is_dir():
            continue
        achados.extend(sorted(p for p in pasta.glob(f"{prefixo}*.md") if p.is_file()))
    return achados


def _limpar_md(texto: str, limite: int) -> str:
    texto = re.sub(r"[ \t]+", " ", texto or "")
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    return texto[:limite]


def _normalizar(txt: str) -> str:
    import unicodedata

    sem_acento = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


_GENERICOS = {
    "itens trabalhados",
    "pendencias",
    "pendencias / proximos passos",
    "proximos passos",
    "documentacao",
}


def _blocos(entries) -> list[tuple[str, list[str]]]:
    """Seções ## / ### com suas linhas de conteúdo: [(titulo, [linhas])]."""
    blocos: list[tuple[str, list[str]]] = []
    for e in entries or []:
        titulo, linhas = None, []
        for raw in (e.body or "").splitlines():
            s = raw.strip()
            m = re.match(r"^#{2,3}\s+(.*\S)", s)
            if m:
                if titulo is not None:
                    blocos.append((titulo, linhas))
                titulo = re.sub(r"[*_`\[\]()#]", "", m.group(1)).strip()
                titulo = re.sub(r"\s+", " ", titulo)[:80]
                linhas = []
            elif titulo is not None and s and not s.startswith("#"):
                linhas.append(s)
        if titulo is not None:
            blocos.append((titulo, linhas))
    return blocos


def _limpar_detalhe(linhas: list[str], max_len: int = 650) -> str:
    """Primeiro parágrafo da seção. Corta no fim de frase, nunca no meio."""
    partes: list[str] = []
    for s in linhas:
        if not s.strip():
            break
        partes.append(re.sub(r"^([-*•]|\d+[.)])\s+", "", s.strip()))
    texto = re.sub(r"[*_`]", "", " ".join(partes)).strip()
    texto = re.sub(r"\s+", " ", texto)
    if len(texto) <= max_len:
        return texto
    corte = texto[:max_len]
    for sep in (". ", "! ", "? "):
        i = corte.rfind(sep)
        if i > max_len // 2:
            return corte[: i + 1].rstrip()
    return corte.rsplit(" ", 1)[0] + "…"


def _itens(entries, max_itens: int = 50, max_detalhe: int = 900) -> list[tuple[str, str]]:
    """[(tópico, detalhe)] — só entra tópico com conteúdo de verdade."""
    vistos: set[str] = set()
    itens: list[tuple[str, str]] = []
    for titulo, linhas in _blocos(entries):
        norm = _normalizar(titulo)
        if not titulo or norm in _GENERICOS or norm.startswith("perguntas"):
            continue
        if len(titulo.split()) < 2:
            continue
        if norm.split(" ", 1)[0] in ("ontem", "hoje"):
            continue
        detalhe = _limpar_detalhe(linhas, max_detalhe)
        if not detalhe or titulo in vistos:
            continue
        vistos.add(titulo)
        itens.append((titulo, detalhe))
        if len(itens) >= max_itens:
            break
    return itens


def _topicos(entries, max_topicos: int = 6, max_len: int = 80) -> list[str]:
    """Tópicos do dia = cabeçalhos ## / ### dos docs (o que o dia tratou)."""
    return [t for t, _ in _itens(entries, max_itens=max_topicos)][:max_topicos]


def _sentencas_topicos(itens: list[tuple[str, str]]) -> list[str]:
    """Uma frase por tópico: ['Tópico: detalhe.', ...]."""
    frases = []
    for titulo, detalhe in itens:
        s = f"{titulo}: {detalhe}".rstrip()
        if not s.endswith((".", "!", "?", "…", ":")):
            s += "."
        frases.append(s)
    return frases


def _entradas_do_dia(raiz: Path, dia: date, limite: int = MAX_BODY) -> list:
    """Cada doc do dia vira um "registro" (kind DOC) para o resumo."""
    partes, usado = [], 0
    for path in _arquivos_do_dia(raiz, dia):
        try:
            corpo = _limpar_md(path.read_text(encoding="utf-8", errors="replace"),
                               limite - usado)
        except OSError:
            continue
        if not corpo:
            continue
        partes.append(corpo)
        usado += len(corpo)
        if usado >= limite:
            break
    if not partes:
        return []
    return [SimpleNamespace(kind="DOC", body="\n\n---\n\n".join(partes), author=None,
                            minutes=None, task_code=None)]


def _texto(entries, limite: int = MAX_BODY) -> str:
    blocos = []
    for e in entries or []:
        cabeca = f"[{e.kind or 'DOC'}]"
        if getattr(e, "author", None):
            cabeca += f" {e.author}"
        if getattr(e, "task_code", None):
            cabeca += f" ({e.task_code})"
        corpo = " ".join((e.body or "").split())
        blocos.append(f"{cabeca} {corpo}".strip())
    return "\n".join(blocos)[:limite]


def _fatos(entries) -> dict:
    por_tipo: dict[str, int] = {}
    minutos = 0
    for e in entries or []:
        por_tipo[e.kind or "DOC"] = por_tipo.get(e.kind or "DOC", 0) + 1
        minutos += e.minutes or 0
    return {
        "registros": len(entries or []),
        "tipos": por_tipo,
        "minutos": minutos,
        "topicos": _topicos(entries),
    }


def _heuristica(f_ontem: dict, f_hoje: dict, itens_ontem, itens_hoje) -> str:
    """Resumo em primeira pessoa; cada tópico vira uma frase com detalhe."""

    def parte(rotulo: str, verbo: str, fatos: dict, itens: list) -> str:
        if itens:
            return f"{rotulo} {verbo} " + " ".join(_sentencas_topicos(itens))
        if fatos["registros"]:
            return f"{rotulo}: {fatos['registros']} registro(s)."
        return f"{rotulo}: sem registros."

    return (parte("Ontem", "trabalhei em", f_ontem, itens_ontem) + " "
            + parte("Hoje", "estou em", f_hoje, itens_hoje))


def _via_llm(ontem_txt: str, hoje_txt: str, ontem: str, hoje: str) -> str:
    from relay.ai.llm import invoke_text

    texto = invoke_text(
        [("system", _SYSTEM),
         ("user", _USER.format(ontem=ontem, corpo_ontem=ontem_txt or "(sem registros)",
                               hoje=hoje, corpo_hoje=hoje_txt or "(sem registros)"))],
        temperature=0.3,
        timeout=180,
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
        "summary": _heuristica(f_ontem, f_hoje,
                               _itens(entries_ontem, max_detalhe=900),
                               _itens(entries_hoje, max_detalhe=900)),
        "engine": "heuristic",
        "yesterday": {"date": ontem, **f_ontem,
                      "itens": [{"topico": t, "detalhe": d}
                                for t, d in _itens(entries_ontem, max_detalhe=900)]},
        "today": {"date": hoje, **f_hoje,
                  "itens": [{"topico": t, "detalhe": d}
                            for t, d in _itens(entries_hoje, max_detalhe=900)]},
    }


_USER_DIA = """Doc(s) de daily de {dia}:
{corpo}

Relate em primeira pessoa o que foi feito (texto puro, sem markdown, sem
lista), cobrindo todos os tópicos do documento com seus detalhes:"""


def summarize_day(*, dia: str, entries, use_ai: bool = True) -> dict:
    """Resumo de um único dia (usado pelo acordeão por dia)."""
    fatos = _fatos(entries)
    corpo = _texto(entries)
    if not fatos["registros"]:
        return {
            "summary": "",
            "engine": "empty",
            "date": dia,
            "registros": 0,
            "tipos": {},
            "minutos": 0,
        }
    if use_ai:
        try:
            from relay.ai.llm import invoke_text

            texto = invoke_text(
                [("system", _SYSTEM_DIA), ("user", _USER_DIA.format(dia=dia, corpo=corpo))],
                temperature=0.3,
                timeout=180,
            )
            texto = " ".join(str(texto or "").split())
            if texto:
                return {
                    "summary": texto,
                    "engine": "llm",
                    "date": dia,
                    **fatos,
                }
        except Exception:  # noqa: BLE001
            pass
    itens = _itens(entries)
    if itens:
        texto = "Trabalhei em " + " ".join(_sentencas_topicos(itens))
    else:
        texto = f"{fatos['registros']} registro(s)" if fatos["registros"] else ""
    return {
        "summary": texto,
        "engine": "heuristic",
        "date": dia,
        **fatos,
        "itens": [{"topico": t, "detalhe": d} for t, d in itens],
    }


def project_day_summary(session, project_id: int, dia: str, *, refresh: bool = False,
                        use_ai: bool = True) -> dict:
    """Resumo dos docs de um dia (YYYY-MM-DD) do diretório configurado."""
    from relay.db.models import Project

    try:
        alvo = date.fromisoformat(dia)
    except ValueError:
        raise ValueError(f"data inválida (use AAAA-MM-DD): {dia}")
    chave = (project_id, "dia", dia)
    if not refresh and chave in _CACHE:
        ts, dados = _CACHE[chave]
        if time.monotonic() - ts < _TTL:
            return {"projectId": project_id, "cached": True, **dados}

    project = session.query(Project).filter(Project.id == project_id).first()
    raiz_txt = (getattr(project, "daily_docs_path", "") or "").strip()
    raiz = Path(raiz_txt)
    if not raiz_txt or not raiz.is_dir():
        dados = {
            "summary": "",
            "engine": "empty",
            "configured": False,
            "reason": "not_configured" if not raiz_txt else "not_found",
            "date": dia,
            "registros": 0,
            "tipos": {},
            "minutos": 0,
            "saved": False,
            "savedFile": None,
        }
    else:
        dados = summarize_day(dia=dia, entries=_entradas_do_dia(raiz, alvo), use_ai=use_ai)
        dados["configured"] = True
        gerado = _generated_path(raiz, alvo)
        dados["saved"] = gerado.is_file()
        dados["savedFile"] = gerado.name if gerado.is_file() else None
    _CACHE[chave] = (time.monotonic(), dados)
    return {"projectId": project_id, "cached": False, **dados}


def save_day_summary(session, project_id: int, dia: str, *, use_ai: bool = True) -> dict:
    """Gera o resumo do dia e persiste em `generated-daily-DD-MM-YYYY.md`.

    Sobrescreve o arquivo se ele já existir (é um artefato gerado).
    """
    from relay.db.models import Project

    try:
        alvo = date.fromisoformat(dia)
    except ValueError:
        raise ValueError(f"data inválida (use AAAA-MM-DD): {dia}")

    project = session.query(Project).filter(Project.id == project_id).first()
    raiz_txt = (getattr(project, "daily_docs_path", "") or "").strip()
    raiz = Path(raiz_txt)
    if not raiz_txt or not raiz.is_dir():
        raise ValueError("diretório de docs de daily não configurado ou não encontrado")

    arquivos = _arquivos_do_dia(raiz, alvo)
    if not arquivos:
        raise ValueError(f"sem docs de daily para {dia}")
    dados = summarize_day(dia=dia, entries=_entradas_do_dia(raiz, alvo), use_ai=use_ai)
    destino = _generated_path(raiz, alvo)
    destino.write_text(
        _render_generated(dia, dados["summary"], [p.name for p in arquivos]),
        encoding="utf-8",
    )
    dados.update({"configured": True, "saved": True, "savedFile": destino.name})
    _CACHE[(project_id, "dia", dia)] = (time.monotonic(), dados)
    return {"projectId": project_id, "cached": False, "file": destino.name, **dados}


def project_advance(session, project_id: int, *, refresh: bool = False,
                    use_ai: bool = True) -> dict:
    """Lê os docs de ontem/hoje no diretório configurado e resume (com cache curto)."""
    from relay.db.models import Project

    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    s_ontem, s_hoje = ontem.isoformat(), hoje.isoformat()
    chave = (project_id, s_ontem, s_hoje)
    if not refresh and chave in _CACHE:
        ts, dados = _CACHE[chave]
        if time.monotonic() - ts < _TTL:
            return {"projectId": project_id, "cached": True, **dados}

    project = session.query(Project).filter(Project.id == project_id).first()
    raiz_txt = (getattr(project, "daily_docs_path", "") or "").strip()
    raiz = Path(raiz_txt)
    dados: dict
    if not raiz_txt or not raiz.is_dir():
        dados = {
            "summary": "",
            "engine": "empty",
            "configured": False,
            "reason": "not_configured" if not raiz_txt else "not_found",
            "yesterday": {"date": s_ontem, "registros": 0, "tipos": {}, "minutos": 0},
            "today": {"date": s_hoje, "registros": 0, "tipos": {}, "minutos": 0},
        }
    else:
        dados = summarize_advance(
            ontem=s_ontem, hoje=s_hoje,
            entries_ontem=_entradas_do_dia(raiz, ontem),
            entries_hoje=_entradas_do_dia(raiz, hoje),
            use_ai=use_ai,
        )
        dados["configured"] = True
    _CACHE[chave] = (time.monotonic(), dados)
    return {"projectId": project_id, "cached": False, **dados}
