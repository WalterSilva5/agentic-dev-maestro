"""Formato do doc de daily do projeto (markdown) — parser e gerador.

O time mantém um arquivo por dia no vault, em `daily/YYYY-MM/DD-MM-YYYY - Daily - <tema>.md`,
com esta forma::

    # Daily - 04/11/2026 — config E3/E4 na VM (tema)

    <parágrafo de contexto>

    ## Itens trabalhados

    ### `13972` — modo de conexão do banco
    - bullet
    - bullet

    ## Estado da sprint

    <texto>

    ## Pendências

    - bullet

Este módulo converte entre esse markdown e a lista de registros do Maestro
(`ProjectDailyEntry`), para permitir importar o histórico e exporter de volta
no mesmo formato.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date as _date
from datetime import datetime

SECTIONS = ("INTRO", "ITEMS", "SPRINT", "PENDING", "OTHER")

# títulos de seção aceitos (variações que existem no vault)
_SECTION_TITLES = {
    "itens trabalhados": "ITEMS",
    "itens": "ITEMS",
    "estado da sprint": "SPRINT",
    "estado do board": "SPRINT",
    "pendências": "PENDING",
    "pendencias": "PENDING",
    "pendente": "PENDING",
    "pendências / próximos passos": "PENDING",
    "pendencias / proximos passos": "PENDING",
    "próximos passos": "PENDING",
    "proximos passos": "PENDING",
}

_SECTION_HEADINGS = {
    "SPRINT": "Estado da sprint",
    "PENDING": "Pendências",
}

_DATE_BR = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_DATE_DASH = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
_DATE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
# aceita "# Daily - <data> — tema", "# Daily — <data> (contexto)", "# Daily - <data>"
_TITLE_LINE = re.compile(
    r"^#\s*Daily\s*(?:[—–:-]+\s*)?(?P<rest>.*)$", re.IGNORECASE,
)
_CARD_IN_BACKTICKS = re.compile(r"`([A-Za-z]{1,10}-\d+|\d{4,})`")


@dataclass
class DailyBlock:
    """Um registro extraído/gerado para o doc."""

    section: str = "ITEMS"
    title: str = ""
    body: str = ""
    kind: str = "WORK"
    author: str | None = None
    minutes: int | None = None
    task_code: str = ""
    sort_order: int = 0
    extra: dict = field(default_factory=dict)


def parse_date_br(text: str) -> str | None:
    """Aceita `04/11/2026`, `04-11-2026` e `2026-11-04` -> `2026-11-04`."""
    text = text or ""
    m = _DATE_BR.search(text)
    if m:
        d, mo, y = m.groups()
        try:
            return _date(int(y), int(mo), int(d)).isoformat()
        except ValueError:
            return None
    m = _DATE_DASH.search(text)
    if m:
        d, mo, y = m.groups()
        try:
            return _date(int(y), int(mo), int(d)).isoformat()
        except ValueError:
            return None
    m = _DATE_ISO.search(text)
    if m:
        y, mo, d = m.groups()
        try:
            return _date(int(y), int(mo), int(d)).isoformat()
        except ValueError:
            return None
    return None


def format_date_br(iso: str) -> str:
    """`2026-11-04` -> `04/11/2026`."""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
    except ValueError:
        return iso
    return d.strftime("%d/%m/%Y")


def _section_of(heading: str) -> str | None:
    key = (heading or "").strip().lower()
    return _SECTION_TITLES.get(key)


def parse_daily_markdown(content: str) -> tuple[str, str, list[DailyBlock]]:
    """Divide o markdown em (data_iso, tema_do_dia, blocos).

    Cada `###` de "Itens trabalhados" vira um bloco; cada bullet de
    "Pendências" vira um bloco; as demais seções viram um bloco único.
    """
    lines = (content or "").replace("\r\n", "\n").split("\n")

    day_iso = ""
    day_title = ""
    blocks: list[DailyBlock] = []

    section = "INTRO"
    section_heading = ""
    # buffer da seção corrente
    buf: list[str] = []
    current_item: DailyBlock | None = None

    def flush_text(target_section: str):
        """Fecha o buffer como um bloco de texto corrido."""
        nonlocal buf, current_item
        text = "\n".join(buf).strip()
        buf = []
        if current_item is not None:
            current_item.body = (current_item.body + ("\n" if current_item.body and text else "") + text).strip()
            current_item = None
            return
        if not text:
            return
        if target_section == "PENDING":
            # um bloco por bullet, mantendo as linhas de continuação juntas
            atual: list[str] = []
            for line in text.split("\n"):
                item = line.rstrip()
                if item.lstrip().startswith(("-", "*", "•")):
                    if atual:
                        blocks.append(DailyBlock(section="PENDING", title=section_heading,
                                                 body="\n".join(atual).strip(), kind="NOTE"))
                    atual = [item.lstrip()[1:].strip()]
                elif item.strip():
                    if atual:
                        atual.append(item.rstrip())
                    elif not atual:
                        atual = [item.strip()]
            if atual:
                blocks.append(DailyBlock(section="PENDING", title=section_heading,
                                         body="\n".join(atual).strip(), kind="NOTE"))
            return
        blocks.append(DailyBlock(section=target_section, title=section_heading,
                                 body=text, kind="NOTE"))

    for raw in lines:
        line = raw.rstrip()

        # título do dia
        if not blocks and line.startswith("# "):
            m = _TITLE_LINE.match(line)
            rest = (m.group("rest") if m else line.lstrip("# ")).strip()
            day_iso = parse_date_br(rest) or ""
            # remove a data e separadores do tema
            tema = re.sub(
                r"^\s*(?:\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\s*",
                "", rest,
            )
            tema = re.sub(r"^[—–:-]+\s*", "", tema).strip()
            day_title = tema
            section = "INTRO"
            continue

        # troca de seção `## ...`
        if line.startswith("## "):
            flush_text(section)
            heading = line[3:].strip()
            nova = _section_of(heading)
            section = nova or "OTHER"
            section_heading = heading
            if nova is None:
                buf = [f"## {heading}"]
            continue

        # `###` em outras seções pertence ao texto daquela seção
        if line.startswith("### ") and section != "ITEMS":
            buf.append(line)
            continue

        # sub-item `### ...` dentro de "Itens trabalhados" vira um item
        if line.startswith("### "):
            flush_text(section)
            heading = line[4:].strip()
            cards = _CARD_IN_BACKTICKS.findall(heading)
            current_item = DailyBlock(
                section="ITEMS",
                title=heading[:200],          # heading original (round-trip fiel)
                kind="WORK",
                task_code=(cards[0] if cards else ""),
            )
            blocks.append(current_item)
            buf = []
            continue

        buf.append(line)

    flush_text(section)

    # apara e ordena
    for i, b in enumerate(blocks):
        b.body = (b.body or "").strip()
        b.sort_order = i
    blocks = [b for b in blocks if b.body or b.title]

    # o tema do dia precisa sobreviver ao round-trip: guarda no bloco INTRO
    if day_title:
        intro = next((b for b in blocks if b.section == "INTRO"), None)
        if intro is not None:
            intro.title = intro.title or day_title[:200]
        else:
            blocks.insert(0, DailyBlock(
                section="INTRO", title=day_title[:200], body="", kind="NOTE", sort_order=-1,
            ))
            for i, b in enumerate(blocks):
                b.sort_order = i

    return day_iso, day_title, blocks


def render_daily_markdown(day_iso: str, title: str, blocks: list[DailyBlock]) -> str:
    """Gera o markdown no mesmo formato que o time usa no vault.

    Emite os blocos na ordem original e abre o cabeçalho `##` quando a seção
    muda, preservando o título original de cada seção (inclusive repetidas).
    """
    titulo_dia = f"# Daily - {format_date_br(day_iso)}"
    if title:
        titulo_dia += f" — {title}"

    ordenados = sorted(blocks, key=lambda x: (x.sort_order, x.id if hasattr(x, "id") else 0))

    out: list[str] = [titulo_dia, ""]
    secao_atual: str | None = None
    heading_atual: str | None = None

    for b in ordenados:
        sec = b.section or "ITEMS"

        if sec == "INTRO":
            corpo = (b.body or "").strip()
            if corpo:
                out.append(corpo)
                out.append("")
            secao_atual = "INTRO"
            continue

        if sec == "OTHER":
            # já traz o próprio `## ...` no corpo
            corpo = (b.body or "").strip()
            if corpo:
                out.append(corpo)
                out.append("")
            secao_atual = "OTHER"
            heading_atual = None
            continue

        if sec == "ITEMS":
            section_head = "Itens trabalhados"
            item_head = (b.title or "").strip()
            if not item_head:
                item_head = f"`{b.task_code}`" if b.task_code else (b.body or "").split("\n", 1)[0][:80]
            elif b.task_code and f"`{b.task_code}`" not in item_head:
                item_head = f"`{b.task_code}` — {item_head}"
        else:
            section_head = (b.title or "").strip() or _SECTION_HEADINGS.get(sec, "")
            item_head = ""

        if sec != secao_atual or section_head != heading_atual:
            out.append("## " + section_head)
            out.append("")
            secao_atual = sec
            heading_atual = section_head

        if sec == "ITEMS":
            out.append("### " + item_head)
            corpo = (b.body or "").strip()
            if corpo:
                out.append(corpo)
            out.append("")
        elif sec == "PENDING":
            corpo = re.sub(r"^[-*•]\s+", "", (b.body or "").strip())
            out.append("- " + corpo.strip())
        else:  # SPRINT e demais seções de texto
            corpo = (b.body or "").strip()
            if corpo:
                out.append(corpo)
                out.append("")

    if secao_atual == "PENDING":
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def suggested_filename(day_iso: str, title: str) -> str:
    """`DD-MM-YYYY - Daily - <tema>.md`, como no vault."""
    try:
        d = datetime.strptime(day_iso, "%Y-%m-%d").date()
        prefix = d.strftime("%d-%m-%Y")
        month_dir = d.strftime("%Y-%m")
    except ValueError:
        prefix, month_dir = day_iso, day_iso[:7]
    slug = (title or "daily").strip()
    for ch in '/\\:*?"<>|':
        slug = slug.replace(ch, "-")
    slug = re.sub(r"\s+", " ", slug).strip(" .")[:90] or "daily"
    return f"{prefix} - Daily - {slug}.md", month_dir
