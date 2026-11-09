"""Report semanal do time: números do board + a leitura do líder.

Duas camadas:

- **automático** — quem entregou o quê na semana, o que está em aberto, atrasos,
  revisões e a distribuição de carga (tudo do board);
- **manual** — os campos que só o líder sabe ("como está trabalhando",
  serviço/apoio, pontos de atenção, próximo passo), guardados em `TeamNote`.

O markdown gerado segue o formato dos acompanhamentos do vault
(`lideranca/gestao/acompanhamento-semanal-equipe-*.md`), com versão nominal e
anonimizada (Pessoa A/B/C) para apresentação ampla.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta

from relay.dimensions import MODULES
from relay.stages import primary_group
from relay.timeutil import data_local, limites_utc

ANONIMOS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# "PR #8910", "PR 8910", "pullrequest/8910" e "#8910" em comentários
_PRR = r"\bPR\s*#?\s*(\d{2,6})\b|pullrequest/(\d{2,6})|#(\d{4,6})\b"
import re as _re

_PR_RE = _re.compile(_PRR)


def _sugestao_servico(servico: dict, entregues: int) -> str:
    """Texto pronto para o campo 'Serviço/apoio' (o líder edita se quiser)."""
    partes = []
    cards = sorted(servico.get("cards", {}))
    if servico.get("reviews"):
        alvo = f" ({', '.join(cards[:6])}{'…' if len(cards) > 6 else ''})" if cards else ""
        partes.append(f"Revisou {servico['reviews']} card(s){alvo}")
    if servico.get("prs"):
        partes.append("PRs citados: " + ", ".join(f"#{p}" for p in sorted(servico["prs"])))
    if entregues:
        partes.append(f"Entregou {entregues} card(s)")
    return " · ".join(partes)


def week_bounds(ref: date | None = None) -> tuple[date, date]:
    """Segunda e domingo da semana de `ref` (padrão: hoje)."""
    ref = ref or date.today()
    segunda = ref - timedelta(days=ref.weekday())
    return segunda, segunda + timedelta(days=6)


def _modulo(task) -> str:
    chave = primary_group([lb.name for lb in task.labels])
    return MODULES.get(chave, chave) if chave != "sem-modulo" else ""


def _importado(task, quando) -> bool:
    """Conclusão veio da importação (data não representa entrega de verdade).

    O sync grava `descrição = "Importado do Azure #..."` e, no passado, o
    auto-arquivo preenchia `done_at` com a data do import — contar isso como
    entrega da semana inflaria o relatório.
    """
    if quando is None:
        return True
    if not (task.description or "").startswith("Importado do Azure"):
        return False
    criado = data_local(_dt(task.created_at))
    return bool(criado and criado == data_local(quando))


def _dt(valor) -> datetime | None:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.fromisoformat(str(valor))
    except ValueError:
        return None


def compute_weekly(session, project, ref: date | None = None) -> dict:
    """Números da semana por membro (+ anotações já salvas)."""
    from relay.db.models import (
        BoardColumn,
        Comment,
        Member,
        Task,
        TeamNote,
    )

    inicio, fim = week_bounds(ref)
    hoje = date.today()

    cols = (
        session.query(BoardColumn)
        .filter(BoardColumn.project_id == project.id)
        .order_by(BoardColumn.order)
        .all()
    )
    por_coluna = {c.id: c for c in cols}
    done_ids = {c.id for c in cols if c.is_done}
    primeira_ordem = cols[0].order if cols else 0

    tasks = (
        session.query(Task)
        .filter(
            Task.project_id == project.id,
            Task.deleted_at == None,  # noqa: E711
            Task.archived_at == None,  # noqa: E711
            Task.is_local == False,  # noqa: E712  (lembrete local não entra)
        )
        .all()
    )

    notas = {
        (n.member_name, n.week_start): n
        for n in session.query(TeamNote)
        .filter(TeamNote.project_id == project.id, TeamNote.week_start == inicio)
        .all()
    }
    # serviço da semana: revisões dadas e PRs citados nos comentários
    # `created_at` é gravado em UTC: o intervalo da semana (local) vira UTC
    # antes de filtrar, senão comentário de fim de domingo cai na semana errada
    de_utc, ate_utc = limites_utc(inicio, fim)
    comentarios_semana = (
        session.query(Comment)
        .join(Task, Comment.task_id == Task.id)
        .filter(
            Task.project_id == project.id,
            Comment.created_at >= de_utc,
            Comment.created_at <= ate_utc,
        )
        .all()
    )
    servico_por_autor: dict[str, dict] = {}
    for c in comentarios_semana:
        autor = (c.author or "").strip()
        dados = servico_por_autor.setdefault(autor, {"reviews": 0, "cards": {}, "prs": set()})
        if c.type == "CODE_REVIEW":
            dados["reviews"] += 1
            tarefa = c.task
            if tarefa is not None:
                dados["cards"][tarefa.code] = {
                    "code": tarefa.code,
                    "title": tarefa.title or "",
                    "date": (data_local(c.created_at) or hoje).isoformat(),
                }
        for achado in _PR_RE.finditer(c.body or ""):
            numero = next((g for g in achado.groups() if g), None)
            if numero:
                dados["prs"].add(numero)

    nomes = sorted({m.name for m in session.query(Member).filter(Member.project_id == project.id).all()}
                   | {t.assignee for t in tasks if t.assignee})

    membros = []
    for nome in nomes:
        meus = [t for t in tasks if (t.assignee or "") == nome]
        abertos = [t for t in meus if t.column_id not in done_ids]
        entregues = []
        sem_data = 0
        for t in meus:
            col = por_coluna.get(t.column_id)
            quando = _dt(t.done_at)
            dia = data_local(quando)
            if col and col.is_done and _importado(t, quando):
                # só incomoda o relatório se a data "cairia" nesta semana
                if dia and inicio <= dia <= fim:
                    sem_data += 1
                continue
            if dia and inicio <= dia <= fim:
                entregues.append({
                    "code": t.code,
                    "title": t.title,
                    "module": _modulo(t),
                    "date": dia.isoformat(),
                    "inferred": False,
                    "column": col.name if col else "",
                })
        entregues.sort(key=lambda x: (x["date"], x["code"]))
        carga = Counter(
            por_coluna[t.column_id].name for t in abertos if t.column_id in por_coluna
        )
        backlog = sum(
            1 for t in abertos
            if por_coluna.get(t.column_id) and por_coluna[t.column_id].order <= primeira_ordem
        )
        nota = notas.get((nome, inicio))
        servico = servico_por_autor.get(nome, {"reviews": 0, "cards": {}, "prs": set()})
        membros.append({
            "name": nome,
            "assigned": len(meus),
            "doneTotal": sum(1 for t in meus if t.column_id in done_ids),
            "legacyDone": sem_data,
            "delivered": entregues,
            "deliveredCount": len(entregues),
            "open": len(abertos),
            "backlog": backlog,
            "active": len(abertos) - backlog,
            "overdue": sum(
                1 for t in abertos if t.due_date and t.due_date.date() < hoje
            ),
            "reviews": servico.get("reviews", 0),
            "reviewedCards": sorted(servico.get("cards", {}).values(), key=lambda x: x["date"]),
            "prs": sorted(servico.get("prs", set())),
            "serviceSuggested": _sugestao_servico(servico, len(entregues)),
            "byColumn": [{"name": n, "count": q} for n, q in carga.most_common()],
            "note": {
                "highlights": (nota.highlights if nota else "") or "",
                "service": (nota.service if nota else "") or "",
                "attention": (nota.attention if nota else "") or "",
                "nextStep": (nota.next_step if nota else "") or "",
                "updatedAt": nota.updated_at.isoformat() if nota and nota.updated_at else None,
            },
        })

    membros.sort(key=lambda m: (-m["deliveredCount"], -m["open"], m["name"]))

    entregues_semana = [e for m in membros for e in m["delivered"]]
    sem_data_total = sum(m["legacyDone"] for m in membros)
    por_modulo = Counter(e["module"] or "sem módulo" for e in entregues_semana)
    abertos = [t for t in tasks if t.column_id not in done_ids]

    resumo = {
        "cards": len(tasks),
        "done": sum(1 for t in tasks if t.column_id in done_ids),
        "pct": round(sum(1 for t in tasks if t.column_id in done_ids) / len(tasks) * 100) if tasks else 0,
        "doneInWeek": len(entregues_semana),
        "legacyDone": sem_data_total,
        "open": len(abertos),
        "overdue": sum(1 for t in abertos if t.due_date and t.due_date.date() < hoje),
        "unassigned": sum(1 for t in abertos if not t.assignee),
        "byColumn": [
            {"name": c.name, "count": sum(1 for t in tasks if t.column_id == c.id),
             "isDone": bool(c.is_done)}
            for c in cols
        ],
        "byModule": [{"module": m, "count": n} for m, n in por_modulo.most_common()],
    }

    return {
        "project": {"id": project.id, "key": project.key, "name": project.name},
        "week": {
            "start": inicio.isoformat(),
            "end": fim.isoformat(),
            "label": f"{inicio.strftime('%d/%m')} a {fim.strftime('%d/%m/%Y')}",
        },
        "summary": resumo,
        "members": membros,
        "notesPending": sum(1 for m in membros if not any(m["note"].values())),
    }


def _nome(membro: dict, indice: int, anonimizado: bool) -> str:
    if not anonimizado:
        return membro["name"]
    letra = ANONIMOS[indice % len(ANONIMOS)]
    return f"Pessoa {letra}"


def _bloco_texto(titulo: str, texto: str) -> list[str]:
    texto = (texto or "").strip()
    if not texto:
        return []
    linhas = [f"**{titulo}:** {texto}" if "\n" not in texto else f"**{titulo}:**", ""]
    if "\n" in texto:
        linhas += [f"- {l.strip('- •').strip()}" for l in texto.splitlines() if l.strip()]
    return linhas + [""]


def render_markdown(dados: dict, anonimizado: bool = False) -> str:
    """Markdown no formato dos acompanhamentos semanais do vault."""
    semana, resumo = dados["week"], dados["summary"]
    out: list[str] = []

    titulo = "Acompanhamento semanal da equipe"
    if anonimizado:
        titulo += " (versão anonimizada)"
    out.append(f"# {titulo} — {semana['label']}")
    out.append("")
    if anonimizado:
        out.append(
            "> **Versão para apresentação ampla — sem nomes.** As pessoas aparecem como "
            "**Pessoa A/B/C**; o de-para fica só com a gestão direta."
        )
    else:
        out.append(
            "> **Uso interno de gestão.** Este relatório identifica as pessoas porque é para "
            "distribuição e acompanhamento direto. Para apresentação ampla, gere a versão "
            "anonimizada."
        )
    out.append(f"> Período: **{semana['label']}**")
    out.append("")

    # ---------- 1. resumo ----------
    out.append("## 1. Resumo do período")
    out.append("")
    out.append("| Indicador | Valor |")
    out.append("|---|---|")
    out.append(f"| Progresso do board | **{resumo['done']}/{resumo['cards']} ({resumo['pct']}%)** |")
    out.append(f"| Cards concluídos no período | **{resumo['doneInWeek']}** |")
    if resumo["byModule"]:
        mods = " · ".join(f"{m['module']} {m['count']}" for m in resumo["byModule"])
        out.append(f"| Entregas por módulo | {mods} |")
    colunas = " · ".join(f"{c['name']} {c['count']}" for c in resumo["byColumn"])
    out.append(f"| Cards no board | **{resumo['cards']}** — {colunas} |")
    out.append(f"| Em aberto | **{resumo['open']}** (atrasados **{resumo['overdue']}**) |")
    out.append(f"| Sem responsável (aberto) | **{resumo['unassigned']}** |")
    if resumo.get("legacyDone"):
        out.append(
            f"| Conclusões do período sem data confiável | {resumo['legacyDone']} card(s) "
            "vieram da importação (a data de conclusão é a do import) — não contadas |"
        )
    out.append("")

    # ---------- 2. membros ----------
    out.append("## 2. Como cada membro está trabalhando")
    out.append("")
    if not dados["members"]:
        out.append("_Nenhum membro com cards no projeto._")
        out.append("")
    for i, m in enumerate(dados["members"]):
        nome = _nome(m, i, anonimizado)
        foco = ", ".join(c["name"] for c in m["byColumn"][:2])
        cabecalho = f"### {nome}"
        if m["deliveredCount"]:
            cabecalho += f" — {m['deliveredCount']} entrega(s) no período"
        elif foco:
            cabecalho += f" — foco em {foco}"
        out.append(cabecalho)
        out.append("")
        out.append("| | |")
        out.append("|---|---|")
        if m["delivered"]:
            entregas = ", ".join(
                f"`{e['code']}`" + (f" ({e['module']})" if e["module"] else "")
                for e in m["delivered"]
            )
            out.append(f"| Cards concluídos no período | **{m['deliveredCount']}** — {entregas} |")
        else:
            out.append("| Cards concluídos no período | — |")
        if m["byColumn"]:
            carga = " · ".join(f"{c['name']} {c['count']}" for c in m["byColumn"])
            out.append(f"| Em aberto | **{m['open']}** ({carga}) |")
        else:
            out.append(f"| Em aberto | **{m['open']}** |")
        out.append(f"| Atrasados | {m['overdue']} |")
        if m["reviews"]:
            out.append(f"| Revisões registradas | {m['reviews']} |")
        out.append("")
        for titulo_txt, chave in (
            ("Como está trabalhando", "highlights"),
            ("Serviço/apoio", "service"),
            ("Pontos de atenção (fatos, não julgamento)", "attention"),
            ("Próximo passo", "nextStep"),
        ):
            out += _bloco_texto(titulo_txt, m["note"].get(chave, ""))
        # o que o board já registra de serviço (revisões/PRs) sem o líder digitar
        if m.get("serviceSuggested") and not (m["note"].get("service") or "").strip():
            out += _bloco_texto("Serviço/apoio (levantado do board)", m["serviceSuggested"])
        out.append("")

    # ---------- 3. carga ----------
    out.append("## 3. Distribuição de carga (fim do período)")
    out.append("")
    out.append("| Membro | Cards | Em aberto | Backlog | Concluídos | Atrasados |")
    out.append("|---|---:|---:|---:|---:|---:|")
    for i, m in enumerate(dados["members"]):
        out.append(
            f"| {_nome(m, i, anonimizado)} | {m['assigned']} | {m['open']} | "
            f"{m['backlog']} | {m['doneTotal']} | {m['overdue']} |"
        )
    out.append("")

    if dados.get("notesPending"):
        out.append(
            f"> {dados['notesPending']} membro(s) sem anotação de gestão nesta semana — "
            "o relatório sai só com os números do board."
        )
        out.append("")

    out.append("---")
    out.append("")
    out.append(f"_Gerado pelo Relay Local em {datetime.now().strftime('%d/%m/%Y %H:%M')}._")
    return "\n".join(out).strip() + "\n"
