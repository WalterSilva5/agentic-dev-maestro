"""Dimensões de agrupamento do projeto: módulo, submódulo, sprint, plataforma, tag.

Nem toda label é "módulo". No projeto da migração convivem, na mesma tabela de
labels, coisas de naturezas diferentes:

- **módulo**     — `cashier`, `config`, `financeiro`   (unidade de entrega)
- **submódulo / onda** — `cfg-e1`, `fin-e2`, `onda-1`  (pacote dentro do módulo)
- **sprint**     — `sprint-1` … `sprint-5`
- **plataforma** — `vm`, `var3-app`, `var-mobile`, `service`, `engine` (onde roda)
- **processo**   — `fundacao`, `infra`, `bug`, `despriorizado` (natureza/estado)

Misturar tudo em "por módulo" distorce as métricas. Este módulo classifica as
labels e agrega cada dimensão separadamente, para a UI, o PDF e os agentes.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Classificação
# ---------------------------------------------------------------------------

# Módulos canônicos (unidade de entrega da migração) -> rótulo de exibição.
MODULES: dict[str, str] = {
    "auth": "Auth",
    "cashier": "Cashier",
    "cliente": "Cliente",
    "config": "Config",
    "financeiro": "Financeiro",
    "troca": "Troca",
    "venda": "Venda",
    "voucher": "Voucher",
    "tef": "TEF",
    "acordo": "Acordo",
    "monitor": "Monitor",
    "estatisticas": "Estatísticas",
    "batch": "Batch",
    "abend": "Abend",
    "crm": "CRM",
    "tudoav": "TudoAV",
    "cobransaas": "CobranSaaS",
    "nfce": "NFC-e",
    "carteira-digital": "Carteira Digital",
}

# Prefixos de submódulo (`cfg-e1`) -> módulo dono.
SUBMODULE_PREFIXES: dict[str, str] = {
    "cfg": "config",
    "fin": "financeiro",
    "tro": "troca",
    "ven": "venda",
    "csh": "cashier",
    "cli": "cliente",
    "aut": "auth",
    "tcf": "config",
}

# `onda-N` é a sub-entrega (onda) do cashier no projeto da migração.
WAVE_MODULE = "cashier"

PLATFORM_LABELS = {
    "vm", "service", "engine", "enginefiscal", "var3-app", "var3_app",
    "var-mobile", "var_mobile", "tesouraria", "tesouraria-api",
    "app", "mobile", "desktop", "web",
}

PROCESS_LABELS = {
    "fundacao", "fundação", "infra", "bug", "bugs", "hotfix",
    "despriorizado", "debt", "tech-debt", "techdebt", "divida-tecnica",
    "p0", "p1", "p2", "melhoria", "refactor",
}

_SPRINT_RE = re.compile(r"^sprint[-_ ]?(\d+)$", re.IGNORECASE)
_SUBMODULE_RE = re.compile(r"^([a-z]{2,4})[-_ ]?e(\d+)$", re.IGNORECASE)
_WAVE_RE = re.compile(r"^onda[-_ ]?(\d+)$", re.IGNORECASE)

# rótulos legíveis das naturezas
PROCESS_LABELS_PT = {
    "fundacao": "Fundação",
    "fundação": "Fundação",
    "infra": "Infra",
    "bug": "Bug",
    "bugs": "Bug",
    "hotfix": "Hotfix",
    "despriorizado": "Despriorizado",
    "debt": "Dívida técnica",
    "tech-debt": "Dívida técnica",
    "techdebt": "Dívida técnica",
    "divida-tecnica": "Dívida técnica",
    "p0": "P0",
    "p1": "P1",
    "p2": "P2",
    "melhoria": "Melhoria",
    "refactor": "Refactor",
}


def classify_label(nome: str) -> dict:
    """Classifica uma label em uma das dimensões.

    Retorna `{kind, module, code, label, order}` onde `kind` é
    `MODULE | SUBMODULE | SPRINT | PLATFORM | PROCESS | OTHER`.
    """
    bruto = (nome or "").strip()
    chave = bruto.lower()

    if not chave:
        return {"kind": "OTHER", "module": None, "code": bruto, "label": bruto, "order": 99}

    if chave in MODULES:
        return {"kind": "MODULE", "module": chave, "code": chave,
                "label": MODULES[chave], "order": 0}

    m = _SPRINT_RE.match(chave)
    if m:
        return {"kind": "SPRINT", "module": None, "code": chave,
                "label": f"Sprint {m.group(1)}", "order": int(m.group(1))}

    m = _WAVE_RE.match(chave)
    if m:
        return {"kind": "SUBMODULE", "module": WAVE_MODULE, "code": chave,
                "label": f"Onda {m.group(1)}", "order": int(m.group(1))}

    m = _SUBMODULE_RE.match(chave)
    if m:
        prefixo, numero = m.group(1).lower(), m.group(2)
        modulo = SUBMODULE_PREFIXES.get(prefixo)
        if modulo:
            return {"kind": "SUBMODULE", "module": modulo, "code": chave,
                    "label": f"E{numero}", "order": int(numero)}

    if chave in PLATFORM_LABELS:
        return {"kind": "PLATFORM", "module": None, "code": chave,
                "label": bruto, "order": 0}

    if chave in PROCESS_LABELS:
        return {"kind": "PROCESS", "module": None, "code": chave,
                "label": PROCESS_LABELS_PT.get(chave, bruto), "order": 0}

    return {"kind": "OTHER", "module": None, "code": chave, "label": bruto, "order": 99}


# ---------------------------------------------------------------------------
# Agregação
# ---------------------------------------------------------------------------


def _pct(done: int, total: int) -> int:
    return round(done / total * 100) if total else 0


def aggregate_dimensions(tasks, done_ids) -> dict:
    """Agrupa as tarefas por dimensão, sem misturar módulo com sprint/tag.

    - `modules`: cada módulo com seus submódulos/ondas aninhados
    - `sprints`, `platforms`, `process`, `other`: listas independentes
    - `unlabeled`: cards sem nenhuma label de módulo (para métricas honestas)
    """
    total_cards = len(tasks)

    # módulo -> tarefas (inclui quem só tem submódulo/onda)
    por_modulo: dict[str, set] = {k: set() for k in MODULES}
    sub_por_modulo: dict[str, dict[str, set]] = {k: {} for k in MODULES}
    sprints: dict[str, set] = {}
    plataformas: dict[str, set] = {}
    processos: dict[str, set] = {}
    outras: dict[str, set] = {}
    com_modulo: set = set()

    for t in tasks:
        for lb in t.labels:
            info = classify_label(lb.name)
            kind = info["kind"]
            if kind == "MODULE":
                por_modulo.setdefault(info["module"], set()).add(t.id)
                com_modulo.add(t.id)
            elif kind == "SUBMODULE":
                mod = info["module"]
                por_modulo.setdefault(mod, set()).add(t.id)
                com_modulo.add(t.id)
                sub_por_modulo.setdefault(mod, {}).setdefault(info["code"], set()).add(t.id)
            elif kind == "SPRINT":
                sprints.setdefault(info["code"], set()).add(t.id)
            elif kind == "PLATFORM":
                plataformas.setdefault(info["code"], set()).add(t.id)
            elif kind == "PROCESS":
                processos.setdefault(info["code"], set()).add(t.id)
            else:
                outras.setdefault(info["code"], set()).add(t.id)

    def _item(code: str, ids: set, rotulo: str | None = None) -> dict:
        done = sum(1 for t in tasks if t.id in ids and t.column_id in done_ids)
        return {"name": code, "label": rotulo or code, "total": len(ids),
                "done": done, "pct": _pct(done, len(ids))}

    modulos = []
    for chave, ids in por_modulo.items():
        if not ids:
            continue
        subs = [
            _item(cod, sub_ids, classify_label(cod).get("label") or cod)
            for cod, sub_ids in sorted(
                sub_por_modulo.get(chave, {}).items(),
                key=lambda kv: classify_label(kv[0]).get("order", 0),
            )
        ]
        item = _item(chave, ids, MODULES.get(chave, chave))
        item["submodules"] = subs
        item["submodules_total"] = sum(s["total"] for s in subs)
        modulos.append(item)

    def _lista(fonte: dict[str, set], rotulos: dict[str, str] | None = None) -> list[dict]:
        itens = [
            _item(cod, ids, (rotulos or {}).get(cod))
            for cod, ids in fonte.items()
        ]
        itens.sort(key=lambda x: (-x["total"], x["name"]))
        return itens

    # sprints ordenadas por número e com rótulo legível ("Sprint 1")
    sprints_lista = _lista(
        sprints, {cod: classify_label(cod)["label"] for cod in sprints}
    )
    sprints_lista.sort(key=lambda x: (
        classify_label(x["name"]).get("order", 0), x["name"]
    ))

    modulos.sort(key=lambda x: (-x["total"], x["label"]))

    return {
        "cards": total_cards,
        "modules": modulos,
        "sprints": sprints_lista,
        "platforms": _lista(plataformas),
        "process": _lista(processos, PROCESS_LABELS_PT),
        "other": _lista(outras),
        "unlabeled": {
            "total": total_cards - len(com_modulo),
            "done": sum(
                1 for t in tasks
                if t.id not in com_modulo and t.column_id in done_ids
            ),
        },
        "with_module": len(com_modulo),
    }
