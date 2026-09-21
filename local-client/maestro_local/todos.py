"""Consultas de TODOs compartilhadas entre telas.

A tela da pausa para os olhos mostra a lista de pendências em aberto; a
ordenação fica aqui para não haver duas versões dela.
"""
from __future__ import annotations

from datetime import datetime

from maestro_local.db.models import Todo, get_session

_PRIORIDADE_ORDEM = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def todos_abertos(limite: int = 30) -> list[dict]:
    """TODOs não concluídos, os mais urgentes primeiro.

    Devolve dicts para quem chama não segurar objetos da sessão.
    """
    s = get_session()
    try:
        itens = s.query(Todo).filter(Todo.done == False).all()  # noqa: E712
        itens.sort(key=lambda td: (
            _PRIORIDADE_ORDEM.get(td.priority or "MEDIUM", 2),
            td.due_at or datetime.max,
            td.sort_order or 0,
        ))
        return [{"id": td.id, "text": td.text, "priority": td.priority or "MEDIUM",
                 "due_at": td.due_at} for td in itens[:limite]]
    finally:
        s.close()
