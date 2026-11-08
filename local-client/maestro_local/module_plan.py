"""Plano oficial de módulos e sub-entregas da migração.

Fonte: `docs-migração/diagrams/acompanhamento/10-progresso-entrega.svg`
(escopo 156 endpoints, 17 módulos; `nfce` e `carteira-digital` descontinuados)
e `tasks-migração-walter/sub-entregas/00-plano-geral.md`.

Serve para nomear as sub-entregas (`cfg-e1` → "E1 · loja"), mostrar módulos
planejados que ainda não têm card (0/26) e comparar cards × endpoints.
"""
from __future__ import annotations

# label exibido, endpoints no escopo e sub-entregas (tag, rótulo, endpoints)
MODULE_PLAN: dict[str, dict] = {
    "auth": {"label": "auth", "endpoints": 9, "deliveries": []},
    "cliente": {"label": "cliente", "endpoints": 9, "deliveries": []},
    "config": {
        "label": "config",
        "endpoints": 26,
        "deliveries": [
            ("cfg-e1", "E1 · loja", 4),
            ("cfg-e2", "E2 · monitor e estação", 5),
            ("cfg-e3", "E3 · parâmetros e utilitários", 15),
            ("cfg-e4", "E4 · porta e ambiente", 1),
        ],
    },
    "cashier": {
        "label": "cashier",
        "endpoints": 32,
        "deliveries": [
            ("onda-1", "O1 · abrir e carregar", 13),
            ("onda-2", "O2 · movimentar", 11),
            ("onda-3", "O3 · fechar e acertar", 8),
        ],
    },
    "financeiro": {
        "label": "financeiro",
        "endpoints": 20,
        "deliveries": [
            ("fin-e1", "E1 · consultas e preço", 6),
            ("fin-e2", "E2 · adesão e termos", 8),
            ("fin-e3", "E3 · operação financeira", 6),
        ],
    },
    "troca": {
        "label": "troca",
        "endpoints": 19,
        "deliveries": [
            ("tro-e1", "E1 · consulta e seleção", 6),
            ("tro-e2", "E2 · montagem", 5),
            ("tro-e3", "E3 · NSU e de-para", 4),
            ("tro-e4", "E4 · fechamento", 4),
        ],
    },
    "venda": {
        "label": "venda",
        "endpoints": 10,
        "deliveries": [
            ("ven-e1", "E1 · origem e CPF", 3),
            ("ven-e2", "E2 · pagamento e benefícios", 4),
            ("ven-e3", "E3 · fechamento e TEF", 3),
        ],
    },
    "voucher": {"label": "voucher", "endpoints": 7, "deliveries": []},
    "tef": {"label": "tef", "endpoints": 5, "deliveries": []},
    "acordo": {"label": "acordo", "endpoints": 4, "deliveries": []},
    "monitor": {"label": "monitor", "endpoints": 4, "deliveries": []},
    "estatisticas": {"label": "estatisticas", "endpoints": 3, "deliveries": []},
    "abend": {"label": "abend", "endpoints": 2, "deliveries": []},
    "cobransaas": {"label": "cobransaas", "endpoints": 2, "deliveries": []},
    "tudoav": {"label": "tudoav", "endpoints": 2, "deliveries": []},
    "batch": {"label": "batch", "endpoints": 1, "deliveries": []},
    "crm": {"label": "crm", "endpoints": 1, "deliveries": []},
}

# Fora de escopo — não migrar (descontinuados no SVG).
DISCONTINUED = {
    "nfce": {"label": "nfce", "endpoints": 17, "motivo": "descontinuado"},
    "carteira-digital": {"label": "carteira-digital", "endpoints": 11, "motivo": "descontinuado"},
}

# Ordem do plano: agrupada por estágio, como no diagrama de acompanhamento.
PLAN_ORDER = [
    "auth", "cliente",
    "config",
    "cashier",
    "financeiro", "troca", "venda",
    "voucher", "tef", "acordo", "monitor", "estatisticas", "batch",
    "abend", "cobransaas", "tudoav", "crm",
]

TOTAL_ENDPOINTS = sum(m["endpoints"] for m in MODULE_PLAN.values())  # 156


def delivery_label(tag: str) -> str | None:
    """`cfg-e1` -> 'E1 · loja'; `onda-2` -> 'O2 · movimentar'."""
    chave = (tag or "").strip().lower()
    for mod in MODULE_PLAN.values():
        for codigo, rotulo, _n in mod["deliveries"]:
            if codigo == chave:
                return rotulo
    return None


def delivery_endpoints(tag: str) -> int | None:
    chave = (tag or "").strip().lower()
    for mod in MODULE_PLAN.values():
        for codigo, _rotulo, n in mod["deliveries"]:
            if codigo == chave:
                return n
    return None


def module_of_delivery(tag: str) -> str | None:
    chave = (tag or "").strip().lower()
    for nome, mod in MODULE_PLAN.items():
        for codigo, _rotulo, _n in mod["deliveries"]:
            if codigo == chave:
                return nome
    return None


def plan_summary() -> dict:
    return {
        "modules": len(MODULE_PLAN),
        "endpoints": TOTAL_ENDPOINTS,
        "with_deliveries": sum(1 for m in MODULE_PLAN.values() if m["deliveries"]),
        "deliveries": sum(len(m["deliveries"]) for m in MODULE_PLAN.values()),
    }
