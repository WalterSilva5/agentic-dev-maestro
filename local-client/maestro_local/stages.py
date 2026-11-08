"""Quem **chegou** em cada estágio do board (métrica cumulativa), e o corte por grupo.

Duas perguntas diferentes:

- **está em** um estágio  -> `Task.column_id == coluna` (foto de agora)
- **chegou** em um estágio -> já passou por ali alguma vez

"Chegou" é o que interessa para acompanhar fluxo: um card em `Dev Review` já
passou por `Dev Review`, mesmo que hoje não esteja mais lá. O fluxo é
`Doing → Dev Review → Dev Box → In Test → … → Done`, então **Dev Box é o
último estado do desenvolvimento** (dev concluído, aguardando teste). Duas
fontes combinadas:

1. **ordem das colunas** — o fluxo é linear, então quem está numa coluna de
   ordem N já passou por todas as de ordem menor (`Dev Review` antes de
   `Dev Box`; `Rework`, `Verified`, `Accepted` e `Done` depois de `In Test`);
2. **histórico de movimentação** (`activity_log`, action `moved`, detalhe
   `Origem -> Destino`) — pega movimentos fora de ordem e saltos.

O corte por grupo usa **um grupo por card** (o módulo principal, na ordem do
plano), para que a soma dos grupos feche em 100% — a divisão é feita por maior
resto, então nunca fica 99% nem 101%.
"""
from __future__ import annotations

import re
import unicodedata

from maestro_local.dimensions import MODULES, classify_label
from maestro_local.module_plan import PLAN_ORDER

SEM_GRUPO = "sem-modulo"
SEM_GRUPO_LABEL = "Sem módulo"


def slug(nome: str) -> str:
    """'Dev Box' -> 'dev-box'; 'In Test' -> 'in-test'."""
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def pct_split(valores: list[int]) -> list[int]:
    """Percentuais inteiros que somam exatamente 100 (método do maior resto).

    Divide `valores` pelo total e distribui o resto da divisão entre os maiores
    restos, de modo que a soma seja sempre 100 quando o total > 0.
    """
    total = sum(valores)
    if total <= 0:
        return [0 for _ in valores]
    exatos = [v * 100 / total for v in valores]
    pisos = [int(x) for x in exatos]
    resto = 100 - sum(pisos)
    ordem = sorted(
        range(len(valores)),
        key=lambda i: (exatos[i] - pisos[i], valores[i]),
        reverse=True,
    )
    for i in ordem[: max(0, resto)]:
        pisos[i] += 1
    return pisos


def primary_group(labels) -> str:
    """Módulo principal do card (um só), para o corte somar 100%.

    Entre os módulos citados (diretos ou via sub-entrega), escolhe o primeiro na
    ordem do plano. Sem label de módulo devolve `sem-modulo`.
    """
    modulos = set()
    for nome in labels or []:
        info = classify_label(nome)
        if info["kind"] in ("MODULE", "SUBMODULE") and info["module"]:
            modulos.add(info["module"])
    if not modulos:
        return SEM_GRUPO
    for chave in PLAN_ORDER:
        if chave in modulos:
            return chave
    return sorted(modulos)[0]


def _colunas_do_historico(linhas) -> dict[int, set[str]]:
    """`activity_log` -> {task_id: {colunas por onde passou}}.

    O detalhe é `Origem -> Destino`; as **duas** pontas contam: sair de uma
    coluna prova que a tarefa esteve nela (inclusive quando ela voltou depois).
    """
    passou: dict[int, set[str]] = {}
    for task_id, detail in linhas:
        if not detail or "->" not in detail:
            continue
        origem, destino = detail.split("->", 1)
        for nome in (origem.strip(), destino.strip()):
            if nome:
                passou.setdefault(task_id, set()).add(slug(nome))
    return passou


def compute_stages(tasks, columns, history_rows=None) -> dict:
    """Chegada cumulativa por coluna + distribuição por grupo em cada uma.

    `columns` aceita objetos com `id`, `name`, `order`, `is_done`;
    `history_rows` é uma lista de `(task_id, detail)` de `activity_log`.
    """
    # tarefa local (lembrete pessoal) não entra em métrica nenhuma
    locais = sum(1 for t in tasks if getattr(t, "is_local", False))
    tasks = [t for t in tasks if not getattr(t, "is_local", False)]

    ordenadas = sorted(columns, key=lambda c: (c.order, c.id))
    por_ordem = {c.order: c for c in ordenadas}
    historico = _colunas_do_historico(history_rows or [])

    total = len(tasks)
    chegou: dict[str, set[int]] = {slug(c.name): set() for c in ordenadas}
    atual: dict[str, set[int]] = {slug(c.name): set() for c in ordenadas}
    grupo_do_card: dict[int, str] = {}

    for t in tasks:
        col = por_ordem.get(t.column.order) if getattr(t, "column", None) else None
        nome_atual = slug(col.name) if col else None
        if col:
            atual.setdefault(nome_atual, set()).add(t.id)

        # 1) tudo até a coluna atual (fluxo linear)
        if col:
            for outra in ordenadas:
                if outra.order <= col.order:
                    chegou[slug(outra.name)].add(t.id)

        # 2) movimentos registrados (inclui voltar/saltar)
        for nome_destino in historico.get(t.id, ()):
            if nome_destino in chegou:
                chegou[nome_destino].add(t.id)

        grupo_do_card[t.id] = primary_group([lb.name for lb in t.labels])

    linhas = []
    for c in ordenadas:
        chave = slug(c.name)
        ids = chegou[chave]
        linhas.append({
            "id": c.id,
            "name": c.name,
            "stage": chave,
            "order": c.order,
            "isDone": bool(c.is_done),
            "reached": len(ids),
            "current": len(atual[chave]),
        })
    # % do board que chegou / que está agora (não é divisão em partes)
    for x in linhas:
        x["pct"] = round(x["reached"] / total * 100) if total else 0
        x["pctCurrent"] = round(x["current"] / total * 100) if total else 0

    # distribuição por grupo, por estágio (soma 100%)
    grupos: list[tuple[str, str]] = [
        (m, MODULES.get(m, m)) for m in PLAN_ORDER
    ] + [(SEM_GRUPO, SEM_GRUPO_LABEL)]
    breakdown = {}
    for x in linhas:
        ids = chegou[x["stage"]]
        if not ids:
            breakdown[x["stage"]] = []
            continue
        contagem = {chave: 0 for chave, _rotulo in grupos}
        for tid in ids:
            chave_grupo = grupo_do_card.get(tid, SEM_GRUPO)
            contagem[chave_grupo] = contagem.get(chave_grupo, 0) + 1
        itens = [
            {"group": chave, "label": rotulo, "total": contagem.get(chave, 0)}
            for chave, rotulo in grupos
            if contagem.get(chave, 0) > 0
        ]
        itens.sort(key=lambda y: (-y["total"], y["label"]))
        for item, p in zip(itens, pct_split([y["total"] for y in itens])):
            item["pct"] = p
        breakdown[x["stage"]] = itens

    # distribuição do board inteiro (mesma lógica, para comparar)
    contagem_total: dict[str, int] = {}
    for tid, chave in grupo_do_card.items():
        contagem_total[chave] = contagem_total.get(chave, 0) + 1
    board = [
        {"group": chave,
         "label": MODULES.get(chave, SEM_GRUPO_LABEL) if chave != SEM_GRUPO else SEM_GRUPO_LABEL,
         "total": contagem_total.get(chave, 0)}
        for chave in [*PLAN_ORDER, SEM_GRUPO]
        if contagem_total.get(chave, 0) > 0
    ]
    board.sort(key=lambda y: (-y["total"], y["label"]))
    for item, p in zip(board, pct_split([y["total"] for y in board])):
        item["pct"] = p

    return {
        "total": total,
        "local": locais,
        "stages": linhas,
        "breakdown": breakdown,
        "board": board,
    }
