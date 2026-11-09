"""Contexto do projeto para o copiloto de reunião.

A reunião em si manda no transcript, mas o copiloto só dá dica útil se souber
onde o time está: o que está parado no board, o que atrasou, como está o
progresso por módulo e o que foi registrado nas dailies recentes.

O bloco é curto de propósito (cabe no limite de contexto do extrator) e é
regenerado a cada extração — com cache curto na view para não consultar o
banco a cada trecho.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from maestro_local.timeutil import data_local

LIMITE_CARDS = 12
LIMITE_ATRASADOS = 8
LIMITE_DAILIES = 5
LIMITE_ENTREGAS = 8


def _dias_desde(quando: datetime | None, hoje: date) -> int | None:
    dia = data_local(quando)
    if dia is None:
        return None
    return max(0, (hoje - dia).days)


def project_context(session, project_id: int) -> str:
    """Markdown compacto: board, atrasos, módulos, entregas e dailies recentes."""
    from maestro_local.db.models import (
        BoardColumn,
        Project,
        ProjectDailyEntry,
        Task,
    )
    from maestro_local.dimensions import aggregate_dimensions

    projeto = session.query(Project).filter(Project.id == project_id).first()
    if projeto is None:
        return ""

    hoje = date.today()
    cols = (
        session.query(BoardColumn)
        .filter(BoardColumn.project_id == project_id)
        .order_by(BoardColumn.order)
        .all()
    )
    por_id = {c.id: c for c in cols}
    done_ids = {c.id for c in cols if c.is_done}
    primeira = cols[0].order if cols else 0

    tasks = (
        session.query(Task)
        .filter(
            Task.project_id == project_id,
            Task.deleted_at == None,  # noqa: E711
            Task.archived_at == None,  # noqa: E711
            Task.is_local == False,  # noqa: E712
        )
        .all()
    )
    if not tasks and not cols:
        return ""

    abertos = [t for t in tasks if t.column_id not in done_ids]
    concluidos = len(tasks) - len(abertos)
    pct = round(concluidos / len(tasks) * 100) if tasks else 0

    linhas = [f"## Projeto — {projeto.key} · {projeto.name}"]
    linhas.append(
        f"- Board: {len(tasks)} cards · {concluidos} concluídos ({pct}%) · "
        f"{len(abertos)} em aberto · {sum(1 for t in abertos if not t.assignee)} sem responsável"
    )
    por_coluna = [
        f"{c.name} {sum(1 for t in tasks if t.column_id == c.id)}"
        for c in cols
        if any(t.column_id == c.id for t in tasks)
    ]
    if por_coluna:
        linhas.append("- Por coluna: " + " · ".join(por_coluna))

    # o que está em andamento (fora do backlog) e, entre esses, os mais parados
    andamento = [
        t for t in abertos
        if (col := por_id.get(t.column_id)) is not None and col.order > primeira
    ]
    andamento.sort(key=lambda t: (t.updated_at or datetime.min, t.number))
    if andamento:
        linhas.append("")
        linhas.append("### Em andamento (mais parados primeiro)")
        for t in andamento[:LIMITE_CARDS]:
            col = por_id.get(t.column_id)
            parado = _dias_desde(t.updated_at, hoje)
            marca = f" · parado há {parado}d" if parado and parado >= 3 else ""
            dono = t.assignee or "sem dono"
            linhas.append(f"- {t.code} · {t.title[:80]} — {col.name if col else '?'} · {dono}{marca}")

    atrasados = sorted(
        (t for t in abertos if t.due_date and t.due_date.date() < hoje),
        key=lambda t: t.due_date,
    )
    if atrasados:
        linhas.append("")
        linhas.append("### Atrasados")
        for t in atrasados[:LIMITE_ATRASADOS]:
            linhas.append(
                f"- {t.code} · {t.title[:70]} — venceu {t.due_date.date().strftime('%d/%m')}"
                f" · {t.assignee or 'sem dono'}"
            )

    # progresso por módulo (plano de entrega)
    dims = aggregate_dimensions(tasks, done_ids)
    modulos = [m for m in dims.get("modules", []) if m["total"] > 0][:8]
    if modulos:
        linhas.append("")
        linhas.append("### Progresso por módulo")
        linhas.append(
            "- " + " · ".join(f"{m['label']} {m['done']}/{m['total']} ({m['pct']}%)" for m in modulos)
        )

    # entregas recentes (data real de conclusão)
    entregues = [
        t for t in tasks
        if t.done_at and (dia := data_local(t.done_at)) and (hoje - dia).days <= 7
    ]
    entregues.sort(key=lambda t: t.done_at, reverse=True)
    if entregues:
        linhas.append("")
        linhas.append("### Concluídos nos últimos 7 dias")
        for t in entregues[:LIMITE_ENTREGAS]:
            linhas.append(f"- {t.code} · {t.title[:70]} — {data_local(t.done_at).strftime('%d/%m')}")

    # dailies recentes
    recentes = (
        session.query(ProjectDailyEntry)
        .filter(ProjectDailyEntry.project_id == project_id)
        .order_by(ProjectDailyEntry.date.desc(), ProjectDailyEntry.sort_order)
        .limit(LIMITE_DAILIES)
        .all()
    )
    if recentes:
        linhas.append("")
        linhas.append("### Registros recentes (daily do projeto)")
        for d in recentes:
            # corpo da daily vem em markdown: tira marcação para o contexto não
            # gastar token com `**`, backticks e "- " de lista
            corpo = re.sub(r"[`*_>#]", "", d.body or "")
            corpo = " ".join(corpo.split())
            if len(corpo) > 240:
                corpo = corpo[:237] + "…"
            titulo = f"{d.title} — " if d.title else ""
            linhas.append(f"- {d.date} · {d.kind} · {titulo}{corpo}")

    return "\n".join(linhas).strip()
