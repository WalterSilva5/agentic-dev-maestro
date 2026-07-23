"""Ferramentas internas expostas ao agente estratégico.

Operam direto sobre o banco do workspace ativo (get_session), sem passar
pela API HTTP. Cada tool retorna texto/JSON simples para o modelo raciocinar.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from langchain_core.tools import tool

from maestro_local.db.models import (
    ActivityLog,
    BoardColumn,
    Comment,
    Document,
    MemoryEntry,
    Project,
    Task,
    Todo,
    get_session,
)


def _col_name(s, column_id):
    col = s.query(BoardColumn).get(column_id)
    return col.name if col else "?"


@tool
def list_projects() -> str:
    """Lista os projetos do workspace ativo com chave, nome e total de tarefas."""
    s = get_session()
    try:
        out = []
        for p in s.query(Project).all():
            total = s.query(Task).filter(Task.project_id == p.id, Task.deleted_at.is_(None)).count()
            out.append({"id": p.id, "key": p.key, "name": p.name, "tasks": total})
        return json.dumps(out, ensure_ascii=False) if out else "Nenhum projeto."
    finally:
        s.close()


@tool
def get_board_summary(project_id: int) -> str:
    """Resumo do board de um projeto: contagem de tarefas por coluna e títulos.

    Use para entender o estado atual do trabalho antes de sugerir ações.
    """
    s = get_session()
    try:
        project = s.query(Project).get(project_id)
        if not project:
            return f"Projeto {project_id} não encontrado."
        cols = s.query(BoardColumn).filter(BoardColumn.project_id == project_id).order_by(BoardColumn.order).all()
        lines = [f"Board do projeto {project.key} - {project.name}:"]
        for c in cols:
            tasks = s.query(Task).filter(
                Task.column_id == c.id, Task.deleted_at.is_(None)
            ).all()
            lines.append(f"\n[{c.name}] ({len(tasks)} tarefas)")
            for t in tasks:
                flags = []
                if t.requires_human:
                    flags.append("requer-dev")
                flag_str = f" ({', '.join(flags)})" if flags else ""
                lines.append(f"  - {project.key}-{t.number}: {t.title} [{t.priority}]{flag_str}")
        return "\n".join(lines)
    finally:
        s.close()


@tool
def list_tasks(project_id: int, priority: str = "", column_name: str = "") -> str:
    """Lista tarefas de um projeto, com filtros opcionais por prioridade
    (LOW/MEDIUM/HIGH/URGENT) e por nome da coluna."""
    s = get_session()
    try:
        q = s.query(Task).filter(Task.project_id == project_id, Task.deleted_at.is_(None))
        if priority:
            q = q.filter(Task.priority == priority.upper())
        tasks = q.all()
        project = s.query(Project).get(project_id)
        key = project.key if project else "?"
        out = []
        for t in tasks:
            cname = _col_name(s, t.column_id)
            if column_name and column_name.lower() not in cname.lower():
                continue
            out.append({
                "code": f"{key}-{t.number}",
                "title": t.title,
                "type": t.type,
                "priority": t.priority,
                "column": cname,
                "requiresHuman": bool(t.requires_human),
            })
        return json.dumps(out, ensure_ascii=False) if out else "Nenhuma tarefa encontrada."
    finally:
        s.close()


@tool
def request_task_review(task_code: str, reason: str) -> str:
    """Solicita revisão humana de uma tarefa: cria uma tarefa de revisão (CHORE,
    requer-dev, prioridade HIGH) vinculada e move a original para a coluna de
    Revisão se existir. task_code no formato KEY-N (ex: MST-3)."""
    s = get_session()
    try:
        if "-" not in task_code:
            return "Código inválido. Use o formato KEY-N, ex: MST-3."
        key, _, num = task_code.rpartition("-")
        project = s.query(Project).filter(Project.key == key).first()
        if not project:
            return f"Projeto {key} não encontrado."
        try:
            number = int(num)
        except ValueError:
            return "Número da tarefa inválido."
        original = s.query(Task).filter(
            Task.project_id == project.id, Task.number == number, Task.deleted_at.is_(None)
        ).first()
        if not original:
            return f"Tarefa {task_code} não encontrada."

        # Coluna de revisão (ou a primeira que contenha 'revis')
        review_col = s.query(BoardColumn).filter(
            BoardColumn.project_id == project.id,
            BoardColumn.name.ilike("%revis%"),
        ).first()

        project.task_seq = (project.task_seq or 0) + 1
        rnum = project.task_seq
        col_id = review_col.id if review_col else original.column_id
        review_task = Task(
            project_id=project.id,
            column_id=col_id,
            number=rnum,
            title=f"Revisar {task_code}: {original.title}",
            description=f"Revisão solicitada pelo agente estratégico.\n\nMotivo: {reason}\n\nTarefa de origem: {task_code}",
            type="CHORE",
            priority="HIGH",
            requires_human=True,
        )
        s.add(review_task)
        s.flush()

        if review_col and original.column_id != review_col.id:
            original.column_id = review_col.id
            s.add(ActivityLog(entity_type="task", entity_id=original.id,
                              action="moved", detail=f"Movido para {review_col.name} (revisão solicitada)"))

        s.add(ActivityLog(entity_type="task", entity_id=review_task.id,
                          action="created", detail=f"Tarefa de revisão de {task_code} criada pelo agente"))
        s.commit()
        return (f"Revisão solicitada: criada {project.key}-{rnum} (requer-dev, HIGH) "
                f"vinculada a {task_code}" + (f" e {task_code} movida para {review_col.name}." if review_col else "."))
    except Exception as e:  # noqa: BLE001
        s.rollback()
        return f"Erro ao solicitar revisão: {e}"
    finally:
        s.close()


@tool
def add_task_comment(task_code: str, comment: str, comment_type: str = "NOTE") -> str:
    """Adiciona um comentário a uma tarefa. comment_type: NOTE, PROGRESS ou CODE_REVIEW."""
    s = get_session()
    try:
        key, _, num = task_code.rpartition("-")
        project = s.query(Project).filter(Project.key == key).first()
        if not project:
            return f"Projeto {key} não encontrado."
        task = s.query(Task).filter(
            Task.project_id == project.id, Task.number == int(num), Task.deleted_at.is_(None)
        ).first()
        if not task:
            return f"Tarefa {task_code} não encontrada."
        ctype = comment_type.upper() if comment_type.upper() in ("NOTE", "PROGRESS", "CODE_REVIEW") else "NOTE"
        s.add(Comment(body=comment, type=ctype, task_id=task.id))
        s.commit()
        return f"Comentário ({ctype}) adicionado a {task_code}."
    except Exception as e:  # noqa: BLE001
        s.rollback()
        return f"Erro: {e}"
    finally:
        s.close()


@tool
def create_todo(text: str) -> str:
    """Cria um TODO simples na lista de pendências do usuário."""
    s = get_session()
    try:
        s.add(Todo(text=text.strip(), sort_order=s.query(Todo).count()))
        s.commit()
        return f"TODO criado: {text}"
    except Exception as e:  # noqa: BLE001
        s.rollback()
        return f"Erro: {e}"
    finally:
        s.close()


@tool
def get_recent_activity(days: int = 1) -> str:
    """Retorna a atividade dos últimos N dias (tarefas criadas, movidas, comentadas).
    Use para montar resumos do dia ou entender o que foi feito recentemente."""
    s = get_session()
    try:
        since = datetime.utcnow() - timedelta(days=max(1, days))
        entries = s.query(ActivityLog).filter(
            ActivityLog.created_at >= since
        ).order_by(ActivityLog.created_at.desc()).limit(80).all()
        if not entries:
            return "Nenhuma atividade no período."
        lines = [f"{e.created_at.strftime('%d/%m %H:%M')} - {e.action}: {e.detail or ''}" for e in entries]
        return "\n".join(lines)
    finally:
        s.close()


@tool
def search_knowledge_base(query: str) -> str:
    """Busca nas notas da Base de conhecimento (2º cérebro) do workspace por
    palavras-chave e retorna as mais relevantes (título + trecho). Use quando o
    usuário perguntar sobre decisões, procedimentos ou anotações registradas."""
    from maestro_local.kb import retrieve
    s = get_session()
    try:
        notes = [{"id": d.id, "title": d.title, "body": d.body or ""}
                 for d in s.query(Document).filter(Document.type == "KB").all()]
    finally:
        s.close()
    if not notes:
        return "Nenhuma nota na Base de conhecimento."
    hits = retrieve(notes, query, top_k=4)
    if not hits:
        return "Nenhuma nota relevante encontrada."
    return "\n\n".join(f"[{n['title']}]\n{(n['body'] or '')[:400]}" for n in hits)


@tool
def get_project_metrics() -> str:
    """Métricas rápidas do workspace por projeto: total de tarefas, concluídas e
    ativas. Use para relatórios, priorização e visão geral do progresso."""
    s = get_session()
    try:
        projects = s.query(Project).all()
        if not projects:
            return "Nenhum projeto."
        out = []
        for p in projects:
            tasks = s.query(Task).filter(
                Task.project_id == p.id, Task.deleted_at.is_(None)).all()
            done_cols = {c.id for c in s.query(BoardColumn).filter(
                BoardColumn.project_id == p.id, BoardColumn.is_done.is_(True)).all()}
            done = sum(1 for t in tasks if t.column_id in done_cols)
            out.append(f"{p.key} — {p.name}: {len(tasks)} tarefas, {done} concluídas, "
                       f"{len(tasks) - done} ativas")
        return "\n".join(out)
    finally:
        s.close()


@tool
def list_pending_todos() -> str:
    """Lista os TODOs pendentes (não concluídos) do usuário, com prioridade e
    prazo quando houver. Use para lembrar o que ainda falta fazer."""
    s = get_session()
    try:
        todos = (s.query(Todo).filter(Todo.done.is_(False))
                 .order_by(Todo.sort_order, Todo.id).all())
        if not todos:
            return "Nenhum TODO pendente."
        lines = []
        for t in todos:
            due = f" (vence {t.due_at.strftime('%d/%m %H:%M')})" if t.due_at else ""
            lines.append(f"- [{t.priority}] {t.text}{due}")
        return "\n".join(lines)
    finally:
        s.close()


@tool
def search_memory(query: str, kind: str = "", project_id: int = 0) -> str:
    """Busca na memória agentic do workspace (fatos, decisões, preferências,
    episódios, procedimentos). Use busca semântica/híbrida para recuperar
    contexto de qualquer ponto do desenvolvimento. kind opcional:
    fact|decision|preference|episode|procedure|context (vírgula para vários).
    project_id=0 = todos os projetos."""
    from maestro_local import memory as mem
    s = get_session()
    try:
        hits = mem.search(
            s,
            query,
            kind=kind or None,
            project_id=project_id or None,
            top_k=6,
            mark_accessed=True,
        )
        if not hits:
            return "Nenhuma memória relevante encontrada."
        return mem.format_for_agent(hits)
    finally:
        s.close()


@tool
def remember(
    title: str,
    content: str,
    kind: str = "fact",
    project_id: int = 0,
    task_id: int = 0,
    importance: float = 0.5,
    tags: str = "",
) -> str:
    """Grava uma memória duradoura no workspace para uso futuro por agentes.
    kind: fact|decision|preference|episode|procedure|context.
    Use para decisões de arquitetura, preferências do dev, lições aprendidas,
    contexto de tarefas e procedimentos. tags: separadas por vírgula."""
    from maestro_local import memory as mem
    s = get_session()
    try:
        entry = mem.remember(
            s,
            title=title,
            content=content,
            kind=kind or "fact",
            tags=tags or None,
            project_id=project_id or None,
            task_id=task_id or None,
            source_type="agent",
            importance=importance if importance is not None else 0.5,
        )
        s.commit()
        return (
            f"Memória gravada id={entry.id} kind={entry.kind} "
            f"title={entry.title!r} embed={'sim' if entry.embedding else 'não'}"
        )
    except Exception as e:  # noqa: BLE001
        s.rollback()
        return f"Erro ao gravar memória: {e}"
    finally:
        s.close()


@tool
def forget_memory(memory_id: int) -> str:
    """Remove (soft-delete) uma memória do workspace pelo id numérico."""
    from maestro_local import memory as mem
    s = get_session()
    try:
        entry = (
            s.query(MemoryEntry)
            .filter(MemoryEntry.id == memory_id, MemoryEntry.deleted_at.is_(None))
            .first()
        )
        if not entry:
            return f"Memória {memory_id} não encontrada."
        mem.soft_delete(s, entry)
        s.commit()
        return f"Memória {memory_id} removida."
    except Exception as e:  # noqa: BLE001
        s.rollback()
        return f"Erro: {e}"
    finally:
        s.close()


ALL_TOOLS = [
    list_projects,
    get_board_summary,
    list_tasks,
    request_task_review,
    add_task_comment,
    create_todo,
    get_recent_activity,
    search_knowledge_base,
    search_memory,
    remember,
    forget_memory,
    get_project_metrics,
    list_pending_todos,
]
