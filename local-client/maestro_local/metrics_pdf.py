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
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
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

    # dimensões classificadas (módulo != sprint != plataforma != natureza)
    from maestro_local.dimensions import aggregate_dimensions
    dimensoes = aggregate_dimensions(tasks, done_ids)

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
        "dimensoes": dimensoes,
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


def _donut(dados: list[tuple[str, int, str]], size: float = 46 * mm,
           titulo: str = "", st: dict | None = None) -> Drawing:
    """Donut com buraco central e total, igual ao `PieChart` da interface."""
    dados = [(rot, val, cor) for rot, val, cor in dados if val]
    total = sum(v for _r, v, _c in dados)
    d = Drawing(size, size)
    if not total:
        if titulo:
            d.add(String(size / 2, size / 2, "Sem dados", textAnchor="middle",
                         fontName="Helvetica", fontSize=7.5, fillColor=MUTED))
        return d

    pc = Pie()
    pc.x = size * 0.04
    pc.y = size * 0.04
    pc.width = size * 0.92
    pc.height = size * 0.92
    pc.data = [v for _r, v, _c in dados]
    pc.labels = None
    pc.startAngle = 90
    pc.direction = "clockwise"
    pc.slices.strokeColor = colors.white
    pc.slices.strokeWidth = 1.2
    for i, (_r, _v, cor) in enumerate(dados):
        pc.slices[i].fillColor = colors.HexColor(cor)
    try:
        pc.innerRadiusFraction = 0.52
    except Exception:  # versões antigas: cai no modo pizza
        pass
    d.add(pc)
    d.add(String(size / 2, size / 2 - 2.2, str(total), textAnchor="middle",
                 fontName="Helvetica-Bold", fontSize=8.5, fillColor=TEXT))
    if titulo:
        d.add(String(size / 2, size - 1, titulo, textAnchor="middle",
                     fontName="Helvetica-Bold", fontSize=7, fillColor=TEXT))
    return d


def _legenda(dados: list[tuple[str, int, str]], st: dict, largura: float = 44 * mm,
             max_itens: int = 5) -> Table:
    """Legenda do donut: bolinha + rótulo + valor (igual ao quadro da UI)."""
    dados = [(r, v, c) for r, v, c in dados if v]
    linhas = []
    for rot, val, cor in dados[:max_itens]:
        rot = rot if len(rot) <= 26 else rot[:25] + "…"
        linhas.append([
            _bar_legenda(cor),
            Paragraph(f"{rot} <font color='#6B7280'>({val})</font>", st["small"]),
        ])
    if len(dados) > max_itens:
        linhas.append(["", Paragraph(f"+{len(dados) - max_itens} outros", st["small"])])
    if not linhas:
        return Table([[Paragraph("—", st["small"])]], colWidths=[largura])
    t = Table(linhas, colWidths=[4 * mm, largura - 4 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _bar_legenda(cor: str) -> Drawing:
    d = Drawing(3.2 * mm, 3.2 * mm)
    d.add(String(0, 0.4 * mm, "■", fontName="Helvetica", fontSize=8,
                 fillColor=colors.HexColor(cor)))
    return d


def _cartao_grafico(titulo: str, dados: list[tuple[str, int, str]], st: dict,
                    largura: float = 84 * mm, size: float = 42 * mm,
                    max_legenda: int = 5) -> Table:
    """Donut + legenda + título, no mesmo formato dos cards da aba Métricas."""
    largura_legenda = largura - size - 6
    corpo = Table([[_donut(dados, size=size, st=st),
                    _legenda(dados, st, largura=largura_legenda, max_itens=max_legenda)]],
                  colWidths=[size, largura_legenda])
    corpo.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    caixa = Table([
        [Paragraph(titulo.upper(), st["kpi_lbl"])],
        [corpo],
    ], colWidths=[largura])
    caixa.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return caixa


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


def _dados_colunas(m: dict) -> list[tuple[str, int, str]]:
    return [
        (nome, n, PIE_COLORS[i % len(PIE_COLORS)])
        for i, (nome, n, _wip, _done) in enumerate(m["por_coluna"])
        if n
    ]


def _dados_pessoas(m: dict) -> list[tuple[str, int, str]]:
    return [
        (p["nome"], p["total"], "#9CA3AF" if p["sem_dono"] else PIE_COLORS[i % len(PIE_COLORS)])
        for i, p in enumerate(m["por_pessoa"])
        if p["total"]
    ]


def _dados_prioridade(m: dict) -> list[tuple[str, int, str]]:
    rotulos = {"URGENT": "Urgente", "HIGH": "Alta", "MEDIUM": "Média", "LOW": "Baixa"}
    cores = {"URGENT": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#4F46E5", "LOW": "#71717A"}
    ordem = ["URGENT", "HIGH", "MEDIUM", "LOW"]
    return [
        (rotulos[k], m["por_prioridade"][k], cores[k])
        for k in ordem
        if m["por_prioridade"].get(k)
    ]


def _dados_modulos(m: dict) -> list[tuple[str, int, str]]:
    """Só módulos (sem sprint/plataforma/tag) — usa a classificação."""
    mods = [x for x in m.get("dimensoes", {}).get("modules", []) if x["total"] > 0]
    return [
        (x["label"], x["total"], PIE_COLORS[i % len(PIE_COLORS)])
        for i, x in enumerate(mods)
    ]


def _dados_epicos(m: dict) -> list[tuple[str, int, str]]:
    return [(x["nome"], x["total"], x["color"]) for x in m["por_epico"]]


def _titulo(flow, texto: str, st):
    flow.append(Paragraph(texto, st["h2"]))


def build_metrics_pdf(session, project) -> bytes:
    """Monta o PDF com os mesmos gráficos da aba Métricas."""
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

    LARG = 85 * mm  # 2 cartões por linha (174mm)
    flow = []

    # ---------- cabeçalho ----------
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

    # ---------- gráficos: coluna | responsável | prioridade ----------
    _titulo(flow, "Visão por coluna, responsável e prioridade", st)
    graficos1 = Table([
        [
            _cartao_grafico("Distribuição por coluna", _dados_colunas(m), st, largura=LARG),
            _cartao_grafico("Por prioridade", _dados_prioridade(m), st, largura=LARG, max_legenda=4),
        ],
        [
            _cartao_grafico("Por responsável", _dados_pessoas(m), st, largura=LARG),
            _cartao_grafico("Por módulo (labels)", _dados_modulos(m), st, largura=LARG, max_legenda=5),
        ],
    ], colWidths=[LARG + 2 * mm] * 2)
    graficos1.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    flow.append(graficos1)

    # ---------- alertas ----------
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
        _titulo(flow, "Alertas", st)
        for a in alertas:
            flow.append(Paragraph("• " + a, st["body"]))

    # ---------- por épico (donut) ----------
    if m["por_epico"]:
        _titulo(flow, "Por épico", st)
        flow.append(_cartao_grafico("Distribuição por épico", _dados_epicos(m), st,
                                    largura=174 * mm, size=46 * mm, max_legenda=8))

    # ---------- módulos e submódulos (classificação explícita) ----------
    dims = m.get("dimensoes", {})
    mods = dims.get("modules", [])
    if mods:
        _titulo(flow, "Módulos e submódulos", st)
        sem = dims.get("unlabeled", {}).get("total", 0)
        plano = dims.get("plan") or {}
        flow.append(Paragraph(
            f"<b>{plano.get('modules', 0)} módulos · {plano.get('endpoints', 0)} endpoints no plano</b>"
            + f" · {dims.get('with_module', 0)}/{dims.get('cards', 0)} cards com módulo"
            + (f" · {sem} sem módulo (não entram no progresso por módulo)" if sem else "")
            + " · um card pode ter mais de um módulo · largura da barra proporcional ao tamanho",
            st["small"],
        ))
        flow.append(Spacer(1, 2 * mm))
        maximo = max(x["total"] for x in mods) or 1
        linhas = [[
            Paragraph("<b>Módulo / sub-entrega</b>", st["small"]),
            Paragraph("<b>Progresso</b>", st["small"]),
            Paragraph("<b>Cards / endpoints</b>", st["small"]),
        ]]
        for x in mods[:24]:
            largura = max(10, 150 * x["total"] / maximo)
            cor = GREEN if x["pct"] == 100 else (AMBER if x["pct"] > 0 else colors.HexColor("#CBD5E1"))
            ep = f" · {x['endpoints']} ep" if x.get("endpoints") else ""
            linhas.append([
                Paragraph(f"<b>{x['label']}</b>", st["body"]),
                _bar(x["pct"], width=largura, cor=cor),
                Paragraph(f"{x['done']}/{x['total']} cards{ep} · {x['pct']}%", st["small"]),
            ])
            for sub in x.get("submodules", [])[:6]:
                largura_s = max(8, 110 * sub["total"] / maximo)
                cor_s = GREEN if sub["pct"] == 100 else (AMBER if sub["pct"] > 0 else colors.HexColor("#CBD5E1"))
                ep_s = f" · {sub['endpoints']} ep" if sub.get("endpoints") else ""
                linhas.append([
                    Paragraph(f"&nbsp;&nbsp;&nbsp;{sub['label']} <font color='#9CA3AF'>({sub['name']})</font>",
                              st["small"]),
                    _bar(sub["pct"], width=largura_s, height=5, cor=cor_s),
                    Paragraph(f"{sub['done']}/{sub['total']}{ep_s} · {sub['pct']}%", st["small"]),
                ])
        t = Table(linhas, colWidths=[52 * mm, 78 * mm, 44 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, BORDER),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#9CA3AF")),
        ]))
        flow.append(t)
        if len(mods) > 24:
            flow.append(Paragraph(f"+ {len(mods) - 24} módulo(s) não exibidos", st["small"]))
        if dims.get("discontinued"):
            fora = " · ".join(
                f"{x['label']} ({x['total']} cards"
                + (f" / {x['endpoints']} ep" if x.get("endpoints") else "")
                + f") — {x.get('reason', '')}"
                for x in dims["discontinued"]
            )
            flow.append(Spacer(1, 1.5 * mm))
            flow.append(Paragraph(f"<b>Fora de escopo:</b> {fora}", st["small"]))

    # ---------- sprints / plataformas / natureza (dimensões separadas) ----------
    sprints = dims.get("sprints", [])
    plataformas = dims.get("platforms", [])
    natureza = dims.get("process", [])
    if sprints or plataformas or natureza:
        _titulo(flow, "Sprints, plataformas e natureza", st)
        flow.append(Paragraph(
            "Estas dimensões não são módulos: sprint é o ciclo, plataforma é onde roda "
            "e natureza é o tipo de trabalho. Ficam fora do progresso por módulo.",
            st["small"],
        ))
        flow.append(Spacer(1, 1.5 * mm))

        def _bloco(titulo: str, itens: list[dict], mostrar_pct: bool = True):
            dados = [[Paragraph(f"<b>{titulo}</b>", st["small"]), Paragraph("", st["small"])]]
            for it in itens[:10]:
                valor = (f"{it['done']}/{it['total']} — {it['pct']}%" if mostrar_pct
                         else f"{it['done']}/{it['total']}")
                dados.append([Paragraph(it["label"], st["body"]), Paragraph(valor, st["small"])])
            t = Table(dados, colWidths=[40 * mm, 42 * mm])
            t.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, BORDER),
            ]))
            return t

        colunas = []
        if sprints:
            colunas.append(_bloco("Por sprint", sprints))
        if plataformas:
            colunas.append(_bloco("Por plataforma", plataformas, mostrar_pct=False))
        if natureza:
            colunas.append(_bloco("Por natureza", natureza))
        grid = Table([colunas], colWidths=[56 * mm] * len(colunas))
        grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        flow.append(grid)

    # ---------- por coluna (tabela) ----------
    _titulo(flow, "Cards por coluna", st)
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

    # ---------- por responsável (barras) ----------
    _titulo(flow, "Por responsável", st)
    flow.append(_tabela_barra(
        [(p["nome"], p["done"], p["total"], p["pct"]) for p in m["por_pessoa"][:12]],
        st,
        cor_fn=lambda nome: colors.HexColor("#9CA3AF") if nome == "Sem responsável" else ACCENT,
    ))

    # ---------- daily ----------
    d = m["daily"]
    if d["total"]:
        _titulo(flow, "Daily do projeto", st)
        tipos = ", ".join(f"{k}: {v}" for k, v in sorted(d["por_tipo"].items()))
        horas = round(d["minutos"] / 60, 1)
        flow.append(Paragraph(
            f"{d['total']} registro(s) em {d['dias']} dia(s) · {horas}h registradas · {tipos}",
            st["body"],
        ))
        if d["ultimos"]:
            flow.append(Paragraph("Últimos dias: " + ", ".join(d["ultimos"]), st["small"]))

    flow.append(Spacer(1, 5 * mm))
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
