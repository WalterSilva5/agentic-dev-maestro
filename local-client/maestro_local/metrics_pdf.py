"""Relatório de métricas do projeto em PDF.

Gera um PDF de uma página (ou mais) com o mesmo conteúdo da aba **Métricas**
do board, para enviar a liderança sem depender da tela.

Uso pela API:
    GET /api/projects/{id}/metrics/export.pdf

Uso direto (CLI/debug):
    python -c "from maestro_local.metrics_pdf import build_metrics_pdf; ..."
"""
from __future__ import annotations

import io
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ACCENT = colors.HexColor("#6D5EF8")
MUTED = colors.HexColor("#6B7280")
TEXT = colors.HexColor("#0B0D12")
BORDER = colors.HexColor("#E3E6EE")
GREEN = colors.HexColor("#16A34A")
AMBER = colors.HexColor("#D97706")
RED = colors.HexColor("#DC2626")
PIE_COLORS = ["#4F46E5", "#06B6D4", "#F59E0B", "#EF4444", "#10B981", "#8B5CF6", "#EC4899", "#6366F1"]


# ---------------------------------------------------------------------------
# Cálculo das métricas (espelha o que o board mostra)
# ---------------------------------------------------------------------------


def collect_metrics(session, project) -> dict:
    """Consolida números do projeto: progresso, módulos, pessoas, colunas, daily."""
    from maestro_local.db.models import (
        BoardColumn,
        Epic,
        Label,
        ProjectDailyEntry,
        Task,
    )

    cols = (
        session.query(BoardColumn)
        .filter(BoardColumn.project_id == project.id)
        .order_by(BoardColumn.order)
        .all()
    )
    done_ids = {c.id for c in cols if c.is_done}

    tasks = (
        session.query(Task)
        .filter(
            Task.project_id == project.id,
            Task.deleted_at == None,  # noqa: E711
            Task.archived_at == None,  # noqa: E711
        )
        .all()
    )
    total = len(tasks)
    done = sum(1 for t in tasks if t.column_id in done_ids)
    pct = round(done / total * 100) if total else 0

    hoje = date.today()
    vencidas = [t for t in tasks if t.due_date and t.due_date.date() < hoje and t.column_id not in done_ids]
    limite = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    limite = limite.fromordinal(limite.toordinal() - 14)
    paradas = [t for t in tasks if t.column_id not in done_ids and t.updated_at and t.updated_at < limite]

    wip = []
    for c in cols:
        if c.wip_limit and c.wip_limit > 0:
            n = sum(1 for t in tasks if t.column_id == c.id)
            if n > c.wip_limit:
                wip.append((c.name, n, c.wip_limit))

    # por coluna
    por_coluna = [(c.name, sum(1 for t in tasks if t.column_id == c.id), c.wip_limit, bool(c.is_done)) for c in cols]

    # por pessoa (inclui "sem responsável")
    pessoas: dict[str, list] = {}
    for t in tasks:
        pessoas.setdefault(t.assignee or "", []).append(t)
    por_pessoa = []
    for nome, lst in pessoas.items():
        feitas = sum(1 for t in lst if t.column_id in done_ids)
        por_pessoa.append({
            "nome": nome or "Sem responsável",
            "total": len(lst),
            "done": feitas,
            "pct": round(feitas / len(lst) * 100) if lst else 0,
            "sem_dono": not nome,
        })
    por_pessoa.sort(key=lambda x: (-x["total"], x["nome"]))

    # por prioridade
    por_prioridade: dict[str, int] = {}
    for t in tasks:
        por_prioridade[t.priority or "MEDIUM"] = por_prioridade.get(t.priority or "MEDIUM", 0) + 1

    # por épico
    epics = session.query(Epic).filter(Epic.project_id == project.id).order_by(Epic.name).all()
    por_epico = []
    for ep in epics:
        lst = [t for t in tasks if any(e.id == ep.id for e in t.epics)]
        if not lst:
            continue
        feitas = sum(1 for t in lst if t.column_id in done_ids)
        por_epico.append({
            "nome": ep.name,
            "color": ep.color or PIE_COLORS[len(por_epico) % len(PIE_COLORS)],
            "total": len(lst),
            "done": feitas,
            "pct": round(feitas / len(lst) * 100),
        })
    por_epico.sort(key=lambda x: -x["total"])

    # por módulo (label) — só labels usadas
    labels = session.query(Label).order_by(Label.name).all()
    contagem_label: dict[str, int] = {}
    for t in tasks:
        for lb in t.labels:
            contagem_label[lb.name] = contagem_label.get(lb.name, 0) + 1
    por_modulo = []
    for lb in labels:
        n = contagem_label.get(lb.name, 0)
        if not n:
            continue
        lst = [t for t in tasks if any(x.name == lb.name for x in t.labels)]
        feitas = sum(1 for t in lst if t.column_id in done_ids)
        por_modulo.append({
            "nome": lb.name,
            "color": lb.color or ACCENT,
            "total": n,
            "done": feitas,
            "pct": round(feitas / n * 100),
        })
    por_modulo.sort(key=lambda x: x["nome"])

    # daily do projeto
    daily = (
        session.query(ProjectDailyEntry)
        .filter(ProjectDailyEntry.project_id == project.id)
        .order_by(ProjectDailyEntry.date.desc(), ProjectDailyEntry.sort_order)
        .all()
    )
    daily_dias = sorted({d.date for d in daily}, reverse=True)
    daily_min = sum(d.minutes or 0 for d in daily)
    por_tipo_daily: dict[str, int] = {}
    for d in daily:
        por_tipo_daily[d.kind or "WORK"] = por_tipo_daily.get(d.kind or "WORK", 0) + 1

    return {
        "projeto": {"key": project.key, "name": project.name, "id": project.id},
        "total": total,
        "done": done,
        "pct": pct,
        "abertas": total - done,
        "vencidas": len(vencidas),
        "paradas": len(paradas),
        "wip": wip,
        "por_coluna": por_coluna,
        "por_pessoa": por_pessoa,
        "por_prioridade": por_prioridade,
        "por_epico": por_epico,
        "por_modulo": por_modulo,
        "daily": {
            "total": len(daily),
            "dias": len(daily_dias),
            "minutos": daily_min,
            "por_tipo": por_tipo_daily,
            "ultimos": daily_dias[:10],
        },
        "gerado_em": datetime.now(),
    }


# ---------------------------------------------------------------------------
# Desenho do PDF
# ---------------------------------------------------------------------------


def _styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Title"], fontName="Helvetica-Bold",
                             fontSize=19, leading=23, textColor=TEXT, alignment=TA_LEFT,
                             spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontName="Helvetica",
                              fontSize=9.5, leading=12, textColor=MUTED, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=11.5, leading=14, textColor=TEXT,
                             spaceBefore=10, spaceAfter=5),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica",
                               fontSize=9, leading=12, textColor=TEXT),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8, leading=10.5, textColor=MUTED),
        "kpi_val": ParagraphStyle("kpi_val", parent=base["Normal"], fontName="Helvetica-Bold",
                                  fontSize=17, leading=19, textColor=ACCENT),
        "kpi_lbl": ParagraphStyle("kpi_lbl", parent=base["Normal"], fontName="Helvetica",
                                  fontSize=7.5, leading=9, textColor=MUTED),
    }


def _bar(pct: float, width: float = 90, height: float = 7, cor=ACCENT) -> Table:
    """Barra de progresso feita com duas células (sem depender de gráfico)."""
    pct = max(0, min(100, pct))
    cheio = width * pct / 100.0
    vazio = max(0.1, width - cheio)
    t = Table([["", ""]], colWidths=[cheio or 0.1, vazio], rowHeights=[height])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), cor),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#EEEFF5")),
        ("BOX", (0, 0), (-1, -1), 0, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _kpi_row(m: dict, st: dict) -> Table:
    def celula(valor, rotulo):
        return [Paragraph(str(valor), st["kpi_val"]), Paragraph(rotulo, st["kpi_lbl"])]

    dados = [[
        celula(f"{m['pct']}%", "PROGRESSO"),
        celula(f"{m['done']}/{m['total']}", "CONCLUÍDAS"),
        celula(m["abertas"], "EM ABERTO"),
        celula(m["vencidas"], "VENCIDAS"),
        celula(m["paradas"], "PARADAS 14d+"),
        celula(m["daily"]["dias"], "DIAS COM DAILY"),
    ]]
    t = Table(dados, colWidths=[28 * mm] * 6)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def _tabela_barra(linhas: list[tuple[str, int, int, int]], st: dict, cor_fn=None) -> Table:
    """Linhas: (nome, feito, total, pct) com barra ao lado."""
    dados = []
    for nome, feito, total, pct in linhas:
        cor = cor_fn(nome) if cor_fn else (GREEN if pct == 100 else (AMBER if pct > 0 else colors.HexColor("#CBD5E1")))
        dados.append([
            Paragraph(nome, st["body"]),
            _bar(pct, width=52, cor=cor),
            Paragraph(f"{feito}/{total} · {pct}%", st["small"]),
        ])
    if not dados:
        return Table([[Paragraph("Sem dados.", st["small"])]], colWidths=[168 * mm])
    t = Table(dados, colWidths=[58 * mm, 56 * mm, 54 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, BORDER),
    ]))
    return t


def build_metrics_pdf(session, project) -> bytes:
    """Monta o PDF e devolve os bytes."""
    m = collect_metrics(session, project)
    st = _styles()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Métricas — {project.key} {project.name}",
        author="Agentic Dev Maestro",
    )

    flow = []
    flow.append(Paragraph(f"Métricas do projeto — {project.key} · {project.name}", st["h1"]))
    flow.append(Paragraph(
        f"Gerado em {m['gerado_em'].strftime('%d/%m/%Y %H:%M')} · "
        f"{m['total']} tarefas no board · progresso {m['pct']}%",
        st["sub"],
    ))
    flow.append(_kpi_row(m, st))
    flow.append(Spacer(1, 3 * mm))
    flow.append(_bar(m["pct"], width=174 * mm, height=9,
                     cor=GREEN if m["pct"] == 100 else ACCENT))

    # Alertas
    alertas = []
    for nome, n, lim in m["wip"]:
        alertas.append(f"<b>WIP acima do limite</b> — {nome}: {n}/{lim}")
    if m["vencidas"]:
        alertas.append(f"<b>{m['vencidas']} tarefa(s) vencida(s)</b> sem concluir")
    if m["paradas"]:
        alertas.append(f"<b>{m['paradas']} tarefa(s) parada(s)</b> há mais de 14 dias")
    sem_dono = next((p for p in m["por_pessoa"] if p["sem_dono"]), None)
    if sem_dono and sem_dono["total"]:
        alertas.append(
            f"<b>{sem_dono['total']} tarefa(s) sem responsável</b> "
            f"({round(sem_dono['total'] / max(1, m['total']) * 100)}% do board)"
        )
    if alertas:
        flow.append(Paragraph("Alertas", st["h2"]))
        for a in alertas:
            flow.append(Paragraph("• " + a, st["body"]))

    # Progresso por coluna
    flow.append(Paragraph("Por coluna", st["h2"]))
    linhas_col = [
        (f"{nome}{' (conclusão)' if is_done else ''}", 0, n, 0)
        for nome, n, _wip, is_done in m["por_coluna"]
    ]
    dados_col = [[
        Paragraph("<b>Coluna</b>", st["small"]),
        Paragraph("<b>Cards</b>", st["small"]),
        Paragraph("<b>Conclusão</b>", st["small"]),
    ]]
    for (nome, n, wip, is_done) in m["por_coluna"]:
        dados_col.append([
            Paragraph(nome, st["body"]),
            Paragraph(f"<b>{n}</b>" + (f" / {wip}" if wip else ""), st["small"]),
            Paragraph("✓" if is_done else "", st["small"]),
        ])
    t = Table(dados_col, colWidths=[112 * mm, 42 * mm, 20 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, BORDER),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#9CA3AF")),
    ]))
    flow.append(t)

    # Por pessoa
    flow.append(Paragraph("Por responsável", st["h2"]))
    linhas_pessoa = [(p["nome"], p["done"], p["total"], p["pct"]) for p in m["por_pessoa"][:12]]
    flow.append(_tabela_barra(
        linhas_pessoa,
        st,
        cor_fn=lambda nome: colors.HexColor("#9CA3AF") if nome == "Sem responsável" else ACCENT,
    ))

    # Por módulo / épico
    if m["por_modulo"] or m["por_epico"]:
        if m["por_modulo"]:
            flow.append(Paragraph("Por módulo (labels)", st["h2"]))
            limite_mod = 24
            flow.append(_tabela_barra(
                [(x["nome"], x["done"], x["total"], x["pct"]) for x in m["por_modulo"][:limite_mod]],
                st,
                cor_fn=lambda _n: ACCENT,
            ))
            if len(m["por_modulo"]) > limite_mod:
                flow.append(Paragraph(
                    f"+ {len(m['por_modulo']) - limite_mod} módulo(s) não exibidos", st["small"]
                ))
        if m["por_epico"]:
            flow.append(Paragraph("Por épico", st["h2"]))
            cores = {e["nome"]: colors.HexColor(e["color"]) for e in m["por_epico"]}
            flow.append(_tabela_barra(
                [(x["nome"], x["done"], x["total"], x["pct"]) for x in m["por_epico"][:16]],
                st,
                cor_fn=lambda n: cores.get(n, ACCENT),
            ))

    # Prioridade
    if m["por_prioridade"]:
        flow.append(Paragraph("Por prioridade", st["h2"]))
        rotulos = {"URGENT": "Urgente", "HIGH": "Alta", "MEDIUM": "Média", "LOW": "Baixa"}
        dados = [[
            Paragraph(rotulos.get(k, k), st["body"]),
            Paragraph(f"<b>{v}</b>", st["small"]),
        ] for k, v in sorted(m["por_prioridade"].items(), key=lambda x: -x[1])]
        t = Table(dados, colWidths=[96 * mm, 72 * mm])
        t.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, BORDER),
        ]))
        flow.append(t)

    # Daily
    d = m["daily"]
    if d["total"]:
        flow.append(Paragraph("Daily do projeto", st["h2"]))
        tipos = ", ".join(f"{k}: {v}" for k, v in sorted(d["por_tipo"].items()))
        horas = round(d["minutos"] / 60, 1)
        flow.append(Paragraph(
            f"{d['total']} registro(s) em {d['dias']} dia(s) · {horas}h registradas · {tipos}",
            st["body"],
        ))
        if d["ultimos"]:
            flow.append(Paragraph("Últimos dias: " + ", ".join(d["ultimos"]), st["small"]))

    flow.append(Spacer(1, 6 * mm))
    flow.append(Paragraph(
        "Fonte: Agentic Dev Maestro · dados locais do workspace ativo. "
        "Não inclui alterações de plataformas externas.",
        st["small"],
    ))

    doc.build(flow)
    return buf.getvalue()


def metrics_pdf_filename(project) -> str:
    dia = datetime.now().strftime("%Y-%m-%d")
    nome = f"metricas-{project.key}-{dia}.pdf"
    return nome.replace(" ", "-")
