"""Taxonomia de rótulos para agrupar cartões por módulo/submódulo.

Este módulo contém apenas nomes e ordem de exibição. Ele **não** contém metas,
contagens de endpoints, escopo planejado nem status de fora de escopo: as
métricas contam somente os cartões existentes no board.
"""
from __future__ import annotations

# label exibido e sub-entregas/subdivisões conhecidas (somente nomes)
MODULE_PLAN: dict[str, dict] = {
    "auth": {"label": "auth", "deliveries": []},
    "cliente": {"label": "cliente", "deliveries": []},
    "config": {
        "label": "config",
        "deliveries": [
            ("cfg-e1", "E1 · loja"),
            ("cfg-e2", "E2 · monitor e estação"),
            ("cfg-e3", "E3 · parâmetros e utilitários"),
            ("cfg-e4", "E4 · porta e ambiente"),
        ],
    },
    "cashier": {
        "label": "cashier",
        "deliveries": [
            ("onda-1", "O1 · abrir e carregar"),
            ("onda-2", "O2 · movimentar"),
            ("onda-3", "O3 · fechar e acertar"),
        ],
    },
    "financeiro": {
        "label": "financeiro",
        "deliveries": [
            ("fin-e1", "E1 · consultas e preço"),
            ("fin-e2", "E2 · adesão e termos"),
            ("fin-e3", "E3 · operação financeira"),
        ],
    },
    "troca": {
        "label": "troca",
        "deliveries": [
            ("tro-e1", "E1 · consulta e seleção"),
            ("tro-e2", "E2 · montagem"),
            ("tro-e3", "E3 · NSU e de-para"),
            ("tro-e4", "E4 · fechamento"),
        ],
    },
    "venda": {
        "label": "venda",
        "deliveries": [
            ("ven-e1", "E1 · origem e CPF"),
            ("ven-e2", "E2 · pagamento e benefícios"),
            ("ven-e3", "E3 · fechamento e TEF"),
        ],
    },
    "voucher": {"label": "voucher", "deliveries": []},
    "tef": {"label": "tef", "deliveries": []},
    "acordo": {"label": "acordo", "deliveries": []},
    "monitor": {"label": "monitor", "deliveries": []},
    "estatisticas": {"label": "estatisticas", "deliveries": []},
    "abend": {"label": "abend", "deliveries": []},
    "cobransaas": {"label": "cobransaas", "deliveries": []},
    "tudoav": {"label": "tudoav", "deliveries": []},
    "batch": {"label": "batch", "deliveries": []},
    "crm": {"label": "crm", "deliveries": []},
    "nfce": {"label": "nfce", "deliveries": []},
    "carteira-digital": {"label": "carteira-digital", "deliveries": []},
}

# Ordem de exibição dos grupos conhecidos.
PLAN_ORDER = [
    "auth", "cliente",
    "config",
    "cashier",
    "financeiro", "troca", "venda",
    "voucher", "tef", "acordo", "monitor", "estatisticas", "batch",
    "abend", "cobransaas", "tudoav", "crm",
    "nfce", "carteira-digital",
]


def delivery_label(tag: str) -> str | None:
    """`cfg-e1` -> 'E1 · loja'; `onda-2` -> 'O2 · movimentar'."""
    chave = (tag or "").strip().lower()
    for mod in MODULE_PLAN.values():
        for codigo, rotulo in mod["deliveries"]:
            if codigo == chave:
                return rotulo
    return None
