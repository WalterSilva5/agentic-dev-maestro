"""Coach proativo: gera dicas curtas e acionáveis ao longo do dia a partir do
estado atual do trabalho (board + TODOs), usando o provedor de IA ativo.

Usado tanto pelo desktop (dica periódica em card flutuante) quanto pela API
(`GET /api/coach/tip`). Mantém o prompt curto para ser barato e não intrusivo.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel

logger = logging.getLogger("maestro.coach")


class _TipOut(BaseModel):
    tip: str = ""
    category: str = ""   # foco | organização | risco | pausa | motivação


_SYSTEM = (
    "Você é um copiloto de produtividade para uma pessoa desenvolvedora. Com base no "
    "ESTADO ATUAL do trabalho, dê UMA única dica curta, específica e acionável para os "
    "próximos minutos — pode ser foco no que importa, organização do board, um risco/"
    "bloqueio a tratar, ou uma pausa saudável quando fizer sentido. No máximo 2 frases, "
    "direto, em português do Brasil. Não invente tarefas que não existem, não repita "
    "dicas óbvias nem dicas recentes já dadas."
)

_PROMPT = (
    "ESTADO ATUAL:\n{context}\n\n{recent}"
    "Responda SOMENTE com JSON no formato:\n"
    '{{"tip": "sua dica curta e acionável", '
    '"category": "foco|organização|risco|pausa|motivação"}}'
)


STUCK_DAYS = 3          # tarefa em andamento sem alteração há N dias = "parada"
HIGH_WIP = 4            # nº de tarefas em andamento a partir do qual o WIP é "alto"


def _active_tasks(session):
    from maestro_local.db.models import Task
    return [t for t in session.query(Task).filter(Task.deleted_at.is_(None)).all()
            if t.archived_at is None]


def _stuck_tasks(session, days: int = STUCK_DAYS):
    """Tarefas em andamento (não concluídas, fora do backlog) sem alteração há N dias."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    return [t for t in _active_tasks(session)
            if t.column and not t.column.is_done and (t.column.order or 0) > 0
            and t.updated_at and t.updated_at < cutoff]


def _overdue_todos(session):
    from datetime import datetime
    from maestro_local.db.models import Todo
    now = datetime.now()
    todos = session.query(Todo).filter(
        Todo.done.is_(False), Todo.due_at.isnot(None), Todo.due_at <= now).all()
    return [td for td in todos if not (td.snoozed_until and td.snoozed_until > now)]


def has_strong_signal(session) -> bool:
    """Há algo concreto que justifique uma dica imediata (evento)?"""
    return bool(_overdue_todos(session)) or bool(_stuck_tasks(session))


def build_context(session) -> str:
    """Resumo compacto do estado do trabalho para alimentar a dica."""
    from datetime import datetime

    from maestro_local.db.models import Todo

    now = datetime.now()
    active = _active_tasks(session)
    doing = [t for t in active
             if t.column and not t.column.is_done and (t.column.order or 0) > 0]
    backlog = [t for t in active if t.column and (t.column.order or 0) == 0]
    todos = session.query(Todo).filter(Todo.done.is_(False)).all()
    overdue = _overdue_todos(session)
    stuck = _stuck_tasks(session)

    lines = [f"Hora atual: {now.strftime('%H:%M')}."]
    lines.append(f"Tarefas em andamento ({len(doing)}):")
    lines += [f"  - [{t.type}] {t.title} (coluna: {t.column.name if t.column else '-'})"
              for t in doing[:12]] or ["  (nenhuma)"]
    if len(doing) >= HIGH_WIP:
        lines.append(f"WIP alto: {len(doing)} tarefas em andamento ao mesmo tempo.")
    if stuck:
        lines.append(f"Tarefas paradas há {STUCK_DAYS}+ dias ({len(stuck)}):")
        lines += [f"  - {t.title}" for t in stuck[:6]]
    lines.append(f"Backlog: {len(backlog)} tarefa(s).")
    lines.append(f"TODOs pendentes: {len(todos)} (vencidos agora: {len(overdue)}).")
    lines += [f"  - {td.title}" for td in overdue[:8]]
    return "\n".join(lines)


def generate_tip(context: str, recent_tips: list[str] | None = None) -> dict:
    """Gera UMA dica proativa a partir do contexto. Levanta se a IA falhar."""
    from maestro_local.ai.llm import invoke_json

    recent = ""
    if recent_tips:
        recent = ("Dicas recentes (NÃO repita):\n"
                  + "\n".join(f"- {r}" for r in recent_tips[-5:]) + "\n\n")
    parsed = invoke_json(
        [("system", _SYSTEM), ("user", _PROMPT.format(context=context, recent=recent))],
        schema=_TipOut, temperature=0.5)
    if not isinstance(parsed, dict):
        raise ValueError("Resposta da IA não é um objeto JSON")
    return {
        "tip": str(parsed.get("tip") or "").strip(),
        "category": str(parsed.get("category") or "").strip(),
    }
