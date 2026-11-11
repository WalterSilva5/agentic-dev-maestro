"""Relay Local — FastAPI application.

All endpoints are open (no auth). The response shapes mirror the web version
so that agents can use the same API format against both backends.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from relay.db.models import (
    ActivityLog,
    BoardColumn,
    Comment,
    DailyNote,
    Document,
    Epic,
    Evidence,
    GateRule,
    Goal,
    Label,
    ApiCall,
    ApiRequest,
    Member,
    MemoryEntry,
    ParityResult,
    Project,
    ProjectDailyEntry,
    ProjectLink,
    Recording,
    Runbook,
    Snippet,
    Sprint,
    StudyPlan,
    StudySession,
    StudyTopic,
    Task,
    TimeLog,
    TaskChecklist,
    TaskDependency,
    Todo,
    get_or_create_member,
    get_session,
    member_stats,
    project_members,
    task_labels,
    DEFAULT_COLUMNS,
)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="Relay Local", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Dependency — DB session
# ---------------------------------------------------------------------------


def db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    name: str
    key: str
    description: Optional[str] = None
    boardUrl: Optional[str] = None
    azureBoardUrl: Optional[str] = None
    targetDate: Optional[str] = None


class TaskCreate(BaseModel):
    projectId: int
    title: str
    description: Optional[str] = None
    objective: Optional[str] = None
    acceptance: Optional[str] = None
    priority: Optional[str] = "MEDIUM"
    estimateMd: Optional[float] = None
    type: Optional[str] = "FEATURE"
    columnId: Optional[int] = None
    parentId: Optional[int] = None
    sprintId: Optional[int] = None
    dueDate: str | None = None
    assignee: str | None = None
    requiresHuman: bool | None = None
    # tarefa local: não sincroniza com o board externo
    isLocal: bool | None = False


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    acceptance: Optional[str] = None
    priority: Optional[str] = None
    estimateMd: Optional[float] = None
    type: Optional[str] = None
    columnId: Optional[int] = None
    parentId: Optional[int] = None
    sprintId: Optional[int] = None
    rank: Optional[str] = None
    dueDate: str | None = None
    assignee: str | None = None
    requiresHuman: bool | None = None
    isLocal: bool | None = None


class MoveBody(BaseModel):
    columnId: int


class SprintCreate(BaseModel):
    name: str
    goal: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    capacity: Optional[float] = None


class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    status: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    capacity: Optional[float] = None
    sortOrder: Optional[int] = None


class SprintComplete(BaseModel):
    moveUnfinishedTo: Optional[int] = None  # id da sprint destino; ausente/null = backlog


class BoardColumnCreate(BaseModel):
    name: str
    wipLimit: Optional[int] = None
    isDone: Optional[bool] = False


class BoardColumnUpdate(BaseModel):
    name: Optional[str] = None
    wipLimit: Optional[int] = None
    isDone: Optional[bool] = None
    order: Optional[int] = None


class BoardColumnReorder(BaseModel):
    orderedIds: list[int]


class ChecklistBody(BaseModel):
    title: str


class DependencyBody(BaseModel):
    blockerCode: str


class LabelCreate(BaseModel):
    name: str
    color: Optional[str] = None


class EpicCreate(BaseModel):
    name: str
    color: Optional[str] = None


class EpicUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class GoalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dueDate: Optional[str] = None
    tag: Optional[str] = None
    epicId: Optional[int] = None
    sprintId: Optional[int] = None


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dueDate: str | None = None
    tag: Optional[str] = None
    epicId: Optional[int] = None
    sprintId: Optional[int] = None


class MemberCreate(BaseModel):
    name: str
    color: Optional[str] = None


class ProjectLinkCreate(BaseModel):
    title: str
    url: str


class ProjectLinkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    sort_order: Optional[int] = None


class ProjectLinkReorder(BaseModel):
    orderedIds: list[int]


def _link_dict(l: ProjectLink) -> dict:
    return {"id": l.id, "projectId": l.project_id, "title": l.title, "url": l.url, "sortOrder": l.sort_order, "createdAt": l.created_at.isoformat() if l.created_at else None}


DAILY_KINDS = ("WORK", "BLOCKER", "DECISION", "NOTE")
DAILY_SECTIONS = ("INTRO", "ITEMS", "SPRINT", "PENDING", "OTHER")


class ProjectDailyCreate(BaseModel):
    body: str
    date: Optional[str] = None          # YYYY-MM-DD (default: hoje)
    kind: Optional[str] = "WORK"
    author: Optional[str] = None
    minutes: Optional[int] = None
    taskCode: Optional[str] = None
    title: Optional[str] = None         # tema do item/dia
    section: Optional[str] = "ITEMS"    # INTRO|ITEMS|SPRINT|PENDING|OTHER


class ProjectDailyUpdate(BaseModel):
    body: Optional[str] = None
    date: Optional[str] = None
    kind: Optional[str] = None
    author: Optional[str] = None
    minutes: Optional[int] = None
    taskCode: Optional[str] = None
    title: Optional[str] = None
    section: Optional[str] = None
    sortOrder: Optional[int] = None


class ProjectDailyImport(BaseModel):
    content: Optional[str] = None       # markdown cru
    path: Optional[str] = None          # ou caminho de um .md
    replace: Optional[bool] = True      # apaga os registros do dia antes de importar


def _daily_validate_section(value: str | None) -> str:
    sec = (value or "ITEMS").strip().upper()
    if sec not in DAILY_SECTIONS:
        raise HTTPException(400, f"section must be one of {', '.join(DAILY_SECTIONS)}")
    return sec


def _daily_dict(e: ProjectDailyEntry) -> dict:
    return {
        "id": e.id,
        "projectId": e.project_id,
        "date": e.date,
        "kind": e.kind or "WORK",
        "section": e.section or "ITEMS",
        "title": e.title or "",
        "sortOrder": e.sort_order or 0,
        "body": e.body or "",
        "author": e.author,
        "minutes": e.minutes,
        "taskCode": e.task_code or "",
        "createdAt": e.created_at.isoformat() if e.created_at else None,
        "updatedAt": e.updated_at.isoformat() if e.updated_at else None,
    }


def _daily_validate_date(value: str | None) -> str:
    if not value:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")


def _daily_validate_kind(value: str | None) -> str:
    kind = (value or "WORK").strip().upper()
    if kind not in DAILY_KINDS:
        raise HTTPException(400, f"kind must be one of {', '.join(DAILY_KINDS)}")
    return kind


class EvidenceCreate(BaseModel):
    kind: str
    title: Optional[str] = None
    url: Optional[str] = None
    environment: Optional[str] = None
    executed_at: Optional[str] = None
    executor: Optional[str] = None
    result: Optional[str] = None
    notes: Optional[str] = None


class ParityCreate(BaseModel):
    case_name: str
    status: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    notes: Optional[str] = None


class ParityUpdate(BaseModel):
    status: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    notes: Optional[str] = None
    case_name: Optional[str] = None


class GateRuleUpsert(BaseModel):
    columnId: int
    require_evidence: Optional[bool] = False
    min_evidence: Optional[int] = 1
    required_evidence_kinds: Optional[str] = None
    require_parity: Optional[bool] = False
    forbidden_parity: Optional[str] = "DIVERGENCIA"
    require_comment_type: Optional[str] = None
    require_pr_merged: Optional[bool] = False
    message: Optional[str] = None


def _evidence_dict(e) -> dict:
    return {
        "id": e.id,
        "taskId": e.task_id,
        "kind": e.kind,
        "title": e.title,
        "url": e.url,
        "environment": e.environment,
        "executed_at": e.executed_at.isoformat() if e.executed_at else None,
        "executor": e.executor,
        "result": e.result,
        "notes": e.notes,
        "createdAt": e.created_at.isoformat() if e.created_at else None,
    }


def _parity_dict(p) -> dict:
    return {
        "id": p.id,
        "taskId": p.task_id,
        "case_name": p.case_name,
        "status": p.status,
        "expected": p.expected,
        "actual": p.actual,
        "notes": p.notes,
        "createdAt": p.created_at.isoformat() if p.created_at else None,
    }


def _gate_rule_dict(r) -> dict:
    return {
        "id": r.id,
        "projectId": r.project_id,
        "columnId": r.column_id,
        "columnName": r.column.name if r.column else None,
        "require_evidence": bool(r.require_evidence),
        "min_evidence": r.min_evidence or 1,
        "required_evidence_kinds": r.required_evidence_kinds,
        "require_parity": bool(r.require_parity),
        "forbidden_parity": r.forbidden_parity,
        "require_comment_type": r.require_comment_type,
        "require_pr_merged": bool(r.require_pr_merged),
        "message": r.message,
    }


class CommentCreate(BaseModel):
    taskId: int
    body: str
    type: Optional[str] = "COMMENT"
    # quem escreveu (agente, revisor, pessoa). Sem isso, "local" — e o serviço
    # por membro no report semanal não consegue atribuir a revisão.
    author: Optional[str] = None


class CommentUpdate(BaseModel):
    body: str
    author: Optional[str] = None


class DocumentCreate(BaseModel):
    title: str
    body: Optional[str] = ""
    type: Optional[str] = "NOTES"
    taskId: Optional[int] = None
    projectId: Optional[int] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    type: Optional[str] = None


class StudyPlanCreate(BaseModel):
    title: str
    category: str = "LINGUAGEM"
    description: Optional[str] = None
    startDate: Optional[str] = None
    targetDate: Optional[str] = None
    resources: Optional[list] = None


class StudyPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    startDate: Optional[str] = None
    targetDate: Optional[str] = None
    resources: Optional[list] = None


class StudyTopicCreate(BaseModel):
    title: str
    description: Optional[str] = None
    parentId: Optional[int] = None
    weight: Optional[float] = 1.0
    estimateHours: Optional[float] = None
    resources: Optional[list] = None


class StudyTopicUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    weight: Optional[float] = None
    estimateHours: Optional[float] = None
    loggedHours: Optional[float] = None
    notes: Optional[str] = None
    resources: Optional[list] = None


class ReorderTopicsBody(BaseModel):
    ids: list[int]


class StudySessionCreate(BaseModel):
    topicId: int
    startedAt: str
    endedAt: Optional[str] = None
    durationMin: Optional[int] = None
    notes: Optional[str] = None
    confidence: Optional[int] = Field(default=None, ge=1, le=5)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

# -- Study serialisation -----------------------------------------------------

def _topic_dict(t: "StudyTopic", include_children: bool = True) -> dict:
    import json
    d = {
        "id": t.id, "planId": t.plan_id, "parentId": t.parent_id,
        "title": t.title, "description": t.description,
        "sortOrder": t.sort_order, "status": t.status,
        "weight": t.weight, "estimateHours": t.estimate_hours,
        "loggedHours": t.logged_hours, "notes": t.notes,
        "resources": json.loads(t.resources) if t.resources else [],
        "createdAt": t.created_at.isoformat() if t.created_at else None,
        "updatedAt": t.updated_at.isoformat() if t.updated_at else None,
    }
    if include_children and t.children:
        d["children"] = [_topic_dict(c, include_children=False)
                         for c in sorted(t.children, key=lambda x: x.sort_order)]
    return d


def _plan_progress(plan: "StudyPlan") -> tuple:
    topics = plan.topics
    not_skipped = [t for t in topics if t.status != "PULADO" and t.parent_id is None]
    done = [t for t in not_skipped if t.status == "CONCLUIDO"]
    done_weight = sum(t.weight or 1 for t in done)
    total_weight = sum(t.weight or 1 for t in not_skipped)
    progress = round((done_weight / total_weight) * 100) if total_weight > 0 else 0
    return progress, len(done), len(not_skipped)


def _plan_dict(p: "StudyPlan", include_topics: bool = False) -> dict:
    progress, done, total = _plan_progress(p)
    return {
        "id": p.id, "title": p.title, "description": p.description,
        "category": p.category, "status": p.status,
        "startDate": p.start_date.isoformat() if p.start_date else None,
        "targetDate": p.target_date.isoformat() if p.target_date else None,
        "progress": progress, "doneTopics": done, "totalTopics": total,
        "createdAt": p.created_at.isoformat() if p.created_at else None,
        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
        **({"topics": [_topic_dict(t) for t in p.topics if t.parent_id is None]} if include_topics else {}),
    }


def _session_dict(s: "StudySession") -> dict:
    return {
        "id": s.id, "planId": s.plan_id, "topicId": s.topic_id,
        "topic": {"id": s.topic.id, "title": s.topic.title} if s.topic else None,
        "startedAt": s.started_at.isoformat() if s.started_at else None,
        "endedAt": s.ended_at.isoformat() if s.ended_at else None,
        "durationMin": s.duration_min, "notes": s.notes,
        "confidence": s.confidence,
        "createdAt": s.created_at.isoformat() if s.created_at else None,
    }


def _label_dict(l: Label) -> dict:
    return {"id": l.id, "name": l.name, "color": l.color}


def _epic_dict(e) -> dict:
    return {"id": e.id, "projectId": e.project_id, "name": e.name, "color": e.color}


def _member_dict(m, stats: dict | None = None) -> dict:
    d = {"id": m.id, "projectId": m.project_id, "name": m.name, "color": m.color}
    if stats is not None:
        d.update({k: v for k, v in stats.items() if k != "member"})
    return d


def _goal_filter_query(s: Session, goal) -> Any:
    """Tarefas do goal (não arquivadas/excluídas) com filtros combinados."""
    from relay.db.models import Epic
    q = s.query(Task).filter(
        Task.project_id == goal.project_id,
        Task.deleted_at == None,  # noqa: E711
        Task.archived_at == None,  # noqa: E711
    )
    if goal.tag:
        q = q.filter(Task.labels.any(Label.name == goal.tag))
    if goal.epic_id:
        q = q.filter(Task.epics.any(Epic.id == goal.epic_id))
    if goal.sprint_id:
        q = q.filter(Task.sprint_id == goal.sprint_id)
    return q


def _goal_progress(s: Session, goal) -> dict:
    from datetime import date
    tasks = [
        t for t in _goal_filter_query(s, goal).all()
        if not t.is_local  # lembrete local não conta em objetivo
    ]
    done = [t for t in tasks if t.column and t.column.is_done]
    pct = round(len(done) / len(tasks) * 100) if tasks else 0
    days_left = None
    if goal.due_date:
        try:
            days_left = (goal.due_date.date() - date.today()).days
        except Exception:  # noqa: BLE001
            days_left = None
    return {"total": len(tasks), "done": len(done), "pct": pct, "daysLeft": days_left}


def _goal_dict(g, s: Session | None = None) -> dict:
    d = {
        "id": g.id,
        "projectId": g.project_id,
        "name": g.name,
        "description": g.description,
        "dueDate": g.due_date.isoformat() if g.due_date else None,
        "tag": g.tag,
        "epicId": g.epic_id,
        "epic": g.epic.name if g.epic else None,
        "sprintId": g.sprint_id,
        "sprint": g.sprint.name if g.sprint else None,
    }
    if s is not None:
        d["progress"] = _goal_progress(s, g)
    return d


def _checklist_dict(c: TaskChecklist) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "checked": c.checked,
        "sortOrder": c.sort_order,
    }


def _dep_dict(d: TaskDependency, role: str) -> dict:
    """role is 'blocker' or 'blocked'."""
    task = d.blocker if role == "blocker" else d.blocked
    return {
        "id": d.id,
        "taskId": task.id,
        "code": task.code,
        "title": task.title,
        "status": task.status,
    }


def _task_brief(t: Task) -> dict:
    return {
        "id": t.id,
        "code": t.code,
        "number": t.number,
        "title": t.title,
        "type": t.type,
        "priority": t.priority,
        "status": t.status,
        "columnId": t.column_id,
        "estimateMd": t.estimate_md,
        "dueDate": t.due_date.isoformat() if t.due_date else None,
        "assignee": t.assignee,
        "requiresHuman": t.requires_human or False,
        "isLocal": bool(t.is_local),
        "parentId": t.parent_id,
        "sprintId": t.sprint_id,
        "doneAt": t.done_at.isoformat() if t.done_at else None,
        "archivedAt": t.archived_at.isoformat() if t.archived_at else None,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
        "updatedAt": t.updated_at.isoformat() if t.updated_at else None,
        "labels": [_label_dict(lb) for lb in t.labels],
        "epics": [{"id": e.id, "name": e.name, "color": e.color} for e in t.epics],
    }


def _task_full(t: Task) -> dict:
    d = _task_brief(t)
    d.update(
        {
            "description": t.description,
            "objective": t.objective,
            "acceptance": t.acceptance,
            "rank": t.rank,
            "projectId": t.project_id,
            "projectKey": t.project.key if t.project else None,
            "checklist": [_checklist_dict(c) for c in t.checklist],
            "blockedBy": [_dep_dict(dep, "blocker") for dep in t.blocked_by],
            "blocking": [_dep_dict(dep, "blocked") for dep in t.blocking],
            "subtasks": [_task_brief(s) for s in t.subtasks if s.deleted_at is None],
        }
    )
    return d


def _column_dict(c: BoardColumn, include_tasks: bool = False) -> dict:
    d = {
        "id": c.id,
        "name": c.name,
        "order": c.order,
        "wipLimit": c.wip_limit,
        "isDone": c.is_done,
    }
    if include_tasks:
        d["tasks"] = [
            _task_brief(t) for t in c.tasks if t.deleted_at is None
        ]
    return d


def _project_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "key": p.key,
        "description": p.description,
        "taskSeq": p.task_seq,
        "externalDocsPath": getattr(p, "external_docs_path", "") or "",
        # Alias genérico (o board externo pode ser Azure DevOps, Jira, ClickUp...).
        # `azureBoardUrl` fica por compatibilidade com clientes antigos.
        "boardUrl": getattr(p, "azure_board_url", "") or "",
        "azureBoardUrl": getattr(p, "azure_board_url", "") or "",
        "targetDate": p.target_date.isoformat() if getattr(p, "target_date", None) else None,
        "hideAssignee": bool(getattr(p, "hide_assignee", False)),
        "dailyDocsPath": getattr(p, "daily_docs_path", "") or "",
        "links": [_link_dict(l) for l in getattr(p, "links", [])],
        "createdAt": p.created_at.isoformat() if p.created_at else None,
    }


def _board_column_dict(c: BoardColumn) -> dict:
    return {"id": c.id, "projectId": c.project_id, "name": c.name, "order": c.order, "wipLimit": c.wip_limit, "isDone": bool(c.is_done)}


def _sprint_dict(sp: Sprint, include_stats: bool = True) -> dict:
    d = {
        "id": sp.id,
        "projectId": sp.project_id,
        "name": sp.name,
        "goal": sp.goal,
        "status": sp.status,
        "startDate": sp.start_date.isoformat() if sp.start_date else None,
        "endDate": sp.end_date.isoformat() if sp.end_date else None,
        "capacity": sp.capacity,
        "sortOrder": sp.sort_order,
    }
    if include_stats:
        tasks = [t for t in sp.tasks if t.deleted_at is None]
        done = [t for t in tasks if t.column and t.column.is_done]
        committed = sum(t.estimate_md or 0 for t in tasks)
        d.update({
            "taskCount": len(tasks),
            "doneCount": len(done),
            "committedMd": round(committed, 2),
            "progress": round(len(done) / len(tasks) * 100) if tasks else 0,
        })
    return d


def _comment_dict(c: Comment) -> dict:
    return {
        "id": c.id,
        "taskId": c.task_id,
        "body": c.body,
        "type": c.type,
        "author": c.author,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
    }


def _document_dict(d: Document) -> dict:
    return {
        "id": d.id,
        "taskId": d.task_id,
        "projectId": d.project_id,
        "title": d.title,
        "body": d.body,
        "type": d.type,
        "version": d.version,
        "createdAt": d.created_at.isoformat() if d.created_at else None,
        "updatedAt": d.updated_at.isoformat() if d.updated_at else None,
    }


def _activity_dict(a: ActivityLog) -> dict:
    return {
        "id": a.id,
        "entityType": a.entity_type,
        "entityId": a.entity_id,
        "action": a.action,
        "detail": a.detail,
        "createdAt": a.created_at.isoformat() if a.created_at else None,
    }


# ---------------------------------------------------------------------------
# Helper — resolve task by code ("KEY-NUM") or raw id
# ---------------------------------------------------------------------------


def _resolve_task(code_or_id: str, s: Session) -> Task:
    if "-" in code_or_id:
        parts = code_or_id.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            project_key, number = parts[0], int(parts[1])
            task = (
                s.query(Task)
                .join(Project)
                .filter(
                    Project.key == project_key,
                    Task.number == number,
                    Task.deleted_at.is_(None),
                )
                .first()
            )
            if task:
                return task
    # Fallback: try as raw integer id
    if code_or_id.isdigit():
        task = s.query(Task).filter(Task.id == int(code_or_id), Task.deleted_at.is_(None)).first()
        if task:
            return task
    raise HTTPException(status_code=404, detail=f"Task '{code_or_id}' not found")


# ---------------------------------------------------------------------------
# Helper — activity log
# ---------------------------------------------------------------------------


def _log(s: Session, entity_type: str, entity_id: int, action: str, detail: str | None = None):
    s.add(ActivityLog(entity_type=entity_type, entity_id=entity_id, action=action, detail=detail))


# ============================= ENDPOINTS ==================================


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@app.post("/api/projects")
def create_project(body: ProjectCreate, s: Session = Depends(db)):
    existing = s.query(Project).filter(Project.key == body.key.upper()).first()
    if existing:
        raise HTTPException(400, "Project key already exists")
    board_url = (body.boardUrl or body.azureBoardUrl or "").strip()
    p = Project(name=body.name, key=body.key.upper(), description=body.description, azure_board_url=board_url,
                target_date=_parse_dt(body.targetDate) if body.targetDate else None)
    s.add(p)
    s.flush()
    for col_def in DEFAULT_COLUMNS:
        s.add(BoardColumn(project_id=p.id, **col_def))
    s.commit()
    s.refresh(p)
    return _project_dict(p)


@app.get("/api/projects")
def list_projects(s: Session = Depends(db)):
    projects = s.query(Project).order_by(Project.created_at.desc()).all()
    return [_project_dict(p) for p in projects]


@app.get("/api/projects/metrics")
def project_metrics(s: Session = Depends(db)):
    now = datetime.utcnow()
    seven_ago = now - timedelta(days=7)
    thirty_ago = now - timedelta(days=30)

    all_tasks = s.query(Task).filter(Task.deleted_at.is_(None)).all()

    done_tasks = [t for t in all_tasks if t.column and t.column.is_done]
    total = len(all_tasks)
    done_count = len(done_tasks)

    completed_7d = len([t for t in done_tasks if t.updated_at and t.updated_at >= seven_ago])
    completed_30d = len([t for t in done_tasks if t.updated_at and t.updated_at >= thirty_ago])

    # Lead time = created_at -> updated_at for done tasks
    lead_times = []
    cycle_times = []
    for t in done_tasks:
        if t.created_at and t.updated_at:
            lt = (t.updated_at - t.created_at).total_seconds() / 3600
            lead_times.append(lt)
            cycle_times.append(lt)  # local version doesn't track "started" separately

    avg_lead = round(sum(lead_times) / len(lead_times), 1) if lead_times else 0
    avg_cycle = round(sum(cycle_times) / len(cycle_times), 1) if cycle_times else 0

    # Weekly throughput — last 8 weeks
    weekly: list[dict] = []
    for w in range(7, -1, -1):
        start = now - timedelta(weeks=w + 1)
        end = now - timedelta(weeks=w)
        count = len([t for t in done_tasks if t.updated_at and start <= t.updated_at < end])
        weekly.append({"week": (now - timedelta(weeks=w)).strftime("%Y-W%W"), "count": count})

    # By type / priority
    by_type: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for t in all_tasks:
        by_type[t.type or "FEATURE"] = by_type.get(t.type or "FEATURE", 0) + 1
        by_priority[t.priority or "MEDIUM"] = by_priority.get(t.priority or "MEDIUM", 0) + 1

    # Per project
    per_project: list[dict] = []
    projects = s.query(Project).all()
    for p in projects:
        ptasks = [t for t in all_tasks if t.project_id == p.id]
        pdone = [t for t in ptasks if t.column and t.column.is_done]
        per_project.append({
            "projectId": p.id,
            "projectName": p.name,
            "projectKey": p.key,
            "totalTasks": len(ptasks),
            "doneTasks": len(pdone),
        })

    return {
        "summary": {
            "totalTasks": total,
            "doneTasks": done_count,
            "completedLast7d": completed_7d,
            "completedLast30d": completed_30d,
            "avgLeadTimeHours": avg_lead,
            "avgCycleTimeHours": avg_cycle,
        },
        "weeklyThroughput": weekly,
        "byType": by_type,
        "byPriority": by_priority,
        "perProject": per_project,
    }


AUTO_ARCHIVE_DAYS = 3


def _auto_archive(s: Session, project_id: int) -> int:
    """Arquiva tarefas concluídas há mais de AUTO_ARCHIVE_DAYS dias.

    Faz o backfill do done_at (a partir de updated_at) para tarefas já em
    coluna de conclusão que ainda não têm o marcador. Retorna quantas arquivou.
    """
    from datetime import timedelta
    now = datetime.utcnow()
    cutoff = now - timedelta(days=AUTO_ARCHIVE_DAYS)
    done_col_ids = {
        c.id for c in s.query(BoardColumn).filter(
            BoardColumn.project_id == project_id, BoardColumn.is_done == True  # noqa: E712
        ).all()
    }
    if not done_col_ids:
        return 0
    tasks = s.query(Task).filter(
        Task.project_id == project_id,
        Task.deleted_at.is_(None),
        Task.archived_at.is_(None),
        Task.column_id.in_(done_col_ids),
    ).all()
    archived = 0
    for t in tasks:
        # Cards importados chegam concluídos e sem data real de conclusão:
        # inventar `done_at` falsearia relatório de entrega. Só arquiva quem
        # tem data de verdade (movido para a coluna de conclusão pelo app).
        if t.done_at is None:
            continue
        if t.done_at <= cutoff:
            t.archived_at = now
            archived += 1
    if tasks:
        s.commit()
    return archived


@app.get("/api/projects/{project_id}/board")
def project_board(project_id: int, sprintId: Optional[str] = None, s: Session = Depends(db)):
    """Board do projeto. sprintId opcional filtra as tarefas:
    - ausente: todas as tarefas
    - "backlog": só tarefas sem sprint
    - número: só tarefas da sprint indicada
    Tarefas arquivadas nunca aparecem aqui.
    """
    p = s.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")

    _auto_archive(s, project_id)

    def _keep(t: Task) -> bool:
        if t.deleted_at is not None or t.archived_at is not None:
            return False
        if sprintId is None or sprintId == "":
            return True
        if sprintId == "backlog":
            return t.sprint_id is None
        return str(t.sprint_id) == str(sprintId)

    columns = []
    for c in p.columns:
        col = _column_dict(c, include_tasks=False)
        col["tasks"] = [_task_brief(t) for t in c.tasks if _keep(t)]
        columns.append(col)
    return {**_project_dict(p), "columns": columns}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, s: Session = Depends(db)):
    p = s.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    s.delete(p)
    s.commit()
    return {"ok": True}


@app.patch("/api/projects/{project_id}")
def update_project(project_id: int, body: dict, s: Session = Depends(db)):
    p = s.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    if "name" in body:
        p.name = body["name"]
    if "description" in body:
        p.description = body["description"]
    if "externalDocsPath" in body:
        p.external_docs_path = (body["externalDocsPath"] or "").strip()
    if "external_docs_path" in body:
        p.external_docs_path = (body["external_docs_path"] or "").strip()
    if "boardUrl" in body:
        p.azure_board_url = (body["boardUrl"] or "").strip()
    if "azureBoardUrl" in body:
        p.azure_board_url = (body["azureBoardUrl"] or "").strip()
    if "azure_board_url" in body:
        p.azure_board_url = (body["azure_board_url"] or "").strip()
    if "targetDate" in body or "target_date" in body:
        raw = body.get("targetDate", body.get("target_date"))
        try:
            p.target_date = _parse_dt(raw) if raw else None
        except (ValueError, TypeError):
            raise HTTPException(400, "targetDate inválida (use AAAA-MM-DD)")
    if "hideAssignee" in body or "hide_assignee" in body:
        raw = body.get("hideAssignee", body.get("hide_assignee"))
        p.hide_assignee = raw is True or str(raw).lower() in ("1", "true", "yes", "sim")
    if "dailyDocsPath" in body or "daily_docs_path" in body:
        from pathlib import Path as _Path
        raw = (body.get("dailyDocsPath", body.get("daily_docs_path")) or "").strip()
        if raw:
            abs_raw = str(_Path(raw).expanduser())
            if not abs_raw.startswith("/"):
                raise HTTPException(400, "dailyDocsPath deve ser absoluto")
            raw = abs_raw
        p.daily_docs_path = raw
    s.commit()
    return _project_dict(p)


class MoveProjectBody(BaseModel):
    targetWorkspaceId: str


@app.post("/api/projects/{project_id}/move")
def move_project(project_id: int, body: MoveProjectBody, s: Session = Depends(db)):
    from relay.db.models import move_project_to_workspace
    from relay.config import list_workspaces

    p = s.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    target_ws = (body.targetWorkspaceId or "").strip()
    if not target_ws:
        raise HTTPException(400, "targetWorkspaceId is required")
    if target_ws not in {w["id"] for w in list_workspaces()}:
        raise HTTPException(404, f"Workspace '{target_ws}' not found")
    # move_project_to_workspace gerencia suas próprias sessões/engines
    new_id = move_project_to_workspace(project_id, target_ws)
    if new_id is None:
        raise HTTPException(400, "Move failed (maybe same workspace or not found)")
    s_expire = s  # força recarregar lista na próxima chamada
    return {"ok": True, "projectId": project_id, "newProjectId": new_id, "targetWorkspaceId": target_ws}


def _validate_docs_path(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return ""
    import os
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        raise HTTPException(400, "externalDocsPath deve ser absoluto")
    # não exige existir agora — só valida formato
    return p


@app.get("/api/projects/{project_id}/docs/files")
def project_docs_files(project_id: int, s: Session = Depends(db)):
    p = s.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    base = (p.external_docs_path or "").strip()
    if not base:
        return {"projectId": p.id, "base": "", "files": []}
    import os
    if not os.path.isdir(base):
        return {"projectId": p.id, "base": base, "files": [], "error": "diretório não existe"}
    files = []
    for fname in sorted(os.listdir(base)):
        if not fname.lower().endswith(".md"):
            continue
        fpath = os.path.join(base, fname)
        try:
            st = os.stat(fpath)
            files.append({"name": fname, "path": fpath, "size": st.st_size, "mtime": st.st_mtime})
        except OSError:
            continue
    return {"projectId": p.id, "base": base, "files": files}


@app.post("/api/projects/{project_id}/docs/sync")
def project_docs_sync(project_id: int, s: Session = Depends(db)):
    p = s.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    base = (p.external_docs_path or "").strip()
    if not base:
        raise HTTPException(400, "externalDocsPath não configurado")
    import os
    import re
    os.makedirs(base, exist_ok=True)
    # exporta Document do projeto → .md ; importa .md órfãos → Document
    existing = {d.title: d for d in s.query(Document).filter(Document.project_id == p.id).all()}
    # export
    exported = 0
    for d in existing.values():
        fname = re.sub(r'[^\w\- ]', '', d.title or "untitled").strip().replace(" ", "-")[:80] or f"doc-{d.id}"
        fpath = os.path.join(base, f"{fname}.md")
        if not os.path.exists(fpath):
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(f"# {d.title}\n\n{(d.body or '').strip()}\n")
                exported += 1
            except OSError as e:
                raise HTTPException(500, str(e))
    # import .md órfãos → Document
    imported = 0
    for fname in os.listdir(base):
        if not fname.lower().endswith(".md"):
            continue
        title = os.path.splitext(fname)[0].replace("-", " ")
        # título já existe? ignora
        if any(t.lower() == title.lower() for t in existing):
            continue
        fpath = os.path.join(base, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                body = f.read()
        except OSError:
            continue
        # primeira linha # título → usa como título real se houver
        m = re.match(r'\s*#\s+(.+)\n', body)
        doc_title = m.group(1).strip() if m else title
        if doc_title.lower() in {k.lower() for k in existing}:
            continue
        d = Document(project_id=p.id, title=doc_title[:200], body=body, type="NOTES")
        s.add(d)
        imported += 1
    if imported:
        s.commit()
    return {"projectId": p.id, "base": base, "exported": exported, "imported": imported}


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@app.post("/api/tasks")
def create_task(body: TaskCreate, s: Session = Depends(db)):
    project = s.query(Project).filter(Project.id == body.projectId).first()
    if not project:
        raise HTTPException(404, "Project not found")

    # Determine column
    col_id = body.columnId
    if not col_id:
        first_col = s.query(BoardColumn).filter(BoardColumn.project_id == project.id).order_by(BoardColumn.order).first()
        if not first_col:
            raise HTTPException(500, "Project has no columns")
        col_id = first_col.id

    # Increment sequence
    project.task_seq = (project.task_seq or 0) + 1
    number = project.task_seq

    task = Task(
        project_id=project.id,
        column_id=col_id,
        number=number,
        title=body.title,
        description=body.description,
        objective=body.objective,
        acceptance=body.acceptance,
        type=body.type,
        priority=body.priority,
        estimate_md=body.estimateMd,
        parent_id=body.parentId,
    )
    if body.dueDate:
        from datetime import datetime as _dt
        task.due_date = _dt.fromisoformat(body.dueDate)
    if body.assignee:
        task.assignee = body.assignee
    if body.requiresHuman is not None:
        task.requires_human = body.requiresHuman
    if body.sprintId is not None:
        task.sprint_id = body.sprintId
    task.is_local = bool(body.isLocal)
    s.add(task)
    s.flush()
    _log(s, "task", task.id, "created", f"Task {project.key}-{number} created")
    s.commit()
    s.refresh(task)
    return _task_full(task)


@app.get("/api/tasks")
def list_tasks(
    projectId: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    labelId: Optional[int] = None,
    parentId: Optional[int] = None,
    type: str | None = None,
    assignee: str | None = None,
    s: Session = Depends(db),
):
    q = s.query(Task).filter(Task.deleted_at.is_(None))
    if projectId:
        q = q.filter(Task.project_id == projectId)
    if priority:
        q = q.filter(Task.priority == priority)
    if parentId is not None:
        q = q.filter(Task.parent_id == parentId)
    if type:
        q = q.filter(Task.type == type)
    if assignee:
        q = q.filter(Task.assignee == assignee)
    if search:
        pattern = f"%{search}%"
        q = q.filter(Task.title.ilike(pattern) | Task.description.ilike(pattern))
    if status:
        q = q.join(BoardColumn).filter(BoardColumn.name == status)
    if labelId:
        q = q.join(task_labels).filter(task_labels.c.label_id == labelId)
    tasks = q.order_by(Task.created_at.desc()).all()
    return [_task_brief(t) for t in tasks]


@app.get("/api/tasks/{code}")
def get_task(code: str, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    return _task_full(task)


@app.patch("/api/tasks/{code}")
def update_task(code: str, body: TaskUpdate, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    changes: list[str] = []
    data = body.model_dump(exclude_unset=True)
    field_map = {
        "title": "title",
        "description": "description",
        "objective": "objective",
        "acceptance": "acceptance",
        "priority": "priority",
        "estimateMd": "estimate_md",
        "type": "type",
        "columnId": "column_id",
        "parentId": "parent_id",
        "sprintId": "sprint_id",
        "rank": "rank",
        "isLocal": "is_local",
    }
    for api_field, model_field in field_map.items():
        if api_field in data:
            old = getattr(task, model_field)
            new = data[api_field]
            if old != new:
                setattr(task, model_field, new)
                changes.append(f"{api_field}: {old} -> {new}")
    if "dueDate" in data:
        from datetime import datetime as _dt
        old_due = task.due_date
        new_due = _dt.fromisoformat(data["dueDate"]) if data["dueDate"] else None
        if old_due != new_due:
            task.due_date = new_due
            changes.append(f"dueDate: {old_due} -> {new_due}")
    if "assignee" in data:
        old_assignee = task.assignee
        new_assignee = data["assignee"]
        if old_assignee != new_assignee:
            task.assignee = new_assignee
            changes.append(f"assignee: {old_assignee} -> {new_assignee}")
    if "requiresHuman" in data:
        old_rh = task.requires_human or False
        new_rh = bool(data["requiresHuman"])
        if old_rh != new_rh:
            task.requires_human = new_rh
            changes.append(f"requiresHuman: {old_rh} -> {new_rh}")
    task.updated_at = datetime.utcnow()
    if changes:
        _log(s, "task", task.id, "updated", "; ".join(changes))
    s.commit()
    s.refresh(task)
    return _task_full(task)


@app.delete("/api/tasks/{code}")
def delete_task(code: str, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    task.deleted_at = datetime.utcnow()
    _log(s, "task", task.id, "deleted", f"Task {task.code} soft-deleted")
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Sprints
# ---------------------------------------------------------------------------


def _parse_dt(value):
    from datetime import datetime as _dt
    return _dt.fromisoformat(value) if value else None


@app.get("/api/projects/{project_id}/sprints")
def list_sprints(project_id: int, s: Session = Depends(db)):
    p = s.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    sprints = (
        s.query(Sprint)
        .filter(Sprint.project_id == project_id)
        .order_by(Sprint.sort_order, Sprint.id)
        .all()
    )
    return [_sprint_dict(sp) for sp in sprints]


@app.post("/api/projects/{project_id}/sprints")
def create_sprint(project_id: int, body: SprintCreate, s: Session = Depends(db)):
    p = s.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    max_order = (
        s.query(Sprint).filter(Sprint.project_id == project_id).count()
    )
    sp = Sprint(
        project_id=project_id,
        name=body.name,
        goal=body.goal,
        start_date=_parse_dt(body.startDate),
        end_date=_parse_dt(body.endDate),
        capacity=body.capacity,
        sort_order=max_order,
    )
    s.add(sp)
    s.commit()
    s.refresh(sp)
    return _sprint_dict(sp)


@app.patch("/api/sprints/{sprint_id}")
def update_sprint(sprint_id: int, body: SprintUpdate, s: Session = Depends(db)):
    sp = s.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sp:
        raise HTTPException(404, "Sprint not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        sp.name = data["name"]
    if "goal" in data:
        sp.goal = data["goal"]
    if "capacity" in data:
        sp.capacity = data["capacity"]
    if "sortOrder" in data:
        sp.sort_order = data["sortOrder"]
    if "startDate" in data:
        sp.start_date = _parse_dt(data["startDate"])
    if "endDate" in data:
        sp.end_date = _parse_dt(data["endDate"])
    if "status" in data and data["status"]:
        sp.status = data["status"]
        # Só uma sprint ativa por projeto: rebaixa as outras.
        if sp.status == "ATIVA":
            for other in s.query(Sprint).filter(
                Sprint.project_id == sp.project_id, Sprint.id != sp.id, Sprint.status == "ATIVA"
            ).all():
                other.status = "PLANEJADA"
    s.commit()
    s.refresh(sp)
    return _sprint_dict(sp)


@app.post("/api/sprints/{sprint_id}/complete")
def complete_sprint(sprint_id: int, body: SprintComplete, s: Session = Depends(db)):
    sp = s.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sp:
        raise HTTPException(404, "Sprint not found")
    target = body.moveUnfinishedTo
    if target is not None:
        dest = s.query(Sprint).filter(Sprint.id == target, Sprint.project_id == sp.project_id).first()
        if not dest:
            raise HTTPException(400, "Destino inválido para tarefas não concluídas")
    moved = 0
    for task in [t for t in sp.tasks if t.deleted_at is None]:
        if not (task.column and task.column.is_done):
            task.sprint_id = target  # None = backlog
            moved += 1
    sp.status = "CONCLUIDA"
    s.commit()
    s.refresh(sp)
    return {**_sprint_dict(sp), "movedUnfinished": moved}


def _sprint_retro_context(sp: Sprint) -> str:
    """Monta um resumo textual da sprint para a IA gerar a retrospectiva."""
    tasks = [t for t in sp.tasks if t.deleted_at is None]
    done = [t for t in tasks if t.column and t.column.is_done]
    pending = [t for t in tasks if not (t.column and t.column.is_done)]
    lines = [
        f"Sprint: {sp.name}",
        f"Meta: {sp.goal or '(sem meta)'}",
        f"Capacidade: {sp.capacity if sp.capacity is not None else '(não definida)'} homem-dia",
        f"Tarefas concluídas ({len(done)}):",
    ]
    lines += [f"  - [{t.type}] {t.title}" for t in done] or ["  (nenhuma)"]
    lines.append(f"Tarefas não concluídas ({len(pending)}):")
    lines += [f"  - [{t.type}] {t.title}" for t in pending] or ["  (nenhuma)"]
    return "\n".join(lines)


@app.get("/api/sprints/{sprint_id}/retrospective")
def get_sprint_retro(sprint_id: int, s: Session = Depends(db)):
    sp = s.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sp:
        raise HTTPException(404, "Sprint not found")
    import json as _json
    retro = None
    if sp.retro_json:
        try:
            retro = _json.loads(sp.retro_json)
        except ValueError:
            retro = None
    return {"sprintId": sp.id, "retro": retro}


@app.post("/api/sprints/{sprint_id}/retrospective")
def generate_sprint_retrospective(sprint_id: int, s: Session = Depends(db)):
    sp = s.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sp:
        raise HTTPException(404, "Sprint not found")
    from relay.triage import generate_sprint_retro
    import json as _json
    try:
        retro = generate_sprint_retro(_sprint_retro_context(sp))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
    sp.retro_json = _json.dumps(retro, ensure_ascii=False)
    s.commit()
    return {"sprintId": sp.id, "retro": retro}


class RetroActionsBody(BaseModel):
    titles: list


@app.post("/api/sprints/{sprint_id}/retrospective/actions")
def create_retro_actions(sprint_id: int, body: RetroActionsBody, s: Session = Depends(db)):
    sp = s.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sp:
        raise HTTPException(404, "Sprint not found")
    project = sp.project
    column = (
        s.query(BoardColumn)
        .filter(BoardColumn.project_id == project.id)
        .order_by(BoardColumn.order.asc())
        .first()
    )
    created = 0
    for title in body.titles:
        title = str(title).strip()
        if not title:
            continue
        project.task_seq = (project.task_seq or 0) + 1
        s.add(Task(
            project_id=project.id,
            column_id=column.id if column else None,
            number=project.task_seq,
            title=f"[Retro] {title}"[:255],
            description=f"Ação de melhoria da retrospectiva da sprint '{sp.name}'",
            type="CHORE",
            requires_human=True,
        ))
        created += 1
    s.commit()
    _log(s, "project", project.id, "retro_actions", f"{created} ação(ões) da retro de {sp.name}")
    return {"ok": True, "created": created}


@app.delete("/api/sprints/{sprint_id}")
def delete_sprint(sprint_id: int, s: Session = Depends(db)):
    sp = s.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sp:
        raise HTTPException(404, "Sprint not found")
    # SQLite não força ON DELETE SET NULL: solta as tarefas para o backlog.
    for task in sp.tasks:
        task.sprint_id = None
    s.delete(sp)
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Board columns
# ---------------------------------------------------------------------------


@app.get("/api/projects/{project_id}/columns")
def list_columns(project_id: int, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    cols = s.query(BoardColumn).filter(BoardColumn.project_id == project_id).order_by(BoardColumn.order).all()
    return [_board_column_dict(c) for c in cols]


@app.post("/api/projects/{project_id}/columns")
def create_column(project_id: int, body: BoardColumnCreate, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    if not (body.name or "").strip():
        raise HTTPException(400, "Name is required")
    if s.query(BoardColumn).filter(BoardColumn.project_id == project_id, BoardColumn.name == body.name.strip()).first():
        raise HTTPException(400, "Column name already exists in this project")
    order = s.query(BoardColumn).filter(BoardColumn.project_id == project_id).count()
    col = BoardColumn(project_id=project_id, name=body.name.strip()[:120], order=order, wip_limit=body.wipLimit, is_done=bool(body.isDone))
    # garante única coluna de conclusão
    if col.is_done:
        for other in s.query(BoardColumn).filter(BoardColumn.project_id == project_id, BoardColumn.is_done == True).all():  # noqa: E712
            other.is_done = False
    s.add(col)
    s.commit()
    s.refresh(col)
    return _board_column_dict(col)


@app.patch("/api/columns/{column_id}")
def update_column(column_id: int, body: BoardColumnUpdate, s: Session = Depends(db)):
    col = s.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise HTTPException(404, "Column not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and (data["name"] or "").strip():
        name = data["name"].strip()[:120]
        if s.query(BoardColumn).filter(BoardColumn.project_id == col.project_id, BoardColumn.name == name, BoardColumn.id != col.id).first():
            raise HTTPException(400, "Column name already exists in this project")
        col.name = name
    if "wipLimit" in data:
        col.wip_limit = data["wipLimit"]
    if "isDone" in data and data["isDone"] is not None:
        if data["isDone"]:
            for other in s.query(BoardColumn).filter(BoardColumn.project_id == col.project_id, BoardColumn.id != col.id, BoardColumn.is_done == True).all():  # noqa: E712
                other.is_done = False
        col.is_done = bool(data["isDone"])
    if "order" in data and data["order"] is not None:
        col.order = int(data["order"])
    s.commit()
    s.refresh(col)
    return _board_column_dict(col)


@app.delete("/api/columns/{column_id}")
def delete_column(column_id: int, s: Session = Depends(db)):
    col = s.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise HTTPException(404, "Column not found")
    cnt = s.query(Task).filter(Task.column_id == col.id, Task.deleted_at == None).count()  # noqa: E711
    if cnt > 0:
        raise HTTPException(400, "Column with tasks cannot be removed. Move the cards first.")
    if s.query(BoardColumn).filter(BoardColumn.project_id == col.project_id).count() <= 1:
        raise HTTPException(400, "Board needs at least one column.")
    s.delete(col)
    s.commit()
    # reordena
    remaining = s.query(BoardColumn).filter(BoardColumn.project_id == col.project_id).order_by(BoardColumn.order).all()
    for i, c in enumerate(remaining):
        c.order = i
    s.commit()
    return {"ok": True}


@app.post("/api/projects/{project_id}/columns/reorder")
def reorder_columns(project_id: int, body: BoardColumnReorder, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    cols = {c.id: c for c in s.query(BoardColumn).filter(BoardColumn.project_id == project_id).all()}
    if set(body.orderedIds) != set(cols.keys()):
        raise HTTPException(400, "orderedIds must contain exactly all column ids of the project")
    for order, cid in enumerate(body.orderedIds):
        cols[cid].order = order
    s.commit()
    return [_board_column_dict(cols[cid]) for cid in body.orderedIds]


@app.post("/api/projects/{project_id}/columns/template")
def apply_column_template(project_id: int, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    if s.query(Task).filter(Task.project_id == project_id, Task.deleted_at == None).count() > 0:  # noqa: E711
        raise HTTPException(400, "Remove/move cards before applying a template with different columns.")
    for c in s.query(BoardColumn).filter(BoardColumn.project_id == project_id).all():
        s.delete(c)
    # fluxo: ... Doing -> Dev Review -> Dev Box -> In Test -> ... -> Done
    template = [("To do", False), ("Approved", False), ("Refinement", False), ("Ready for Dev", False), ("Doing", False), ("Dev Review", False), ("Dev Box", False), ("In Test", False), ("Rework", False), ("Verified", False), ("Accepted", False), ("Done", True)]
    created = []
    for order, (name, is_done) in enumerate(template):
        col = BoardColumn(project_id=project_id, name=name, order=order, is_done=is_done)
        s.add(col)
        created.append(col)
    s.commit()
    for c in created:
        s.refresh(c)
    return [_board_column_dict(c) for c in created]


@app.post("/api/tasks/{code}/move")
def move_task(code: str, body: MoveBody, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    old_col = task.column
    new_col = s.query(BoardColumn).filter(BoardColumn.id == body.columnId).first()
    if not new_col:
        raise HTTPException(404, "Column not found")
    ok, missing, message = _check_gate(task, new_col, s)
    if not ok:
        # FastAPI detail pode ser dict — o frontend trata 422 com missing/message
        raise HTTPException(status_code=422, detail={"missing": missing, "message": message})
    task.column_id = new_col.id
    task.updated_at = datetime.utcnow()
    # Marca/limpa o momento em que a tarefa ficou "concluída" (base do auto-arquivamento)
    if new_col.is_done:
        if task.done_at is None:
            task.done_at = datetime.utcnow()
    else:
        task.done_at = None
    _log(
        s,
        "task",
        task.id,
        "moved",
        f"{old_col.name if old_col else '?'} -> {new_col.name}",
    )
    s.commit()
    s.refresh(task)
    return _task_full(task)


# -- Arquivamento -----------------------------------------------------------


@app.post("/api/tasks/{code}/archive")
def archive_task(code: str, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    if task.archived_at is None:
        task.archived_at = datetime.utcnow()
        _log(s, "task", task.id, "archived", f"Task {task.code} arquivada")
        s.commit()
    s.refresh(task)
    return _task_full(task)


@app.post("/api/tasks/{code}/unarchive")
def unarchive_task(code: str, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    if task.archived_at is not None:
        task.archived_at = None
        # Reinicia a contagem para não re-arquivar na hora
        if task.column and task.column.is_done:
            task.done_at = datetime.utcnow()
        _log(s, "task", task.id, "unarchived", f"Task {task.code} desarquivada")
        s.commit()
    s.refresh(task)
    return _task_full(task)


@app.get("/api/projects/{project_id}/archived")
def list_archived(project_id: int, s: Session = Depends(db)):
    p = s.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    tasks = (
        s.query(Task)
        .filter(
            Task.project_id == project_id,
            Task.deleted_at.is_(None),
            Task.archived_at.isnot(None),
        )
        .order_by(Task.archived_at.desc())
        .all()
    )
    return [_task_brief(t) for t in tasks]


# -- Checklist --------------------------------------------------------------


@app.post("/api/tasks/{code}/checklist")
def add_checklist_item(code: str, body: ChecklistBody, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    max_order = max((c.sort_order for c in task.checklist), default=-1)
    item = TaskChecklist(task_id=task.id, title=body.title, sort_order=max_order + 1)
    s.add(item)
    s.commit()
    s.refresh(item)
    return _checklist_dict(item)


@app.patch("/api/tasks/checklist/{item_id}/toggle")
def toggle_checklist(item_id: int, s: Session = Depends(db)):
    item = s.query(TaskChecklist).filter(TaskChecklist.id == item_id).first()
    if not item:
        raise HTTPException(404, "Checklist item not found")
    item.checked = not item.checked
    s.commit()
    s.refresh(item)
    return _checklist_dict(item)


@app.delete("/api/tasks/checklist/{item_id}")
def delete_checklist(item_id: int, s: Session = Depends(db)):
    item = s.query(TaskChecklist).filter(TaskChecklist.id == item_id).first()
    if not item:
        raise HTTPException(404, "Checklist item not found")
    s.delete(item)
    s.commit()
    return {"ok": True}


# -- Dependencies -----------------------------------------------------------


@app.post("/api/tasks/{code}/dependencies")
def add_dependency(code: str, body: DependencyBody, s: Session = Depends(db)):
    blocked = _resolve_task(code, s)
    blocker = _resolve_task(body.blockerCode, s)
    if blocker.id == blocked.id:
        raise HTTPException(400, "A task cannot block itself")
    existing = (
        s.query(TaskDependency)
        .filter(TaskDependency.blocker_id == blocker.id, TaskDependency.blocked_id == blocked.id)
        .first()
    )
    if existing:
        raise HTTPException(400, "Dependency already exists")
    dep = TaskDependency(blocker_id=blocker.id, blocked_id=blocked.id)
    s.add(dep)
    s.flush()
    _log(s, "task", blocked.id, "dependency_added", f"Blocked by {blocker.code}")
    s.commit()
    s.refresh(dep)
    return {
        "id": dep.id,
        "blockerId": dep.blocker_id,
        "blockedId": dep.blocked_id,
        "blockerCode": blocker.code,
        "blockedCode": blocked.code,
    }


@app.delete("/api/tasks/{code}/dependencies/{dep_id}")
def remove_dependency(code: str, dep_id: int, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    dep = s.query(TaskDependency).filter(TaskDependency.id == dep_id).first()
    if not dep:
        raise HTTPException(404, "Dependency not found")
    if dep.blocker_id != task.id and dep.blocked_id != task.id:
        raise HTTPException(400, "Dependency does not belong to this task")
    _log(s, "task", task.id, "dependency_removed", f"Dependency {dep_id} removed")
    s.delete(dep)
    s.commit()
    return {"ok": True}


# -- Flow / Context ---------------------------------------------------------


@app.get("/api/tasks/{code}/flow")
def task_flow(code: str, s: Session = Depends(db)):
    """Return a simple dependency graph for the task."""
    task = _resolve_task(code, s)
    nodes = [{"id": task.id, "code": task.code, "title": task.title, "status": task.status}]
    edges: list[dict] = []
    seen = {task.id}

    def _walk(t: Task):
        for dep in t.blocked_by:
            b = dep.blocker
            if b.id not in seen:
                seen.add(b.id)
                nodes.append({"id": b.id, "code": b.code, "title": b.title, "status": b.status})
                _walk(b)
            edges.append({"from": b.id, "to": t.id, "type": "blocks"})
        for dep in t.blocking:
            bl = dep.blocked
            if bl.id not in seen:
                seen.add(bl.id)
                nodes.append({"id": bl.id, "code": bl.code, "title": bl.title, "status": bl.status})
                _walk(bl)
            edges.append({"from": t.id, "to": bl.id, "type": "blocks"})

    _walk(task)
    return {"nodes": nodes, "edges": edges}


@app.get("/api/tasks/{code}/context")
def task_context(code: str, s: Session = Depends(db)):
    """Aggregated context for a task — everything an agent needs."""
    task = _resolve_task(code, s)
    comments = (
        s.query(Comment)
        .filter(Comment.task_id == task.id)
        .order_by(Comment.created_at)
        .all()
    )
    docs = (
        s.query(Document)
        .filter(Document.task_id == task.id)
        .all()
    )
    activity = (
        s.query(ActivityLog)
        .filter(ActivityLog.entity_type == "task", ActivityLog.entity_id == task.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "task": _task_full(task),
        "comments": [_comment_dict(c) for c in comments],
        "documents": [_document_dict(d) for d in docs],
        "activity": [_activity_dict(a) for a in activity],
    }


# ---------------------------------------------------------------------------
# Task History / Project Changelog
# ---------------------------------------------------------------------------


@app.get("/api/tasks/{code}/history")
def task_history(code: str, s: Session = Depends(db)):
    """Structured development history for a task — review context."""
    task = _resolve_task(code, s)

    # Column transitions from activity log
    moves = (
        s.query(ActivityLog)
        .filter(ActivityLog.entity_type == "task", ActivityLog.entity_id == task.id, ActivityLog.action == "moved")
        .order_by(ActivityLog.created_at)
        .all()
    )

    # All activity
    activity = (
        s.query(ActivityLog)
        .filter(ActivityLog.entity_type == "task", ActivityLog.entity_id == task.id)
        .order_by(ActivityLog.created_at)
        .all()
    )

    # Comments (code reviews, commit refs, etc)
    comments = (
        s.query(Comment)
        .filter(Comment.task_id == task.id)
        .order_by(Comment.created_at)
        .all()
    )

    # Checklist progress
    checklist = task.checklist
    done_count = sum(1 for c in checklist if c.checked)
    total_count = len(checklist)

    # Build unified timeline
    timeline = []
    for a in activity:
        timeline.append({
            "type": "activity",
            "action": a.action,
            "detail": a.detail,
            "timestamp": a.created_at.isoformat() if a.created_at else None,
        })
    for c in comments:
        timeline.append({
            "type": "comment",
            "commentType": c.type,
            "author": c.author,
            "body": c.body[:200] + "..." if len(c.body) > 200 else c.body,
            "timestamp": c.created_at.isoformat() if c.created_at else None,
        })
    timeline.sort(key=lambda x: x.get("timestamp") or "")

    # Column flow (ordered transitions)
    column_flow = []
    for m in moves:
        column_flow.append({
            "transition": m.detail,
            "timestamp": m.created_at.isoformat() if m.created_at else None,
        })

    # Time in current status
    last_move = moves[-1] if moves else None

    return {
        "task": _task_brief(task),
        "currentStatus": task.status,
        "columnFlow": column_flow,
        "lastMoveAt": last_move.created_at.isoformat() if last_move and last_move.created_at else task.created_at.isoformat() if task.created_at else None,
        "checklist": {
            "done": done_count,
            "total": total_count,
            "items": [{"title": c.title, "checked": c.checked} for c in checklist],
        },
        "timeline": timeline,
        "commentCount": len(comments),
        "hasCodeReview": any(c.type == "CODE_REVIEW" for c in comments),
    }


@app.get("/api/projects/{project_id}/changelog")
def project_changelog(project_id: int, days: int = 7, s: Session = Depends(db)):
    """Project changelog — structured history for review context."""
    project = s.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    since = datetime.utcnow() - timedelta(days=days)

    # All tasks in this project
    tasks = (
        s.query(Task)
        .filter(Task.project_id == project_id, Task.deleted_at.is_(None))
        .all()
    )
    task_ids = [t.id for t in tasks]

    # Activity in the period
    activity = (
        s.query(ActivityLog)
        .filter(
            ActivityLog.entity_type == "task",
            ActivityLog.entity_id.in_(task_ids),
            ActivityLog.created_at >= since,
        )
        .order_by(ActivityLog.created_at.desc())
        .all()
    ) if task_ids else []

    # Comments in the period
    comments = (
        s.query(Comment)
        .filter(
            Comment.task_id.in_(task_ids),
            Comment.created_at >= since,
        )
        .order_by(Comment.created_at.desc())
        .all()
    ) if task_ids else []

    # Tasks completed in period (moved to done column)
    done_columns = s.query(BoardColumn).filter(BoardColumn.project_id == project_id, BoardColumn.is_done == True).all()
    done_col_ids = [c.id for c in done_columns]
    completed = [t for t in tasks if t.column_id in done_col_ids and t.updated_at and t.updated_at >= since]

    # Tasks currently in progress
    in_progress = [t for t in tasks if t.column and t.column.name.lower() in ("fazendo", "doing", "in progress")]

    # Group activity by day
    from collections import defaultdict
    by_day = defaultdict(list)
    for a in activity:
        day = a.created_at.strftime("%Y-%m-%d") if a.created_at else "unknown"
        by_day[day].append(_activity_dict(a))

    return {
        "project": {"id": project.id, "name": project.name, "key": project.key},
        "period": {"days": days, "since": since.isoformat()},
        "summary": {
            "totalTasks": len(tasks),
            "completedInPeriod": len(completed),
            "inProgress": len(in_progress),
            "commentsInPeriod": len(comments),
            "activityCount": len(activity),
        },
        "completed": [_task_brief(t) for t in completed],
        "inProgress": [_task_brief(t) for t in in_progress],
        "recentComments": [
            {
                "taskCode": c.task.code if c.task else "?",
                "type": c.type,
                "author": c.author,
                "body": c.body[:200] + "..." if len(c.body) > 200 else c.body,
                "createdAt": c.created_at.isoformat() if c.created_at else None,
            }
            for c in comments[:20]
        ],
        "activityByDay": dict(by_day),
    }


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


@app.get("/api/labels")
def list_labels(s: Session = Depends(db)):
    labels = s.query(Label).order_by(Label.name).all()
    return [_label_dict(lb) for lb in labels]


@app.post("/api/labels")
def create_label(body: LabelCreate, s: Session = Depends(db)):
    existing = s.query(Label).filter(Label.name == body.name).first()
    if existing:
        raise HTTPException(400, "Label already exists")
    lb = Label(name=body.name, color=body.color)
    s.add(lb)
    s.commit()
    s.refresh(lb)
    return _label_dict(lb)


@app.delete("/api/labels/{label_id}")
def delete_label(label_id: int, s: Session = Depends(db)):
    lb = s.query(Label).filter(Label.id == label_id).first()
    if not lb:
        raise HTTPException(404, "Label not found")
    s.delete(lb)
    s.commit()
    return {"ok": True}


@app.post("/api/labels/{label_id}/tasks/{task_id}")
def attach_label(label_id: int, task_id: int, s: Session = Depends(db)):
    lb = s.query(Label).filter(Label.id == label_id).first()
    if not lb:
        raise HTTPException(404, "Label not found")
    task = s.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(404, "Task not found")
    if lb not in task.labels:
        task.labels.append(lb)
        s.commit()
    return {"ok": True}


@app.delete("/api/labels/{label_id}/tasks/{task_id}")
def detach_label(label_id: int, task_id: int, s: Session = Depends(db)):
    lb = s.query(Label).filter(Label.id == label_id).first()
    if not lb:
        raise HTTPException(404, "Label not found")
    task = s.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(404, "Task not found")
    if lb in task.labels:
        task.labels.remove(lb)
        s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Epics
# ---------------------------------------------------------------------------


@app.get("/api/projects/{project_id}/epics")
def list_epics(project_id: int, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    return [_epic_dict(e) for e in
            s.query(Epic).filter(Epic.project_id == project_id).order_by(Epic.name).all()]


@app.post("/api/projects/{project_id}/epics")
def create_epic(project_id: int, body: EpicCreate, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    if not (body.name or "").strip():
        raise HTTPException(400, "Name is required")
    ep = Epic(project_id=project_id, name=body.name.strip()[:120], color=body.color)
    s.add(ep)
    s.commit()
    s.refresh(ep)
    return _epic_dict(ep)


@app.patch("/api/epics/{epic_id}")
def update_epic(epic_id: int, body: EpicUpdate, s: Session = Depends(db)):
    ep = s.query(Epic).filter(Epic.id == epic_id).first()
    if not ep:
        raise HTTPException(404, "Epic not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and (data["name"] or "").strip():
        ep.name = data["name"].strip()[:120]
    if "color" in data:
        ep.color = data["color"]
    s.commit()
    s.refresh(ep)
    return _epic_dict(ep)


@app.delete("/api/epics/{epic_id}")
def delete_epic(epic_id: int, s: Session = Depends(db)):
    ep = s.query(Epic).filter(Epic.id == epic_id).first()
    if not ep:
        raise HTTPException(404, "Epic not found")
    s.delete(ep)
    s.commit()
    return {"ok": True}


@app.post("/api/epics/{epic_id}/tasks/{task_id}")
def attach_epic(epic_id: int, task_id: int, s: Session = Depends(db)):
    ep = s.query(Epic).filter(Epic.id == epic_id).first()
    if not ep:
        raise HTTPException(404, "Epic not found")
    task = s.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(404, "Task not found")
    if ep not in task.epics:
        task.epics.append(ep)
        s.commit()
    return {"ok": True}


@app.delete("/api/epics/{epic_id}/tasks/{task_id}")
def detach_epic(epic_id: int, task_id: int, s: Session = Depends(db)):
    ep = s.query(Epic).filter(Epic.id == epic_id).first()
    if not ep:
        raise HTTPException(404, "Epic not found")
    task = s.query(Task).filter(Task.id == task_id, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(404, "Task not found")
    if ep in task.epics:
        task.epics.remove(ep)
        s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------


def _parse_goal_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        raise HTTPException(400, "Invalid dueDate (use ISO format)")


@app.get("/api/projects/{project_id}/goals")
def list_goals(project_id: int, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    goals = (s.query(Goal).filter(Goal.project_id == project_id)
             .order_by(Goal.due_date.is_(None), Goal.due_date).all())
    return [_goal_dict(g, s) for g in goals]


@app.post("/api/projects/{project_id}/goals")
def create_goal(project_id: int, body: GoalCreate, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    if not (body.name or "").strip():
        raise HTTPException(400, "Name is required")
    if body.epicId is not None and not s.query(Epic).filter(
            Epic.id == body.epicId, Epic.project_id == project_id).first():
        raise HTTPException(400, "Epic not found in this project")
    if body.sprintId is not None and not s.query(Sprint).filter(
            Sprint.id == body.sprintId, Sprint.project_id == project_id).first():
        raise HTTPException(400, "Sprint not found in this project")
    g = Goal(project_id=project_id, name=body.name.strip()[:200],
             description=(body.description or "").strip() or None,
             due_date=_parse_goal_dt(body.dueDate),
             tag=(body.tag or "").strip() or None,
             epic_id=body.epicId, sprint_id=body.sprintId)
    s.add(g)
    s.commit()
    s.refresh(g)
    return _goal_dict(g, s)


@app.get("/api/goals/{goal_id}")
def get_goal(goal_id: int, s: Session = Depends(db)):
    g = s.query(Goal).filter(Goal.id == goal_id).first()
    if not g:
        raise HTTPException(404, "Goal not found")
    return _goal_dict(g, s)


@app.patch("/api/goals/{goal_id}")
def update_goal(goal_id: int, body: GoalUpdate, s: Session = Depends(db)):
    g = s.query(Goal).filter(Goal.id == goal_id).first()
    if not g:
        raise HTTPException(404, "Goal not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and (data["name"] or "").strip():
        g.name = data["name"].strip()[:200]
    if "description" in data:
        g.description = (data["description"] or "").strip() or None
    if "dueDate" in data:
        g.due_date = _parse_goal_dt(data["dueDate"])
    if "tag" in data:
        g.tag = (data["tag"] or "").strip() or None
    if "epicId" in data:
        if data["epicId"] is not None and not s.query(Epic).filter(
                Epic.id == data["epicId"], Epic.project_id == g.project_id).first():
            raise HTTPException(400, "Epic not found in this project")
        g.epic_id = data["epicId"]
    if "sprintId" in data:
        if data["sprintId"] is not None and not s.query(Sprint).filter(
                Sprint.id == data["sprintId"], Sprint.project_id == g.project_id).first():
            raise HTTPException(400, "Sprint not found in this project")
        g.sprint_id = data["sprintId"]
    s.commit()
    s.refresh(g)
    return _goal_dict(g, s)


@app.delete("/api/goals/{goal_id}")
def delete_goal(goal_id: int, s: Session = Depends(db)):
    g = s.query(Goal).filter(Goal.id == goal_id).first()
    if not g:
        raise HTTPException(404, "Goal not found")
    s.delete(g)
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Members (responsáveis)
# ---------------------------------------------------------------------------


@app.get("/api/projects/{project_id}/members")
def list_members(project_id: int, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    stats = member_stats(s, project_id)
    return [_member_dict(st["member"], st) for st in stats]


@app.post("/api/projects/{project_id}/members")
def create_member(project_id: int, body: MemberCreate, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    m = get_or_create_member(s, project_id, body.name)
    if m is None:
        raise HTTPException(400, "Name is required")
    if body.color:
        m.color = body.color
        s.commit()
    else:
        s.commit()
    s.refresh(m)
    return _member_dict(m)


@app.delete("/api/members/{member_id}")
def delete_member(member_id: int, s: Session = Depends(db)):
    m = s.query(Member).filter(Member.id == member_id).first()
    if not m:
        raise HTTPException(404, "Member not found")
    s.delete(m)   # os cards mantêm o nome em Task.assignee
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Project links (atalhos com título)
# ---------------------------------------------------------------------------


def _validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise HTTPException(400, "URL is required")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(400, "URL deve começar com http:// ou https://")
    if len(url) > 500:
        raise HTTPException(400, "URL muito longa")
    return url


@app.get("/api/projects/{project_id}/links")
def list_links(project_id: int, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    links = s.query(ProjectLink).filter(ProjectLink.project_id == project_id).order_by(ProjectLink.sort_order, ProjectLink.id).all()
    return [_link_dict(l) for l in links]


@app.post("/api/projects/{project_id}/links")
def create_link(project_id: int, body: ProjectLinkCreate, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    title = (body.title or "").strip()
    if not title:
        raise HTTPException(400, "Title is required")
    url = _validate_url(body.url)
    order = s.query(ProjectLink).filter(ProjectLink.project_id == project_id).count()
    link = ProjectLink(project_id=project_id, title=title[:120], url=url, sort_order=order)
    s.add(link)
    s.commit()
    s.refresh(link)
    return _link_dict(link)


@app.patch("/api/links/{link_id}")
def update_link(link_id: int, body: ProjectLinkUpdate, s: Session = Depends(db)):
    link = s.query(ProjectLink).filter(ProjectLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    data = body.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        title = data["title"].strip()
        if not title:
            raise HTTPException(400, "Title is required")
        link.title = title[:120]
    if "url" in data and data["url"] is not None:
        link.url = _validate_url(data["url"])
    if "sort_order" in data and data["sort_order"] is not None:
        link.sort_order = int(data["sort_order"])
    s.commit()
    s.refresh(link)
    return _link_dict(link)


@app.delete("/api/links/{link_id}")
def delete_link(link_id: int, s: Session = Depends(db)):
    link = s.query(ProjectLink).filter(ProjectLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    s.delete(link)
    s.commit()
    # reordena
    remaining = s.query(ProjectLink).filter(ProjectLink.project_id == link.project_id).order_by(ProjectLink.sort_order).all()
    for i, l in enumerate(remaining):
        l.sort_order = i
    s.commit()
    return {"ok": True}


@app.post("/api/projects/{project_id}/links/reorder")
def reorder_links(project_id: int, body: ProjectLinkReorder, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    links = {l.id: l for l in s.query(ProjectLink).filter(ProjectLink.project_id == project_id).all()}
    if set(body.orderedIds) != set(links.keys()):
        raise HTTPException(400, "orderedIds must contain exactly all link ids of the project")
    for order, lid in enumerate(body.orderedIds):
        links[lid].sort_order = order
    s.commit()
    return [_link_dict(links[lid]) for lid in body.orderedIds]


# ---------------------------------------------------------------------------
# P0.1 — Gate de evidência / paridade
# ---------------------------------------------------------------------------


def _seed_gate_rules(project_id: int, s: Session):
    """Cria as regras padrão da migração se ainda não existirem."""
    cols = {c.name.lower(): c for c in s.query(BoardColumn).filter(BoardColumn.project_id == project_id).all()}
    # mapeia nome da coluna → regra (cobre variações do hardcoded anterior)
    seeds = {
        "in test": {"require_evidence": True, "min_evidence": 1, "forbidden_parity": "DIVERGENCIA", "message": "In Test exige evidência e paridade sem DIVERGENCIA."},
        "dev review": {"require_comment_type": "CODE_REVIEW", "message": "Dev Review exige comentário CODE_REVIEW."},
        "review": {"require_comment_type": "CODE_REVIEW", "message": "Review exige comentário CODE_REVIEW."},
        "revisão": {"require_comment_type": "CODE_REVIEW", "message": "Revisão exige comentário CODE_REVIEW."},
        "revisao": {"require_comment_type": "CODE_REVIEW", "message": "Revisao exige comentário CODE_REVIEW."},
        "accepted": {"require_parity": True, "forbidden_parity": "DIVERGENCIA", "message": "Accepted exige paridade FIEL."},
        "done": {"require_pr_merged": True, "message": "Done exige PR mergeado quando houver link."},
    }
    changed = False
    for col_name, cfg in seeds.items():
        col = cols.get(col_name)
        if not col:
            continue
        existing = s.query(GateRule).filter(GateRule.project_id == project_id, GateRule.column_id == col.id).first()
        if existing:
            continue
        r = GateRule(project_id=project_id, column_id=col.id, **cfg)
        s.add(r)
        changed = True
    if changed:
        s.commit()


def _check_gate(task: Task, dest_col: BoardColumn, s: Session) -> tuple[bool, list[str], str]:
    """Valida se o card pode entrar na coluna de destino. Retorna (ok, missing, message)."""
    rule = s.query(GateRule).filter(GateRule.project_id == task.project_id, GateRule.column_id == dest_col.id).first()
    if not rule:
        # tenta semear para o projeto de migração na primeira vez
        _seed_gate_rules(task.project_id, s)
        rule = s.query(GateRule).filter(GateRule.project_id == task.project_id, GateRule.column_id == dest_col.id).first()
        if not rule:
            return True, [], ""
    missing: list[str] = []
    # evidência
    if rule.require_evidence:
        evs = s.query(Evidence).filter(Evidence.task_id == task.id).all()
        if len(evs) < (rule.min_evidence or 1):
            missing.append("EVIDENCIA")
        elif rule.required_evidence_kinds:
            required = {k.strip().upper() for k in rule.required_evidence_kinds.split(",") if k.strip()}
            kinds = {e.kind.upper() for e in evs}
            if not required.issubset(kinds):
                missing.append("EVIDENCIA_KIND")
    # paridade
    if rule.require_parity:
        pars = s.query(ParityResult).filter(ParityResult.task_id == task.id).all()
        if not pars:
            missing.append("PARITY_FIEL")
        else:
            # se forbid DIVERGENCIA, bloqueia se existir
            if rule.forbidden_parity:
                forb = rule.forbidden_parity.upper()
                if any(p.status.upper() == forb for p in pars):
                    missing.append("PARITY_FIEL")
            # exige ao menos um FIEL quando require_parity
            if not any(p.status.upper() == "FIEL" for p in pars):
                # se não tem FIEL, mas tem BLOQUEADO/NAO_EXECUTADO, também falta
                missing.append("PARITY_FIEL")
    elif rule.forbidden_parity:
        pars = s.query(ParityResult).filter(ParityResult.task_id == task.id).all()
        forb = rule.forbidden_parity.upper()
        if any(p.status.upper() == forb for p in pars):
            missing.append("PARITY_FIEL")
    # comentário
    if rule.require_comment_type:
        has = s.query(Comment).filter(Comment.task_id == task.id, Comment.type == rule.require_comment_type).first()
        if not has:
            missing.append(rule.require_comment_type)
    # PR mergeado — por enquanto verifica se há link de PR com status merged (se houver TaskLink no futuro, aqui é placeholder)
    # Se não houver TaskLink, ignora; quando P0.2 existir, verificará TaskLink.kind==PR e status==merged
    if rule.require_pr_merged:
        # sem TaskLink ainda, não bloqueia por falta de PR (backward compat); quando houver, validar
        pass
    if missing:
        return False, missing, rule.message or f"{dest_col.name} exige: {', '.join(missing)}"
    return True, [], ""


@app.get("/api/projects/{project_id}/gate-rules")
def list_gate_rules(project_id: int, s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    _seed_gate_rules(project_id, s)
    rules = s.query(GateRule).filter(GateRule.project_id == project_id).all()
    return [_gate_rule_dict(r) for r in rules]


@app.put("/api/projects/{project_id}/gate-rules")
def put_gate_rules(project_id: int, body: list[GateRuleUpsert], s: Session = Depends(db)):
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    # upsert por columnId
    for item in body:
        col = s.query(BoardColumn).filter(BoardColumn.id == item.columnId, BoardColumn.project_id == project_id).first()
        if not col:
            raise HTTPException(400, f"Column {item.columnId} not in project {project_id}")
        rule = s.query(GateRule).filter(GateRule.project_id == project_id, GateRule.column_id == item.columnId).first()
        if not rule:
            rule = GateRule(project_id=project_id, column_id=item.columnId)
            s.add(rule)
        data = item.model_dump(exclude_unset=True)
        for k, v in data.items():
            if k == "columnId":
                continue
            setattr(rule, k, v)
    s.commit()
    rules = s.query(GateRule).filter(GateRule.project_id == project_id).all()
    return [_gate_rule_dict(r) for r in rules]


@app.post("/api/tasks/{code}/evidence")
def create_evidence(code: str, body: EvidenceCreate, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    kind = (body.kind or "").strip().upper()
    if not kind:
        raise HTTPException(400, "kind is required")
    ev = Evidence(
        task_id=task.id,
        kind=kind,
        title=(body.title or "").strip()[:200] if body.title else None,
        url=(body.url or "").strip() if body.url else None,
        environment=(body.environment or "").strip()[:80] if body.environment else None,
        executor=(body.executor or "").strip()[:100] if body.executor else None,
        result=(body.result or "").strip().upper()[:20] if body.result else None,
        notes=body.notes,
    )
    if body.executed_at:
        try:
            ev.executed_at = datetime.fromisoformat(body.executed_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, "executed_at must be ISO datetime")
    s.add(ev)
    s.commit()
    s.refresh(ev)
    return _evidence_dict(ev)


@app.get("/api/tasks/{code}/evidence")
def list_evidence(code: str, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    evs = s.query(Evidence).filter(Evidence.task_id == task.id).order_by(Evidence.created_at).all()
    return [_evidence_dict(e) for e in evs]


@app.delete("/api/tasks/evidence/{evidence_id}")
def delete_evidence(evidence_id: int, s: Session = Depends(db)):
    ev = s.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(404, "Evidence not found")
    s.delete(ev)
    s.commit()
    return {"ok": True}


@app.post("/api/tasks/{code}/parity")
def create_parity(code: str, body: ParityCreate, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    status = (body.status or "").strip().upper()
    if status not in ("FIEL", "DIVERGENCIA", "BLOQUEADO", "NAO_EXECUTADO"):
        raise HTTPException(400, "status must be FIEL|DIVERGENCIA|BLOQUEADO|NAO_EXECUTADO")
    pr = ParityResult(task_id=task.id, case_name=body.case_name.strip()[:200], status=status, expected=body.expected, actual=body.actual, notes=body.notes)
    s.add(pr)
    s.commit()
    s.refresh(pr)
    return _parity_dict(pr)


@app.get("/api/tasks/{code}/parity")
def list_parity(code: str, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    pars = s.query(ParityResult).filter(ParityResult.task_id == task.id).order_by(ParityResult.created_at).all()
    return [_parity_dict(p) for p in pars]


@app.patch("/api/tasks/parity/{parity_id}")
def update_parity(parity_id: int, body: ParityUpdate, s: Session = Depends(db)):
    pr = s.query(ParityResult).filter(ParityResult.id == parity_id).first()
    if not pr:
        raise HTTPException(404, "Parity not found")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        st = data["status"].strip().upper()
        if st not in ("FIEL", "DIVERGENCIA", "BLOQUEADO", "NAO_EXECUTADO"):
            raise HTTPException(400, "status must be FIEL|DIVERGENCIA|BLOQUEADO|NAO_EXECUTADO")
        pr.status = st
    if "case_name" in data and data["case_name"] is not None:
        pr.case_name = data["case_name"].strip()[:200]
    if "expected" in data:
        pr.expected = data["expected"]
    if "actual" in data:
        pr.actual = data["actual"]
    if "notes" in data:
        pr.notes = data["notes"]
    s.commit()
    s.refresh(pr)
    return _parity_dict(pr)


@app.get("/api/tasks/{code}/quality")
def task_quality(code: str, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    evs = s.query(Evidence).filter(Evidence.task_id == task.id).all()
    pars = s.query(ParityResult).filter(ParityResult.task_id == task.id).all()
    counts = {"fiel": 0, "divergencia": 0, "bloqueado": 0, "nao_executado": 0}
    for p in pars:
        k = p.status.lower()
        if k == "fiel":
            counts["fiel"] += 1
        elif k == "divergencia":
            counts["divergencia"] += 1
        elif k == "bloqueado":
            counts["bloqueado"] += 1
        elif k == "nao_executado":
            counts["nao_executado"] += 1
    # gate_ok para cada coluna? retorna geral: se há regra que bloquearia
    return {
        "task": _task_brief(task),
        "evidence_count": len(evs),
        "parity": counts,
        "gate_ok": counts["divergencia"] == 0,
    }


# ---------------------------------------------------------------------------
# Daily do projeto (registro de trabalho por dia)
# ---------------------------------------------------------------------------


@app.get("/api/projects/{project_id}/daily")
def list_project_daily(
    project_id: int,
    date: Optional[str] = None,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    author: Optional[str] = None,
    kind: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
    s: Session = Depends(db),
):
    """Lista os registros diários do projeto.

    Filtros: `date` (dia exato), `dateFrom`/`dateTo` (intervalo),
    `author`, `kind` (WORK|BLOCKER|DECISION|NOTE) e `q` (busca no texto).
    """
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")

    query = s.query(ProjectDailyEntry).filter(ProjectDailyEntry.project_id == project_id)
    if date:
        query = query.filter(ProjectDailyEntry.date == _daily_validate_date(date))
    else:
        if dateFrom:
            query = query.filter(ProjectDailyEntry.date >= _daily_validate_date(dateFrom))
        if dateTo:
            query = query.filter(ProjectDailyEntry.date <= _daily_validate_date(dateTo))
    if author:
        query = query.filter(ProjectDailyEntry.author.ilike(f"%{author.strip()}%"))
    if kind:
        query = query.filter(ProjectDailyEntry.kind == _daily_validate_kind(kind))
    if q:
        query = query.filter(ProjectDailyEntry.body.ilike(f"%{q.strip()}%"))

    limit = max(1, min(int(limit or 200), 1000))
    # dia mais recente primeiro; dentro do dia, a ordem do documento
    entries = query.order_by(
        ProjectDailyEntry.date.desc(),
        ProjectDailyEntry.sort_order.asc(),
        ProjectDailyEntry.id.asc(),
    ).limit(limit).all()
    return [_daily_dict(e) for e in entries]


@app.post("/api/projects/{project_id}/daily")
def create_project_daily(project_id: int, body: ProjectDailyCreate, s: Session = Depends(db)):
    """Cria um registro diário (comentário de trabalho do dia)."""
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    text = (body.body or "").strip()
    if not text:
        raise HTTPException(400, "body is required")

    prox = (
        s.query(ProjectDailyEntry)
        .filter(ProjectDailyEntry.project_id == project_id, ProjectDailyEntry.date == _daily_validate_date(body.date))
        .count()
    )
    entry = ProjectDailyEntry(
        project_id=project_id,
        date=_daily_validate_date(body.date),
        kind=_daily_validate_kind(body.kind),
        section=_daily_validate_section(body.section),
        title=(body.title or "").strip()[:200],
        sort_order=prox,
        body=text,
        author=(body.author or "").strip()[:100] or None,
        minutes=body.minutes,
        task_code=(body.taskCode or "").strip()[:40],
    )
    s.add(entry)
    s.flush()
    _log(s, "project", project_id, "daily_added", f"{entry.date} {entry.kind}")
    s.commit()
    s.refresh(entry)
    return _daily_dict(entry)


@app.get("/api/project-daily/{entry_id}")
def get_project_daily(entry_id: int, s: Session = Depends(db)):
    entry = s.query(ProjectDailyEntry).filter(ProjectDailyEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Daily entry not found")
    return _daily_dict(entry)


@app.patch("/api/project-daily/{entry_id}")
def update_project_daily(entry_id: int, body: ProjectDailyUpdate, s: Session = Depends(db)):
    entry = s.query(ProjectDailyEntry).filter(ProjectDailyEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Daily entry not found")

    data = body.model_dump(exclude_unset=True)
    if "body" in data and data["body"] is not None:
        text = data["body"].strip()
        if not text:
            raise HTTPException(400, "body cannot be empty")
        entry.body = text
    if "date" in data and data["date"] is not None:
        entry.date = _daily_validate_date(data["date"])
    if "kind" in data and data["kind"] is not None:
        entry.kind = _daily_validate_kind(data["kind"])
    if "author" in data:
        entry.author = (data["author"] or "").strip()[:100] or None
    if "minutes" in data:
        entry.minutes = data["minutes"]
    if "taskCode" in data:
        entry.task_code = (data["taskCode"] or "").strip()[:40]
    if "title" in data:
        entry.title = (data["title"] or "").strip()[:200]
    if "section" in data and data["section"] is not None:
        entry.section = _daily_validate_section(data["section"])
    if "sortOrder" in data and data["sortOrder"] is not None:
        entry.sort_order = int(data["sortOrder"])
    entry.updated_at = datetime.utcnow()
    s.commit()
    s.refresh(entry)
    return _daily_dict(entry)


@app.delete("/api/project-daily/{entry_id}")
def delete_project_daily(entry_id: int, s: Session = Depends(db)):
    entry = s.query(ProjectDailyEntry).filter(ProjectDailyEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Daily entry not found")
    s.delete(entry)
    s.commit()
    return {"ok": True}


@app.get("/api/projects/{project_id}/daily/summary")
def project_daily_summary(
    project_id: int,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    s: Session = Depends(db),
):
    """Resumo por dia e por tipo — alimenta o painel do daily no board."""
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")

    query = s.query(ProjectDailyEntry).filter(ProjectDailyEntry.project_id == project_id)
    if dateFrom:
        query = query.filter(ProjectDailyEntry.date >= _daily_validate_date(dateFrom))
    if dateTo:
        query = query.filter(ProjectDailyEntry.date <= _daily_validate_date(dateTo))
    entries = query.order_by(ProjectDailyEntry.date).all()

    by_day: dict[str, dict] = {}
    by_kind: dict[str, int] = {k: 0 for k in DAILY_KINDS}
    authors: dict[str, int] = {}
    total_minutes = 0
    for e in entries:
        day = by_day.setdefault(e.date, {"date": e.date, "entries": 0, "minutes": 0, "authors": []})
        day["entries"] += 1
        day["minutes"] += e.minutes or 0
        if e.author and e.author not in day["authors"]:
            day["authors"].append(e.author)
        by_kind[e.kind or "WORK"] = by_kind.get(e.kind or "WORK", 0) + 1
        if e.author:
            authors[e.author] = authors.get(e.author, 0) + 1
        total_minutes += e.minutes or 0

    return {
        "projectId": project_id,
        "total": len(entries),
        "totalMinutes": total_minutes,
        "byKind": by_kind,
        "byAuthor": authors,
        "days": sorted(by_day.values(), key=lambda d: d["date"], reverse=True),
    }


@app.get("/api/projects/{project_id}/metrics/daily-advance")
def project_metrics_daily_advance(project_id: int, refresh: bool = False, s: Session = Depends(db)):
    """Resumo do avanço ontem → hoje a partir dos docs de daily (IA + fallback)."""
    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    from relay.daily_advance import project_advance

    return project_advance(s, project_id, refresh=bool(refresh))


def _parse_exclude(raw: str | None) -> set[int]:
    """`?exclude=1,2` -> {1, 2} (ids de coluna fora do cálculo; resto ignorado)."""
    saidos: set[int] = set()
    for parte in (raw or "").split(","):
        parte = parte.strip()
        if parte.isdigit():
            saidos.add(int(parte))
    return saidos


@app.get("/api/projects/{project_id}/metrics/dimensions")
def project_metrics_dimensions(project_id: int, exclude: str | None = None, s: Session = Depends(db)):
    """Métricas separadas por dimensão: módulo (com submódulos), sprint,
    plataforma e natureza. Evita misturar label de módulo com sprint/tag."""
    from relay.dimensions import aggregate_dimensions

    project = s.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    colunas = (
        s.query(BoardColumn)
        .filter(BoardColumn.project_id == project_id)
        .order_by(BoardColumn.order)
        .all()
    )
    done_ids = {c.id for c in colunas if c.is_done}
    tasks = (
        s.query(Task)
        .filter(
            Task.project_id == project_id,
            Task.deleted_at == None,  # noqa: E711
            Task.archived_at == None,  # noqa: E711
        )
        .all()
    )
    fora = _parse_exclude(exclude)
    if fora:
        tasks = [t for t in tasks if t.column_id not in fora]
    dados = aggregate_dimensions(tasks, done_ids, colunas)
    return {"projectId": project_id, "excluded": sorted(fora), **dados}


@app.get("/api/projects/{project_id}/metrics/stages")
def project_metrics_stages(project_id: int, stage: str | None = None, exclude: str | None = None, s: Session = Depends(db)):
    """Quem **chegou** em cada estágio (cumulativo) e o corte por grupo (soma 100%).

    "Chegou" = está na coluna ou já passou por ela (ordem das colunas + histórico
    de movimentação). `stage` (ex.: `dev-box`) devolve o recorte daquele estágio.
    """
    from relay.stages import compute_stages

    project = s.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    columns = s.query(BoardColumn).filter(BoardColumn.project_id == project_id).all()
    tasks = (
        s.query(Task)
        .filter(
            Task.project_id == project_id,
            Task.deleted_at == None,  # noqa: E711
            Task.archived_at == None,  # noqa: E711
        )
        .all()
    )
    historico = (
        s.query(ActivityLog.entity_id, ActivityLog.detail)
        .filter(ActivityLog.entity_type == "task", ActivityLog.action == "moved")
        .all()
    )
    fora = _parse_exclude(exclude)
    if fora:
        tasks = [t for t in tasks if t.column_id not in fora]
    dados = compute_stages(tasks, columns, historico)
    resposta = {"projectId": project_id, "excluded": sorted(fora), **dados}
    if stage:
        alvo = next((x for x in dados["stages"] if x["stage"] == stage), None)
        if not alvo:
            raise HTTPException(404, f"Stage not found: {stage}")
        resposta["selected"] = {
            **alvo,
            "groups": dados["breakdown"].get(stage, []),
        }
    return resposta


@app.get("/api/projects/{project_id}/metrics/export.pdf")
def export_project_metrics_pdf(project_id: int, exclude: str | None = None, s: Session = Depends(db)):
    """Relatório de métricas do projeto em PDF (mesmo conteúdo da aba Métricas)."""
    from relay.metrics_pdf import build_metrics_pdf, metrics_pdf_filename

    project = s.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    try:
        pdf = build_metrics_pdf(s, project, exclude_ids=_parse_exclude(exclude))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"failed to build PDF: {e}")
    filename = metrics_pdf_filename(project)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/projects/{project_id}/daily/export")
def export_project_daily(project_id: int, date: Optional[str] = None, s: Session = Depends(db)):
    """Monta o markdown do dia no formato do vault (`DD-MM-YYYY - Daily - tema.md`)."""
    from relay.daily_doc import DailyBlock, render_daily_markdown, suggested_filename

    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")
    day = _daily_validate_date(date)

    entries = (
        s.query(ProjectDailyEntry)
        .filter(ProjectDailyEntry.project_id == project_id, ProjectDailyEntry.date == day)
        .order_by(ProjectDailyEntry.sort_order, ProjectDailyEntry.id)
        .all()
    )
    if not entries:
        raise HTTPException(404, f"No daily entries for {day}")

    blocks = [
        DailyBlock(
            section=e.section or "ITEMS",
            title=e.title or "",
            body=e.body or "",
            kind=e.kind or "WORK",
            author=e.author,
            minutes=e.minutes,
            task_code=e.task_code or "",
            sort_order=e.sort_order or 0,
        )
        for e in entries
    ]

    # o tema do dia vem do registro INTRO (título) ou do primeiro ITEMS
    titulo = ""
    for e in entries:
        if e.section == "INTRO" and e.title:
            titulo = e.title
            break
    if not titulo:
        for e in entries:
            if e.section == "ITEMS" and e.title:
                titulo = e.title[:80]
                break

    markdown = render_daily_markdown(day, titulo, blocks)
    filename, month_dir = suggested_filename(day, titulo)
    return {
        "projectId": project_id,
        "date": day,
        "title": titulo,
        "markdown": markdown,
        "filename": filename,
        "monthDir": month_dir,
        "entries": len(entries),
    }


@app.post("/api/projects/{project_id}/daily/import")
def import_project_daily(project_id: int, body: ProjectDailyImport, s: Session = Depends(db)):
    """Importa um doc de daily (markdown) e cria os registros do dia.

    Aceita `content` (markdown cru) ou `path` (arquivo .md). Com
    `replace=true` (padrão) os registros daquele dia são substituídos.
    """
    from pathlib import Path as _Path

    from relay.daily_doc import parse_daily_markdown

    if not s.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(404, "Project not found")

    content = body.content
    if not content:
        if not body.path:
            raise HTTPException(400, "content or path is required")
        p = _Path(body.path).expanduser()
        if not p.is_absolute():
            raise HTTPException(400, "path must be absolute")
        if not p.exists() or not p.is_file():
            raise HTTPException(404, f"file not found: {p}")
        content = p.read_text(encoding="utf-8", errors="replace")

    day, titulo, blocks = parse_daily_markdown(content)
    if not day:
        raise HTTPException(400, "could not find the '# Daily - DD/MM/YYYY' header")
    if not blocks:
        raise HTTPException(400, "no content found in the daily document")

    if body.replace:
        for old in (
            s.query(ProjectDailyEntry)
            .filter(ProjectDailyEntry.project_id == project_id, ProjectDailyEntry.date == day)
            .all()
        ):
            s.delete(old)
        s.flush()

    base = (
        s.query(ProjectDailyEntry)
        .filter(ProjectDailyEntry.project_id == project_id, ProjectDailyEntry.date == day)
        .count()
    )
    for i, b in enumerate(blocks):
        s.add(ProjectDailyEntry(
            project_id=project_id,
            date=day,
            kind=(b.kind or "WORK")[:20],
            section=(b.section or "ITEMS")[:20],
            title=(b.title or "")[:200],
            sort_order=base + i,
            body=b.body or "",
            author=(b.author or None),
            minutes=b.minutes,
            task_code=(b.task_code or "")[:40],
        ))
    _log(s, "project", project_id, "daily_imported", f"{day} ({len(blocks)} blocos)")
    s.commit()
    return {
        "ok": True,
        "projectId": project_id,
        "date": day,
        "title": titulo,
        "created": len(blocks),
        "replaced": bool(body.replace),
    }


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@app.get("/api/comments")
def list_comments(taskId: int, s: Session = Depends(db)):
    comments = (
        s.query(Comment)
        .filter(Comment.task_id == taskId)
        .order_by(Comment.created_at)
        .all()
    )
    return [_comment_dict(c) for c in comments]


@app.post("/api/comments")
def create_comment(body: CommentCreate, s: Session = Depends(db)):
    task = s.query(Task).filter(Task.id == body.taskId, Task.deleted_at.is_(None)).first()
    if not task:
        raise HTTPException(404, "Task not found")
    c = Comment(
        task_id=body.taskId,
        body=body.body,
        type=body.type,
        author=(body.author or "local").strip() or "local",
    )
    s.add(c)
    s.flush()
    _log(s, "comment", c.id, "created", f"Comment on task {task.code}")
    s.commit()
    s.refresh(c)
    return _comment_dict(c)


@app.patch("/api/comments/{comment_id}")
def update_comment(comment_id: int, body: CommentUpdate, s: Session = Depends(db)):
    c = s.query(Comment).filter(Comment.id == comment_id).first()
    if not c:
        raise HTTPException(404, "Comment not found")
    c.body = body.body
    if body.author is not None:
        c.author = (body.author or "local").strip() or "local"
    s.commit()
    s.refresh(c)
    return _comment_dict(c)


@app.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: int, s: Session = Depends(db)):
    c = s.query(Comment).filter(Comment.id == comment_id).first()
    if not c:
        raise HTTPException(404, "Comment not found")
    s.delete(c)
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@app.get("/api/documents")
def list_documents(
    taskId: Optional[int] = None,
    projectId: Optional[int] = None,
    s: Session = Depends(db),
):
    q = s.query(Document)
    if taskId:
        q = q.filter(Document.task_id == taskId)
    if projectId:
        q = q.filter(Document.project_id == projectId)
    return [_document_dict(d) for d in q.order_by(Document.created_at.desc()).all()]


@app.post("/api/documents")
def create_document(body: DocumentCreate, s: Session = Depends(db)):
    doc = Document(
        title=body.title,
        body=body.body,
        type=body.type,
        task_id=body.taskId,
        project_id=body.projectId,
    )
    s.add(doc)
    s.commit()
    s.refresh(doc)
    return _document_dict(doc)


@app.put("/api/documents/{doc_id}")
def update_document(doc_id: int, body: DocumentUpdate, s: Session = Depends(db)):
    doc = s.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    data = body.model_dump(exclude_unset=True)
    for field in ("title", "body", "type"):
        if field in data:
            setattr(doc, field, data[field])
    doc.version = (doc.version or 1) + 1
    doc.updated_at = datetime.utcnow()
    s.commit()
    s.refresh(doc)
    return _document_dict(doc)


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, s: Session = Depends(db)):
    doc = s.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    s.delete(doc)
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Base de conhecimento (2º cérebro): notas KB + backlinks + Q&A (RAG-lite)
# ---------------------------------------------------------------------------


def _kb_notes(s: Session, project_id: Optional[int]) -> list[Document]:
    q = s.query(Document).filter(Document.type == "KB")
    if project_id is not None:
        q = q.filter(Document.project_id == project_id)
    return q.order_by(Document.updated_at.desc()).all()


@app.get("/api/kb/notes")
def kb_notes(projectId: Optional[int] = None, q: Optional[str] = None,
             s: Session = Depends(db)):
    from relay.kb import backlinks
    notes = _kb_notes(s, projectId)
    dicts = [{"id": d.id, "title": d.title, "body": d.body or "",
              "projectId": d.project_id,
              "updatedAt": d.updated_at.isoformat() if d.updated_at else None}
             for d in notes]
    links = backlinks(dicts)
    for d in dicts:
        d["backlinks"] = links.get(d["id"], [])
    if q:
        ql = q.lower()
        dicts = [d for d in dicts if ql in f"{d['title']} {d['body']}".lower()]
    return dicts


class KbAskBody(BaseModel):
    question: str
    projectId: Optional[int] = None


@app.post("/api/kb/ask")
def kb_ask(body: KbAskBody, s: Session = Depends(db)):
    from relay.kb import answer
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Pergunta vazia")
    notes = [{"id": d.id, "title": d.title, "body": d.body or ""}
             for d in _kb_notes(s, body.projectId)]
    if not notes:
        return {"answer": "Nenhuma nota na base de conhecimento ainda.", "sources": []}
    try:
        return answer(notes, body.question)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Agentic memory (por workspace) — fatos/decisões com busca híbrida
# ---------------------------------------------------------------------------


class MemoryCreate(BaseModel):
    title: str
    content: str
    kind: Optional[str] = "fact"
    summary: Optional[str] = ""
    tags: Optional[list[str] | str] = None
    projectId: Optional[int] = None
    taskId: Optional[int] = None
    sourceType: Optional[str] = "manual"
    sourceId: Optional[int] = None
    importance: Optional[float] = 0.5
    embed: Optional[bool] = True


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    kind: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[list[str] | str] = None
    projectId: Optional[int] = None
    taskId: Optional[int] = None
    importance: Optional[float] = None
    reembed: Optional[bool] = True


class MemorySearchBody(BaseModel):
    query: str
    kind: Optional[str] = None
    projectId: Optional[int] = None
    taskId: Optional[int] = None
    tags: Optional[str] = None
    topK: Optional[int] = 8
    minScore: Optional[float] = 0.0


class MemoryIngestBody(BaseModel):
    sourceType: str  # task | comment | document | daily | recording | sprint | kb
    sourceId: int
    projectId: Optional[int] = None


class MemoryAskBody(BaseModel):
    question: str
    projectId: Optional[int] = None
    topK: Optional[int] = 6


class MemoryReembedBody(BaseModel):
    onlyMissing: Optional[bool] = True
    limit: Optional[int] = 200


@app.get("/api/memory")
def memory_list(
    q: Optional[str] = None,
    kind: Optional[str] = None,
    projectId: Optional[int] = None,
    taskId: Optional[int] = None,
    tags: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    s: Session = Depends(db),
):
    from relay import memory as mem
    return mem.list_entries(
        s, kind=kind, project_id=projectId, task_id=taskId,
        tags=tags, q=q, limit=limit, offset=offset,
    )


@app.get("/api/memory/stats")
def memory_stats(s: Session = Depends(db)):
    from relay import memory as mem
    return mem.stats(s)


@app.get("/api/memory/kinds")
def memory_kinds():
    from relay import memory as mem
    return {
        "kinds": list(mem.MEMORY_KINDS),
        "sourceTypes": list(mem.SOURCE_TYPES),
    }


@app.post("/api/memory")
def memory_create(body: MemoryCreate, s: Session = Depends(db)):
    from relay import memory as mem
    if not (body.content or "").strip():
        raise HTTPException(400, "content obrigatório")
    try:
        entry = mem.remember(
            s,
            title=body.title,
            content=body.content,
            kind=body.kind or "fact",
            summary=body.summary or "",
            tags=body.tags,
            project_id=body.projectId,
            task_id=body.taskId,
            source_type=body.sourceType or "manual",
            source_id=body.sourceId,
            importance=body.importance if body.importance is not None else 0.5,
            embed=bool(body.embed if body.embed is not None else True),
        )
        s.flush()
        _log(s, "memory", entry.id, "created", entry.title)
        s.commit()
        s.refresh(entry)
        return mem.entry_to_dict(entry)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        s.rollback()
        raise HTTPException(400, str(e))


@app.get("/api/memory/{mem_id}")
def memory_get(mem_id: int, s: Session = Depends(db)):
    from relay import memory as mem
    entry = (
        s.query(MemoryEntry)
        .filter(MemoryEntry.id == mem_id, MemoryEntry.deleted_at.is_(None))
        .first()
    )
    if not entry:
        raise HTTPException(404, "Memória não encontrada")
    return mem.entry_to_dict(entry)


@app.patch("/api/memory/{mem_id}")
def memory_update(mem_id: int, body: MemoryUpdate, s: Session = Depends(db)):
    from relay import memory as mem
    entry = (
        s.query(MemoryEntry)
        .filter(MemoryEntry.id == mem_id, MemoryEntry.deleted_at.is_(None))
        .first()
    )
    if not entry:
        raise HTTPException(404, "Memória não encontrada")
    data = body.model_dump(exclude_unset=True)
    try:
        mem.update_entry(
            s,
            entry,
            title=data.get("title"),
            content=data.get("content"),
            kind=data.get("kind"),
            summary=data.get("summary"),
            tags=data.get("tags") if "tags" in data else None,
            project_id=data["projectId"] if "projectId" in data else ...,
            task_id=data["taskId"] if "taskId" in data else ...,
            importance=data.get("importance"),
            reembed=bool(data.get("reembed", True)),
        )
        s.commit()
        s.refresh(entry)
        return mem.entry_to_dict(entry)
    except Exception as e:  # noqa: BLE001
        s.rollback()
        raise HTTPException(400, str(e))


@app.delete("/api/memory/{mem_id}")
def memory_delete(mem_id: int, s: Session = Depends(db)):
    from relay import memory as mem
    entry = (
        s.query(MemoryEntry)
        .filter(MemoryEntry.id == mem_id, MemoryEntry.deleted_at.is_(None))
        .first()
    )
    if not entry:
        raise HTTPException(404, "Memória não encontrada")
    mem.soft_delete(s, entry)
    s.commit()
    return {"ok": True}


@app.post("/api/memory/search")
def memory_search(body: MemorySearchBody, s: Session = Depends(db)):
    from relay import memory as mem
    if not (body.query or "").strip():
        raise HTTPException(400, "query obrigatória")
    hits = mem.search(
        s,
        body.query,
        kind=body.kind,
        project_id=body.projectId,
        task_id=body.taskId,
        tags=body.tags,
        top_k=body.topK or 8,
        min_score=body.minScore or 0.0,
        mark_accessed=True,
    )
    return {
        "query": body.query,
        "count": len(hits),
        "results": hits,
        "agentContext": mem.format_for_agent(hits),
    }


@app.post("/api/memory/ingest")
def memory_ingest(body: MemoryIngestBody, s: Session = Depends(db)):
    from relay import memory as mem
    try:
        created = mem.ingest(
            s, body.sourceType, body.sourceId, project_id=body.projectId
        )
        return {"ok": True, "count": len(created), "entries": created}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        s.rollback()
        raise HTTPException(400, str(e))


@app.post("/api/memory/ask")
def memory_ask(body: MemoryAskBody, s: Session = Depends(db)):
    from relay import memory as mem
    if not (body.question or "").strip():
        raise HTTPException(400, "Pergunta vazia")
    try:
        return mem.answer(
            s, body.question, project_id=body.projectId, top_k=body.topK or 6
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, str(e))


@app.post("/api/memory/reembed")
def memory_reembed(body: MemoryReembedBody, s: Session = Depends(db)):
    from relay import memory as mem
    try:
        return mem.reembed_all(
            s,
            only_missing=bool(body.onlyMissing if body.onlyMissing is not None else True),
            limit=body.limit or 200,
        )
    except Exception as e:  # noqa: BLE001
        s.rollback()
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------


@app.get("/api/activity")
def list_activity(
    entityType: Optional[str] = None,
    entityId: Optional[int] = None,
    limit: int = Query(default=50, le=200),
    s: Session = Depends(db),
):
    q = s.query(ActivityLog)
    if entityType:
        q = q.filter(ActivityLog.entity_type == entityType.lower())
    if entityId:
        q = q.filter(ActivityLog.entity_id == entityId)
    entries = q.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return [_activity_dict(a) for a in entries]


# ============================= TODOS =======================================


class TodoCreate(BaseModel):
    text: str
    dueAt: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    recurrence: Optional[str] = None  # NONE | DAILY | WEEKLY | MONTHLY
    projectId: Optional[int] = None
    tags: Optional[str] = None


class TodoUpdate(BaseModel):
    text: Optional[str] = None
    done: Optional[bool] = None
    dueAt: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    recurrence: Optional[str] = None
    projectId: Optional[int] = None
    tags: Optional[str] = None


class TodoSnooze(BaseModel):
    minutes: int = 10


def _todo_dict(t: Todo) -> dict:
    return {
        "id": t.id,
        "text": t.text,
        "done": t.done,
        "sortOrder": t.sort_order,
        "priority": t.priority or "MEDIUM",
        "notes": t.notes,
        "recurrence": t.recurrence or "NONE",
        "dueAt": t.due_at.isoformat() if t.due_at else None,
        "snoozedUntil": t.snoozed_until.isoformat() if t.snoozed_until else None,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
        "completedAt": t.completed_at.isoformat() if t.completed_at else None,
        "projectId": t.project_id,
        "tags": t.tags or "",
    }


@app.get("/api/todos")
def list_todos(
    done: Optional[bool] = None,
    projectId: Optional[int] = None,
    q: Optional[str] = None,
    tags: Optional[str] = None,
    s: Session = Depends(db),
):
    query = s.query(Todo)
    if done is not None:
        query = query.filter(Todo.done.is_(done))
    if projectId is not None:
        query = query.filter(Todo.project_id == projectId)
    if tags:
        for tg in [t.strip() for t in tags.split(",") if t.strip()]:
            query = query.filter(Todo.tags.ilike(f"%{tg}%"))
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter((Todo.text.ilike(like)) | (Todo.notes.ilike(like)) | (Todo.tags.ilike(like)))
    todos = query.order_by(Todo.done, Todo.sort_order, Todo.id).all()
    return [_todo_dict(t) for t in todos]


@app.get("/api/todos/pending")
def pending_todos(s: Session = Depends(db)):
    """TODOs cujo horário já chegou e ainda não foram feitos (nem adiados).
    Usado pelo lembrete periódico da interface. Agendamento em hora LOCAL."""
    now = datetime.now()
    todos = (
        s.query(Todo)
        .filter(
            Todo.done.is_(False),
            Todo.due_at.isnot(None),
            Todo.due_at <= now,
        )
        .order_by(Todo.due_at)
        .all()
    )
    pending = [t for t in todos if not (t.snoozed_until and t.snoozed_until > now)]
    return {"count": len(pending), "items": [_todo_dict(t) for t in pending]}


@app.post("/api/todos")
def create_todo(body: TodoCreate, s: Session = Depends(db)):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text é obrigatório")
    t = Todo(
        text=text, sort_order=s.query(Todo).count(),
        priority=body.priority or "MEDIUM", notes=(body.notes or None),
        due_at=_parse_dt(body.dueAt), recurrence=(body.recurrence or "NONE").upper(),
        project_id=body.projectId, tags=(body.tags or "")[:500],
    )
    s.add(t)
    s.commit()
    s.refresh(t)
    return _todo_dict(t)


@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate, s: Session = Depends(db)):
    t = s.query(Todo).get(todo_id)
    if not t:
        raise HTTPException(status_code=404, detail="TODO não encontrado")
    data = body.model_dump(exclude_unset=True)
    if body.text is not None:
        t.text = body.text.strip()
    if "recurrence" in data:
        t.recurrence = (body.recurrence or "NONE").upper()
    if body.done is not None:
        from relay.db.models import advance_todo_recurrence
        if body.done and advance_todo_recurrence(t):
            pass  # recorrente: reagendado para a próxima ocorrência
        else:
            t.done = body.done
            t.completed_at = datetime.utcnow() if body.done else None
    if "priority" in data:
        t.priority = body.priority or "MEDIUM"
    if "notes" in data:
        t.notes = body.notes or None
    if "dueAt" in data:
        t.due_at = _parse_dt(body.dueAt)
        t.snoozed_until = None  # reagendou: limpa o adiamento
    if "projectId" in data:
        t.project_id = body.projectId
    if "tags" in data:
        t.tags = (body.tags or "")[:500]
    s.commit()
    s.refresh(t)
    return _todo_dict(t)


@app.post("/api/todos/{todo_id}/snooze")
def snooze_todo(todo_id: int, body: TodoSnooze, s: Session = Depends(db)):
    t = s.query(Todo).get(todo_id)
    if not t:
        raise HTTPException(status_code=404, detail="TODO não encontrado")
    from datetime import timedelta
    t.snoozed_until = datetime.now() + timedelta(minutes=max(1, body.minutes))
    s.commit()
    s.refresh(t)
    return _todo_dict(t)


@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int, s: Session = Depends(db)):
    t = s.query(Todo).get(todo_id)
    if not t:
        raise HTTPException(status_code=404, detail="TODO não encontrado")
    s.delete(t)
    s.commit()
    return {"ok": True}


# ============================= STUDY =======================================


@app.post("/api/study/plans")
def create_study_plan(body: StudyPlanCreate, s: Session = Depends(db)):
    import json
    p = StudyPlan(
        title=body.title, description=body.description,
        category=body.category or "LINGUAGEM",
        start_date=datetime.fromisoformat(body.startDate) if body.startDate else None,
        target_date=datetime.fromisoformat(body.targetDate) if body.targetDate else None,
        resources=json.dumps(body.resources) if body.resources else None,
    )
    s.add(p)
    s.commit()
    s.refresh(p)
    return _plan_dict(p)


@app.get("/api/study/plans")
def list_study_plans(
    status: Optional[str] = None,
    category: Optional[str] = None,
    s: Session = Depends(db),
):
    q = s.query(StudyPlan)
    if status:
        q = q.filter(StudyPlan.status == status)
    if category:
        q = q.filter(StudyPlan.category == category)
    plans = q.order_by(StudyPlan.updated_at.desc()).all()
    return [_plan_dict(p) for p in plans]


@app.get("/api/study/plans/{plan_id}")
def get_study_plan(plan_id: int, s: Session = Depends(db)):
    p = s.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not p:
        raise HTTPException(404, "Plano nao encontrado")
    return _plan_dict(p, include_topics=True)


@app.patch("/api/study/plans/{plan_id}")
def update_study_plan(plan_id: int, body: StudyPlanUpdate, s: Session = Depends(db)):
    import json
    p = s.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not p:
        raise HTTPException(404, "Plano nao encontrado")
    data = body.model_dump(exclude_unset=True)
    for field in ["title", "description", "category", "status"]:
        if field in data:
            setattr(p, field, data[field])
    if "startDate" in data:
        p.start_date = datetime.fromisoformat(data["startDate"]) if data["startDate"] else None
    if "targetDate" in data:
        p.target_date = datetime.fromisoformat(data["targetDate"]) if data["targetDate"] else None
    if "resources" in data:
        p.resources = json.dumps(data["resources"]) if data["resources"] else None
    p.updated_at = datetime.utcnow()
    s.commit()
    s.refresh(p)
    return _plan_dict(p, include_topics=True)


@app.delete("/api/study/plans/{plan_id}")
def delete_study_plan(plan_id: int, s: Session = Depends(db)):
    p = s.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not p:
        raise HTTPException(404, "Plano nao encontrado")
    s.delete(p)
    s.commit()
    return {"ok": True}


# -- Topics ----------------------------------------------------------------

@app.get("/api/study/plans/{plan_id}/topics")
def list_study_topics(plan_id: int, s: Session = Depends(db)):
    topics = s.query(StudyTopic).filter(StudyTopic.plan_id == plan_id, StudyTopic.parent_id.is_(None))\
        .order_by(StudyTopic.sort_order).all()
    return [_topic_dict(t) for t in topics]


@app.post("/api/study/plans/{plan_id}/topics")
def create_study_topic(plan_id: int, body: StudyTopicCreate, s: Session = Depends(db)):
    import json
    p = s.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not p:
        raise HTTPException(404, "Plano nao encontrado")
    max_order = s.query(StudyTopic).filter(StudyTopic.plan_id == plan_id, StudyTopic.parent_id.is_(None))\
        .with_entities(StudyTopic.sort_order).order_by(StudyTopic.sort_order.desc()).first()
    t = StudyTopic(
        plan_id=plan_id, parent_id=body.parentId, title=body.title,
        description=body.description, sort_order=(max_order[0] + 1) if max_order else 0,
        weight=body.weight or 1.0, estimate_hours=body.estimateHours,
        resources=json.dumps(body.resources) if body.resources else None,
    )
    s.add(t)
    s.commit()
    s.refresh(t)
    return _topic_dict(t)


@app.patch("/api/study/topics/{topic_id}")
def update_study_topic(topic_id: int, body: StudyTopicUpdate, s: Session = Depends(db)):
    import json
    t = s.query(StudyTopic).filter(StudyTopic.id == topic_id).first()
    if not t:
        raise HTTPException(404, "Topico nao encontrado")
    data = body.model_dump(exclude_unset=True)
    for field in ["title", "description", "status", "weight", "estimateHours", "loggedHours", "notes"]:
        if field in data:
            setattr(t, field, data[field])
    if "estimateHours" in data:
        t.estimate_hours = data["estimateHours"]
    if "loggedHours" in data:
        t.logged_hours = data["loggedHours"]
    if "resources" in data:
        t.resources = json.dumps(data["resources"]) if data["resources"] else None
    t.updated_at = datetime.utcnow()
    s.commit()
    s.refresh(t)
    return _topic_dict(t)


@app.delete("/api/study/topics/{topic_id}")
def delete_study_topic(topic_id: int, s: Session = Depends(db)):
    t = s.query(StudyTopic).filter(StudyTopic.id == topic_id).first()
    if not t:
        raise HTTPException(404, "Topico nao encontrado")
    s.delete(t)
    s.commit()
    return {"ok": True}


@app.patch("/api/study/plans/{plan_id}/topics/reorder")
def reorder_study_topics(plan_id: int, body: ReorderTopicsBody, s: Session = Depends(db)):
    for idx, tid in enumerate(body.ids):
        t = s.query(StudyTopic).filter(StudyTopic.id == tid, StudyTopic.plan_id == plan_id).first()
        if t:
            t.sort_order = idx
    s.commit()
    return {"ok": True}


# -- Sessions --------------------------------------------------------------

@app.post("/api/study/sessions")
def create_study_session(body: StudySessionCreate, s: Session = Depends(db)):
    t = s.query(StudyTopic).filter(StudyTopic.id == body.topicId).first()
    if not t:
        raise HTTPException(404, "Topico nao encontrado")
    sess = StudySession(
        plan_id=t.plan_id, topic_id=body.topicId,
        started_at=datetime.fromisoformat(body.startedAt),
        ended_at=datetime.fromisoformat(body.endedAt) if body.endedAt else None,
        duration_min=body.durationMin, notes=body.notes, confidence=body.confidence,
    )
    s.add(sess)
    if body.durationMin and body.durationMin > 0:
        t.logged_hours = (t.logged_hours or 0) + body.durationMin / 60
    s.commit()
    s.refresh(sess)
    return _session_dict(sess)


@app.get("/api/study/sessions")
def list_study_sessions(
    planId: Optional[int] = None,
    date: Optional[str] = None,
    s: Session = Depends(db),
):
    q = s.query(StudySession)
    if planId:
        q = q.filter(StudySession.plan_id == planId)
    if date:
        day_start = datetime.fromisoformat(f"{date}T00:00:00")
        day_end = datetime.fromisoformat(f"{date}T23:59:59")
        q = q.filter(StudySession.started_at >= day_start, StudySession.started_at <= day_end)
    sessions = q.order_by(StudySession.started_at.desc()).all()
    return [_session_dict(ss) for ss in sessions]


@app.get("/api/study/plans/{plan_id}/sessions")
def list_plan_sessions(plan_id: int, s: Session = Depends(db)):
    sessions = s.query(StudySession).filter(StudySession.plan_id == plan_id)\
        .order_by(StudySession.started_at.desc()).all()
    return [_session_dict(ss) for ss in sessions]


@app.get("/api/study/stats")
def get_study_stats(s: Session = Depends(db)):
    plans = s.query(StudyPlan).all()
    sessions = s.query(StudySession).all()
    total_hours = round(sum(ss.duration_min or 0 for ss in sessions) / 60, 1)
    active_plans = len([p for p in plans if p.status == "EM_ANDAMENTO"])
    return {"totalHours": total_hours, "activePlans": active_plans, "totalPlans": len(plans)}


# -- Skills -----------------------------------------------------------------


@app.get("/api/skills")
def list_skills():
    from relay.skills.catalog import SKILLS, CATEGORIES

    return {
        "skills": [
            {
                "id": s["id"],
                "name": s["name"],
                "category": s["category"],
                "categoryLabel": CATEGORIES.get(s["category"], s["category"]),
                "description": s["description"],
                "tags": s.get("tags", []),
                "filename": s["filename"],
            }
            for s in SKILLS
        ],
        "categories": CATEGORIES,
    }


@app.get("/api/skills/{skill_id}")
def get_skill(skill_id: str):
    from relay.skills.catalog import SKILLS

    skill = next((s for s in SKILLS if s["id"] == skill_id), None)
    if not skill:
        raise HTTPException(404, "Skill not found")
    return {
        "id": skill["id"],
        "name": skill["name"],
        "category": skill["category"],
        "description": skill["description"],
        "tags": skill.get("tags", []),
        "filename": skill["filename"],
        "content": skill["content"],
    }


# ---------------------------------------------------------------------------
# Daily Notes
# ---------------------------------------------------------------------------

DAILY_NOTE_TEMPLATE = """\
## Foco do Dia
- [ ] ...

## Bloqueios
- ...

## Notas
- ...
"""


class DailyNoteUpdate(BaseModel):
    body: str | None = None


class ReportAppend(BaseModel):
    content: str


def _build_daily_report(s: Session, day_str: str) -> str:
    day_start = datetime.fromisoformat(f"{day_str}T00:00:00")
    day_end = datetime.fromisoformat(f"{day_str}T23:59:59")

    activities = (
        s.query(ActivityLog)
        .filter(ActivityLog.created_at >= day_start, ActivityLog.created_at <= day_end)
        .order_by(ActivityLog.created_at)
        .all()
    )

    task_ids = set()
    for a in activities:
        if a.entity_type == "task":
            task_ids.add(a.entity_id)

    comments = (
        s.query(Comment)
        .filter(Comment.created_at >= day_start, Comment.created_at <= day_end)
        .all()
    )
    for c in comments:
        task_ids.add(c.task_id)

    tasks = s.query(Task).filter(Task.id.in_(task_ids)).all() if task_ids else []

    note = s.query(DailyNote).filter(DailyNote.date == day_str).first()
    user_notes = note.body if note else ""

    lines = [f"# Relatório Diário — {day_str}", ""]

    # --- Conteúdo estruturado da nota do dia (se existe) ---
    if user_notes.strip():
        lines.append(user_notes.strip())
        lines.append("")

    # --- Tarefas trabalhadas (do board) ---
    if tasks:
        lines.append("## Tarefas do Board")
        lines.append("")
        for task in tasks:
            ttype = task.type or "FEATURE"
            lines.append(f"- **{task.code}** — {task.title} [{ttype}] (_{task.status}_)")
        lines.append("")

    # --- Timeline de atividades ---
    if activities:
        lines.append("## Timeline de Atividades")
        lines.append("")
        for a in activities:
            time_str = a.created_at.strftime("%H:%M") if a.created_at else ""
            lines.append(f"- `{time_str}` {a.action}: {a.detail or ''}")
        lines.append("")

    # --- Code reviews ---
    reviews = [c for c in comments if c.type == "CODE_REVIEW"]
    if reviews:
        lines.append("## Code Reviews")
        lines.append("")
        for r in reviews:
            task = s.query(Task).get(r.task_id)
            code = task.code if task else f"#{r.task_id}"
            lines.append(f"### {code}")
            lines.append(r.body or "")
            lines.append("")

    # --- Resumo automático ---
    lines.append("## Resumo")
    lines.append("")
    lines.append(f"- **Tarefas tocadas**: {len(tasks)}")
    lines.append(f"- **Atividades registradas**: {len(activities)}")
    lines.append(f"- **Code reviews**: {len(reviews)}")
    done_today = sum(
        1 for task in tasks
        if s.query(BoardColumn).get(task.column_id)
        and s.query(BoardColumn).get(task.column_id).is_done
    )
    if done_today:
        lines.append(f"- **Concluídas hoje**: {done_today}")

    return "\n".join(lines)


@app.get("/api/daily/template")
def get_daily_template():
    """Retorna o template padrao para notas diarias."""
    return {"template": DAILY_NOTE_TEMPLATE}


@app.get("/api/daily/{date}")
def get_daily_note(date: str):
    """Retorna a nota diaria de uma data (YYYY-MM-DD)."""
    s = get_session()
    try:
        note = s.query(DailyNote).filter(DailyNote.date == date).first()
        if not note:
            return {"date": date, "body": "", "report": "", "exists": False}
        return {
            "date": note.date,
            "body": note.body or "",
            "report": note.report or "",
            "exists": True,
            "createdAt": note.created_at.isoformat() if note.created_at else None,
            "updatedAt": note.updated_at.isoformat() if note.updated_at else None,
        }
    finally:
        s.close()


@app.put("/api/daily/{date}")
def save_daily_note(date: str, payload: DailyNoteUpdate):
    """Salva ou atualiza o corpo da nota diaria."""
    s = get_session()
    try:
        note = s.query(DailyNote).filter(DailyNote.date == date).first()
        if note:
            if payload.body is not None:
                note.body = payload.body
            note.updated_at = datetime.utcnow()
        else:
            note = DailyNote(date=date, body=payload.body or "")
            s.add(note)
        s.commit()
        return {"date": note.date, "body": note.body, "report": note.report or ""}
    finally:
        s.close()


@app.post("/api/daily/{date}/report")
def generate_daily_report(date: str):
    """Gera o relatorio base do dia com atividades e notas. Salva no banco."""
    s = get_session()
    try:
        report = _build_daily_report(s, date)

        note = s.query(DailyNote).filter(DailyNote.date == date).first()
        if note:
            note.report = report
            note.updated_at = datetime.utcnow()
        else:
            note = DailyNote(date=date, body="", report=report)
            s.add(note)
        s.commit()
        return {"date": date, "report": report}
    finally:
        s.close()


@app.patch("/api/daily/{date}/report")
def append_to_daily_report(date: str, payload: ReportAppend):
    """Adiciona conteudo ao relatorio existente, preservando o original no inicio.

    Uso principal: agente de IA adiciona resumos ou analises ao relatorio
    que o usuario ja criou. O conteudo original permanece intacto no topo,
    e o novo conteudo e adicionado ao final com um separador.
    """
    s = get_session()
    try:
        note = s.query(DailyNote).filter(DailyNote.date == date).first()

        if not note:
            note = DailyNote(date=date, body="")
            s.add(note)

        existing = (note.report or "").rstrip()
        addition = payload.content.strip()

        if existing:
            note.report = f"{existing}\n\n---\n\n{addition}\n"
        else:
            note.report = f"{addition}\n"

        note.updated_at = datetime.utcnow()
        s.commit()
        return {"date": date, "report": note.report}
    finally:
        s.close()


@app.get("/api/daily/{date}/activity")
def get_daily_activity(date: str):
    """Lista tarefas que tiveram atividade em uma data."""
    s = get_session()
    try:
        day_start = datetime.fromisoformat(f"{date}T00:00:00")
        day_end = datetime.fromisoformat(f"{date}T23:59:59")

        activities = (
            s.query(ActivityLog)
            .filter(ActivityLog.created_at >= day_start, ActivityLog.created_at <= day_end)
            .order_by(ActivityLog.created_at.desc())
            .all()
        )

        task_ids = set()
        for a in activities:
            if a.entity_type == "task":
                task_ids.add(a.entity_id)

        comments = (
            s.query(Comment)
            .filter(Comment.created_at >= day_start, Comment.created_at <= day_end)
            .all()
        )
        for c in comments:
            task_ids.add(c.task_id)

        tasks = s.query(Task).filter(Task.id.in_(task_ids)).all() if task_ids else []

        return {
            "date": date,
            "tasks": [
                {
                    "code": t.code,
                    "title": t.title,
                    "status": t.status,
                    "type": t.type or "FEATURE",
                    "requiresHuman": t.requires_human,
                }
                for t in tasks
            ],
            "activityCount": len(activities),
            "commentCount": len(comments),
        }
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------


@app.get("/api/workspaces")
def list_workspaces_ep():
    from relay.config import get_active_workspace_id, list_workspaces
    return {"active": get_active_workspace_id(), "workspaces": list_workspaces()}


@app.post("/api/workspaces/active")
def set_active_workspace_ep(body: dict):
    from relay.config import get_workspace_db_path, set_active_workspace
    from relay.db.models import switch_db
    ws_id = body.get("id")
    if not ws_id:
        raise HTTPException(status_code=400, detail="id é obrigatório")
    set_active_workspace(ws_id)
    switch_db(get_workspace_db_path(ws_id))
    return {"ok": True, "active": ws_id}


@app.post("/api/workspaces")
def create_workspace_ep(body: dict):
    from relay.config import create_workspace as cfg_create
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name é obrigatório")
    icon = (body.get("icon") or "W").strip()[:4] or "W"
    ws = cfg_create(name, icon=icon)
    return ws


# ---------------------------------------------------------------------------
# Assistente (agente interno)
# ---------------------------------------------------------------------------


class AssistantChat(BaseModel):
    messages: list[dict]


@app.post("/api/assistant/chat")
def assistant_chat(body: AssistantChat):
    from relay.ai.agent import run_agent
    try:
        reply = run_agent(body.messages)
        return {"reply": reply}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


class StudyAssistBody(BaseModel):
    action: str          # explain|exercises|quiz|flashcards|ask|roadmap_questions|suggest_topics
    topic: str = ""
    plan: str = ""
    question: str = ""
    existing: list[str] = []
    context: str = ""    # respostas/contexto do estudante (fluxo de roadmap)


@app.post("/api/study/assistant")
def study_assistant(body: StudyAssistBody):
    """Assistente de estudo sob demanda. Retorna {action, result}: result é
    markdown (texto), lista de perguntas (roadmap_questions) ou lista de
    {title, estimate_hours} (suggest_topics)."""
    from relay.study.assistant import run_action
    try:
        result = run_action(
            body.action, topic=body.topic, plan=body.plan,
            question=body.question, existing=body.existing, context=body.context,
        )
        return {"action": body.action, "result": result}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/study/plans/with-files")
def create_study_plan_with_files(
    title: str = Form(...),
    category: str = Form("LIVRO"),
    description: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    s: Session = Depends(db),
):
    """Cria um plano de estudo usando os CAMPOS (título/categoria/descrição) e os
    ARQUIVOS anexados como contexto. Extrai o texto de todos os arquivos, gera os
    tópicos com IA e persiste. O plano é criado mesmo se a geração de IA falhar."""
    from relay.study.assistant import topics_from_material
    from relay.study.ingest import extract_text

    chunks: list[str] = []
    used_files: list[str] = []
    for f in files or []:
        try:
            data = f.file.read()
        except Exception:  # noqa: BLE001
            data = b""
        if not data:
            continue
        text = extract_text(data, f.filename or "")
        if text.strip():
            chunks.append(f"### {f.filename}\n{text}")
            used_files.append(f.filename)
    material = "\n\n".join(chunks)

    plan = StudyPlan(title=title.strip(), category=category or "LIVRO", description=description.strip() or None)
    s.add(plan)
    s.flush()

    ai_error = None
    try:
        topics = topics_from_material(
            material, title=title.strip(), category=category, description=description.strip(),
        )
    except Exception as e:  # noqa: BLE001
        topics, ai_error = [], str(e)

    for i, tp in enumerate(topics):
        hours = tp.get("estimate_hours")
        try:
            hours = float(hours) if hours else None
        except (TypeError, ValueError):
            hours = None
        s.add(StudyTopic(
            plan_id=plan.id, title=tp["title"], sort_order=i, weight=1.0, estimate_hours=hours,
        ))
    s.commit()
    s.refresh(plan)
    return {**_plan_dict(plan, include_topics=True), "usedFiles": used_files, "aiError": ai_error}


# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseModel):
    language: Optional[str] = None
    activeProviderId: Optional[str] = None
    aiProviders: Optional[list] = None
    whisperModel: Optional[str] = None
    meetingContext: Optional[dict] = None


def _settings_dict() -> dict:
    from relay.config import (
        get_active_ai_provider,
        get_language,
        list_ai_providers,
        load_config,
    )
    from relay.config import get_meeting_context_limits

    cron = load_config().get("settings", {}).get("transcricoes", {})
    active = get_active_ai_provider()
    return {
        "language": get_language(),
        "aiProviders": list_ai_providers(),
        "activeProviderId": active["id"] if active else None,
        "whisperModel": cron.get("whisper_model", "small"),
        # quanto do projeto entra no contexto do copiloto de reunião
        "meetingContext": get_meeting_context_limits(),
    }


@app.get("/api/settings")
def get_settings():
    return _settings_dict()


@app.put("/api/settings")
def put_settings(body: SettingsUpdate):
    from relay.config import (
        load_config,
        save_ai_providers,
        save_config,
        set_active_ai_provider,
        set_language,
    )
    if body.language:
        set_language(body.language)
    if body.aiProviders is not None:
        save_ai_providers(body.aiProviders, active_id=body.activeProviderId)
    elif body.activeProviderId:
        set_active_ai_provider(body.activeProviderId)
    if body.whisperModel:
        cfg = load_config()
        cfg.setdefault("settings", {}).setdefault("transcricoes", {})["whisper_model"] = body.whisperModel
        save_config(cfg)
    if body.meetingContext is not None:
        from relay.config import set_meeting_context_limits

        campos = ("cards", "overdue", "dailies", "deliveries")
        set_meeting_context_limits(**{
            k: body.meetingContext[k] for k in campos if k in body.meetingContext
        })
    return _settings_dict()


# ---------------------------------------------------------------------------
# Snippets & prompt library
# ---------------------------------------------------------------------------


def _snippet_dict(s: Snippet) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "content": s.content or "",
        "kind": s.kind or "SNIPPET",
        "language": s.language or "",
        "tags": s.tags or "",
        "projectId": s.project_id,
        "useCount": s.use_count or 0,
        "createdAt": s.created_at.isoformat() if s.created_at else None,
        "updatedAt": s.updated_at.isoformat() if s.updated_at else None,
    }


class SnippetCreate(BaseModel):
    title: str
    content: str = ""
    kind: str = "SNIPPET"
    language: str = ""
    tags: str = ""
    projectId: Optional[int] = None


class SnippetUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    kind: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[str] = None
    projectId: Optional[int] = None


@app.get("/api/snippets")
def list_snippets(kind: Optional[str] = None, q: Optional[str] = None,
                  projectId: Optional[int] = None, s: Session = Depends(db)):
    query = s.query(Snippet)
    if kind:
        query = query.filter(Snippet.kind == kind.upper())
    if projectId is not None:
        query = query.filter(Snippet.project_id == projectId)
    rows = query.order_by(Snippet.updated_at.desc()).all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in f"{r.title} {r.content} {r.tags} {r.language}".lower()]
    return [_snippet_dict(r) for r in rows]


@app.post("/api/snippets")
def create_snippet(body: SnippetCreate, s: Session = Depends(db)):
    row = Snippet(
        title=body.title.strip(), content=body.content or "",
        kind=(body.kind or "SNIPPET").upper(), language=body.language or "",
        tags=body.tags or "", project_id=body.projectId,
    )
    s.add(row)
    s.commit()
    s.refresh(row)
    return _snippet_dict(row)


@app.put("/api/snippets/{snippet_id}")
def update_snippet(snippet_id: int, body: SnippetUpdate, s: Session = Depends(db)):
    row = s.get(Snippet, snippet_id)
    if not row:
        raise HTTPException(status_code=404, detail="Snippet não encontrado")
    if body.title is not None:
        row.title = body.title.strip()
    if body.content is not None:
        row.content = body.content
    if body.kind is not None:
        row.kind = body.kind.upper()
    if body.language is not None:
        row.language = body.language
    if body.tags is not None:
        row.tags = body.tags
    if body.projectId is not None:
        row.project_id = body.projectId
    s.commit()
    s.refresh(row)
    return _snippet_dict(row)


@app.post("/api/snippets/{snippet_id}/use")
def use_snippet(snippet_id: int, s: Session = Depends(db)):
    row = s.get(Snippet, snippet_id)
    if not row:
        raise HTTPException(status_code=404, detail="Snippet não encontrado")
    row.use_count = (row.use_count or 0) + 1
    s.commit()
    return {"ok": True, "useCount": row.use_count}


@app.delete("/api/snippets/{snippet_id}")
def delete_snippet(snippet_id: int, s: Session = Depends(db)):
    row = s.get(Snippet, snippet_id)
    if not row:
        raise HTTPException(status_code=404, detail="Snippet não encontrado")
    s.delete(row)
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Runbooks / comandos de projeto
# ---------------------------------------------------------------------------


def _runbook_dict(r: Runbook) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "command": r.command or "",
        "description": r.description or "",
        "category": r.category or "",
        "projectId": r.project_id,
        "useCount": r.use_count or 0,
        "sortOrder": r.sort_order or 0,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
        "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
    }


class RunbookCreate(BaseModel):
    title: str
    command: str = ""
    description: str = ""
    category: str = ""
    projectId: Optional[int] = None


class RunbookUpdate(BaseModel):
    title: Optional[str] = None
    command: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    projectId: Optional[int] = None


@app.get("/api/runbooks")
def list_runbooks(q: Optional[str] = None, projectId: Optional[int] = None,
                  s: Session = Depends(db)):
    query = s.query(Runbook)
    if projectId is not None:
        query = query.filter(Runbook.project_id == projectId)
    rows = query.order_by(Runbook.sort_order.asc(), Runbook.updated_at.desc()).all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in f"{r.title} {r.command} {r.description} {r.category}".lower()]
    return [_runbook_dict(r) for r in rows]


@app.post("/api/runbooks")
def create_runbook(body: RunbookCreate, s: Session = Depends(db)):
    row = Runbook(
        title=body.title.strip(), command=body.command or "",
        description=body.description or "", category=body.category or "",
        project_id=body.projectId,
    )
    s.add(row)
    s.commit()
    s.refresh(row)
    return _runbook_dict(row)


@app.put("/api/runbooks/{runbook_id}")
def update_runbook(runbook_id: int, body: RunbookUpdate, s: Session = Depends(db)):
    row = s.get(Runbook, runbook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Runbook não encontrado")
    if body.title is not None:
        row.title = body.title.strip()
    if body.command is not None:
        row.command = body.command
    if body.description is not None:
        row.description = body.description
    if body.category is not None:
        row.category = body.category
    if body.projectId is not None:
        row.project_id = body.projectId
    s.commit()
    s.refresh(row)
    return _runbook_dict(row)


@app.post("/api/runbooks/{runbook_id}/use")
def use_runbook(runbook_id: int, s: Session = Depends(db)):
    row = s.get(Runbook, runbook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Runbook não encontrado")
    row.use_count = (row.use_count or 0) + 1
    s.commit()
    return {"ok": True, "useCount": row.use_count}


@app.delete("/api/runbooks/{runbook_id}")
def delete_runbook(runbook_id: int, s: Session = Depends(db)):
    row = s.get(Runbook, runbook_id)
    if not row:
        raise HTTPException(status_code=404, detail="Runbook não encontrado")
    s.delete(row)
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Testador de API (mini-Postman): requests salvos + execução + histórico
# ---------------------------------------------------------------------------


def _api_request_dict(r: ApiRequest) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "method": r.method or "GET",
        "url": r.url or "",
        "headers": r.headers or "",
        "body": r.body or "",
        "projectId": r.project_id,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
        "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
    }


def _api_call_dict(c: ApiCall) -> dict:
    return {
        "id": c.id,
        "requestId": c.request_id,
        "method": c.method,
        "url": c.url,
        "status": c.status,
        "durationMs": c.duration_ms,
        "ok": c.ok,
        "error": c.error or "",
        "responseSnippet": c.response_snippet or "",
        "createdAt": c.created_at.isoformat() if c.created_at else None,
    }


class ApiRequestBody(BaseModel):
    name: str
    method: str = "GET"
    url: str = ""
    headers: str = ""
    body: str = ""
    projectId: Optional[int] = None


class ApiRunBody(BaseModel):
    method: str = "GET"
    url: str
    headers: str = ""
    body: str = ""
    requestId: Optional[int] = None
    save: bool = True


@app.get("/api/http-requests")
def list_api_requests(projectId: Optional[int] = None, s: Session = Depends(db)):
    query = s.query(ApiRequest)
    if projectId is not None:
        query = query.filter(ApiRequest.project_id == projectId)
    rows = query.order_by(ApiRequest.updated_at.desc()).all()
    return [_api_request_dict(r) for r in rows]


@app.post("/api/http-requests")
def create_api_request(body: ApiRequestBody, s: Session = Depends(db)):
    row = ApiRequest(
        name=body.name.strip() or "Sem nome", method=(body.method or "GET").upper(),
        url=body.url or "", headers=body.headers or "", body=body.body or "",
        project_id=body.projectId,
    )
    s.add(row)
    s.commit()
    s.refresh(row)
    return _api_request_dict(row)


@app.put("/api/http-requests/{req_id}")
def update_api_request(req_id: int, body: ApiRequestBody, s: Session = Depends(db)):
    row = s.get(ApiRequest, req_id)
    if not row:
        raise HTTPException(status_code=404, detail="Request não encontrado")
    row.name = body.name.strip() or row.name
    row.method = (body.method or "GET").upper()
    row.url = body.url or ""
    row.headers = body.headers or ""
    row.body = body.body or ""
    if body.projectId is not None:
        row.project_id = body.projectId
    s.commit()
    s.refresh(row)
    return _api_request_dict(row)


@app.delete("/api/http-requests/{req_id}")
def delete_api_request(req_id: int, s: Session = Depends(db)):
    row = s.get(ApiRequest, req_id)
    if not row:
        raise HTTPException(status_code=404, detail="Request não encontrado")
    s.delete(row)
    s.commit()
    return {"ok": True}


@app.get("/api/http-requests/history")
def api_call_history(requestId: Optional[int] = None, limit: int = 30,
                     s: Session = Depends(db)):
    query = s.query(ApiCall)
    if requestId is not None:
        query = query.filter(ApiCall.request_id == requestId)
    rows = query.order_by(ApiCall.created_at.desc()).limit(max(1, min(limit, 200))).all()
    return [_api_call_dict(c) for c in rows]


def _run_http_request(method: str, url: str, headers_raw: str, body: str) -> dict:
    """Executa um request HTTP com a stdlib. Retorna dados p/ histórico + corpo."""
    import json as _json
    import time
    import urllib.error
    import urllib.request

    method = (method or "GET").upper()
    hdrs = {}
    if headers_raw and headers_raw.strip():
        try:
            parsed = _json.loads(headers_raw)
            if isinstance(parsed, dict):
                hdrs = {str(k): str(v) for k, v in parsed.items()}
        except (ValueError, TypeError):
            # formato "Chave: valor" por linha
            for line in headers_raw.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    hdrs[k.strip()] = v.strip()

    data = body.encode("utf-8") if body and method in ("POST", "PUT", "PATCH", "DELETE") else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            duration = int((time.monotonic() - start) * 1000)
            text = raw.decode("utf-8", errors="replace")
            return {
                "ok": True, "status": resp.status, "durationMs": duration,
                "error": "", "body": text,
                "headers": dict(resp.headers.items()),
            }
    except urllib.error.HTTPError as e:
        duration = int((time.monotonic() - start) * 1000)
        raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        return {"ok": False, "status": e.code, "durationMs": duration,
                "error": f"HTTP {e.code}: {e.reason}", "body": raw, "headers": {}}
    except Exception as e:  # noqa: BLE001  (timeout, DNS, conexão, URL inválida)
        duration = int((time.monotonic() - start) * 1000)
        return {"ok": False, "status": None, "durationMs": duration,
                "error": str(e), "body": "", "headers": {}}


@app.post("/api/http-requests/run")
def run_api_request(body: ApiRunBody, s: Session = Depends(db)):
    if not body.url.strip():
        raise HTTPException(status_code=400, detail="URL vazia")
    result = _run_http_request(body.method, body.url.strip(), body.headers, body.body)
    if body.save:
        call = ApiCall(
            request_id=body.requestId, method=(body.method or "GET").upper(),
            url=body.url.strip(), status=result["status"],
            duration_ms=result["durationMs"], ok=result["ok"],
            error=result["error"], response_snippet=(result["body"] or "")[:2000],
        )
        s.add(call)
        s.commit()
    return result


# ---------------------------------------------------------------------------
# Digest proativo (standup automático)
# ---------------------------------------------------------------------------


def _digest_context(s: Session, days: int) -> str:
    from datetime import datetime as _dt, timedelta
    since = _dt.now() - timedelta(days=days)

    active = [t for t in s.query(Task).filter(Task.deleted_at.is_(None)).all()
              if t.archived_at is None]
    done = [t for t in active if t.column and t.column.is_done
            and (t.done_at is None or t.done_at >= since)]
    doing = [t for t in active if t.column and not t.column.is_done
             and t.column.order and t.column.order > 0]

    recent_activity = (
        s.query(ActivityLog)
        .filter(ActivityLog.created_at >= since)
        .order_by(ActivityLog.created_at.desc())
        .limit(30).all()
    )
    notes = (
        s.query(DailyNote)
        .order_by(DailyNote.date.desc())
        .limit(3).all()
    )

    lines = [f"Período: últimos {days} dia(s)."]
    lines.append(f"Tarefas concluídas ({len(done)}):")
    lines += [f"  - [{t.type}] {t.title}" for t in done[:20]] or ["  (nenhuma)"]
    lines.append(f"Tarefas em andamento ({len(doing)}):")
    lines += [f"  - [{t.type}] {t.title} (coluna: {t.column.name if t.column else '-'})"
              for t in doing[:20]] or ["  (nenhuma)"]
    if recent_activity:
        lines.append("Atividade recente:")
        lines += [f"  - {a.action}: {a.detail or ''}" for a in recent_activity[:15]]
    for n in notes:
        if n.body and n.body.strip():
            lines.append(f"Nota do dia {n.date}:\n{n.body.strip()[:600]}")
    return "\n".join(lines)


@app.get("/api/digest")
def get_digest(days: int = 1, s: Session = Depends(db)):
    from relay.digest import generate_digest
    context = _digest_context(s, max(1, min(days, 30)))
    try:
        result = generate_digest(context)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.get("/api/coach/tip")
def get_coach_tip(s: Session = Depends(db)):
    """Uma dica proativa curta a partir do estado atual do trabalho.

    Retorna {"tip": ""} quando não há provedor de IA configurado.
    """
    from relay.coach import build_context, generate_tip
    from relay.config import get_active_ai_provider

    if not get_active_ai_provider():
        return {"tip": "", "category": ""}
    try:
        return generate_tip(build_context(s))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


class CoachConfigUpdate(BaseModel):
    enabled: bool | None = None
    interval_min: int | None = None


@app.get("/api/coach/config")
def get_coach_cfg():
    from relay.config import get_coach_config
    return get_coach_config()


@app.put("/api/coach/config")
def put_coach_cfg(body: CoachConfigUpdate):
    from relay.config import get_coach_config, set_coach_config
    set_coach_config(enabled=body.enabled, interval_min=body.interval_min)
    return get_coach_config()


# ---------------------------------------------------------------------------
# Time tracking / timesheet
# ---------------------------------------------------------------------------


def _timelog_dict(t: TimeLog) -> dict:
    return {
        "id": t.id,
        "taskId": t.task_id,
        "taskCode": t.task_code or "",
        "seconds": t.seconds or 0,
        "note": t.note or "",
        "startedAt": t.started_at.isoformat() if t.started_at else None,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
    }


class TimeLogBody(BaseModel):
    seconds: int
    taskCode: Optional[str] = None
    note: str = ""


@app.get("/api/timelogs")
def list_timelogs(limit: int = 50, s: Session = Depends(db)):
    from datetime import datetime as _dt, timedelta
    rows = (s.query(TimeLog).order_by(TimeLog.created_at.desc())
            .limit(max(1, min(limit, 200))).all())
    week_start = _dt.now() - timedelta(days=7)
    week_total = sum(
        (t.seconds or 0) for t in s.query(TimeLog)
        .filter(TimeLog.created_at >= week_start).all()
    )
    by_task = {}
    for t in s.query(TimeLog).filter(TimeLog.created_at >= week_start).all():
        key = t.task_code or "—"
        by_task[key] = by_task.get(key, 0) + (t.seconds or 0)
    return {
        "logs": [_timelog_dict(t) for t in rows],
        "weekSeconds": week_total,
        "weekByTask": [{"taskCode": k, "seconds": v} for k, v in
                       sorted(by_task.items(), key=lambda kv: -kv[1])],
    }


@app.post("/api/timelogs")
def create_timelog(body: TimeLogBody, s: Session = Depends(db)):
    from datetime import datetime as _dt
    if body.seconds <= 0:
        raise HTTPException(status_code=400, detail="Duração inválida")
    task_id = None
    task_code = (body.taskCode or "").strip()
    if task_code:
        try:
            task = _resolve_task(task_code, s)
            task_id = task.id
            task_code = f"{task.project.key}-{task.number}"
        except HTTPException:
            pass  # mantém o código digitado mesmo sem casar com tarefa
    row = TimeLog(task_id=task_id, task_code=task_code, seconds=body.seconds,
                  note=body.note or "", started_at=_dt.now())
    s.add(row)
    s.commit()
    s.refresh(row)
    return _timelog_dict(row)


@app.delete("/api/timelogs/{log_id}")
def delete_timelog(log_id: int, s: Session = Depends(db)):
    row = s.get(TimeLog, log_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    s.delete(row)
    s.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Tradutor
# ---------------------------------------------------------------------------


class TranslateBody(BaseModel):
    text: str
    source: str = "auto"
    target: str = "en"


@app.get("/api/translate/languages")
def translate_languages():
    from relay.translate import LANGUAGES
    return LANGUAGES


@app.post("/api/translate")
def translate_endpoint(body: TranslateBody):
    from relay.translate import translate
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Texto vazio")
    try:
        return translate(body.text, body.source, body.target)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Praticar inglês (conversação por IA)
# ---------------------------------------------------------------------------


class EnglishStartBody(BaseModel):
    level: str = "INTERMEDIATE"
    topic: str = ""


class EnglishMessageBody(BaseModel):
    level: str = "INTERMEDIATE"
    topic: str = ""
    history: list = []
    message: str


@app.post("/api/english/start")
def english_start(body: EnglishStartBody):
    from relay.english import start
    try:
        return start(body.level, body.topic)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/english/message")
def english_message(body: EnglishMessageBody):
    from relay.english import converse
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    try:
        return converse(body.level, body.topic, body.history, body.message)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Cockpit de Git/PR (somente leitura)
# ---------------------------------------------------------------------------


@app.get("/api/git/status")
def git_status_endpoint(path: str, prs: bool = False):
    from relay.gittools import git_status, gh_prs
    if not path.strip():
        raise HTTPException(status_code=400, detail="Caminho do repositório vazio")
    try:
        status = git_status(path.strip())
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if prs:
        status["prs"] = gh_prs(path.strip())
    return status


# ---------------------------------------------------------------------------
# Assistente de code review (diff → IA → comentário CODE_REVIEW)
# ---------------------------------------------------------------------------


class CodeReviewBody(BaseModel):
    path: str
    base: str = ""                 # ref/base do diff (vazio = working tree)
    taskCode: Optional[str] = None  # se informado, posta como comentário CODE_REVIEW


@app.post("/api/code/review")
def code_review(body: CodeReviewBody, s: Session = Depends(db)):
    from relay.codereview import get_git_diff, review_diff, review_to_markdown
    if not body.path.strip():
        raise HTTPException(status_code=400, detail="Caminho do repositório vazio")
    try:
        diff = get_git_diff(body.path.strip(), body.base)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        review = review_diff(diff)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))

    posted = None
    if body.taskCode:
        task = _resolve_task(body.taskCode, s)
        c = Comment(task_id=task.id, body=review_to_markdown(review), type="CODE_REVIEW")
        s.add(c)
        s.flush()
        _log(s, "task", task.id, "code_review", "Review de IA postado")
        s.commit()
        posted = {"taskId": task.id, "commentId": c.id}
    return {"review": review, "posted": posted}


# ---------------------------------------------------------------------------
# Intake / triagem de bugs (IA → tarefa BUG)
# ---------------------------------------------------------------------------


class BugTriageBody(BaseModel):
    text: str
    projectId: Optional[int] = None   # se informado (+ create), cria a tarefa
    create: bool = False


@app.post("/api/bugs/triage")
def bug_triage(body: BugTriageBody, s: Session = Depends(db)):
    from relay.triage import triage_bug, build_task_description
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Relato vazio")
    try:
        triage = triage_bug(body.text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))

    result = {"triage": triage, "task": None}
    if body.create and body.projectId:
        project = s.get(Project, body.projectId)
        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
        column = (
            s.query(BoardColumn)
            .filter(BoardColumn.project_id == project.id)
            .order_by(BoardColumn.order.asc())
            .first()
        )
        project.task_seq = (project.task_seq or 0) + 1
        task = Task(
            project_id=project.id,
            column_id=column.id if column else None,
            number=project.task_seq,
            title=triage["title"],
            description=build_task_description(body.text, triage),
            type="BUG",
            priority=triage["priority"],
            requires_human=True,
        )
        s.add(task)
        s.flush()
        _log(s, "task", task.id, "created", f"Bug triado {project.key}-{task.number}")
        s.commit()
        s.refresh(task)
        result["task"] = _task_full(task)
    return result


# ---------------------------------------------------------------------------
# Importar TODO/FIXME do código → tarefas
# ---------------------------------------------------------------------------


class ScanTodosBody(BaseModel):
    path: str
    markers: Optional[list] = None      # padrão: ["TODO", "FIXME", "HACK", "XXX"]
    maxResults: int = 500


class ImportTodosBody(BaseModel):
    projectId: int
    items: list                          # [{file, line, marker, text}]


def _scan_code_markers(root: str, markers: list, max_results: int) -> list:
    import os
    import re
    from pathlib import Path
    root_path = Path(root).expanduser()
    if not root_path.exists():
        raise HTTPException(status_code=400, detail="Caminho não encontrado")
    marker_re = re.compile(r"\b(" + "|".join(re.escape(m) for m in markers) + r")\b[:\s]+(.+)")
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv",
                 "dist", "build", ".next", ".mypy_cache", ".pytest_cache", "target"}
    text_ext = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb",
                ".c", ".h", ".cpp", ".hpp", ".cs", ".php", ".rs", ".kt", ".swift",
                ".sh", ".sql", ".vue", ".css", ".scss", ".html", ".md", ".yaml", ".yml"}
    out = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            if Path(fn).suffix.lower() not in text_ext:
                continue
            fpath = Path(dirpath) / fn
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if len(line) > 400:
                            continue
                        m = marker_re.search(line)
                        if m:
                            out.append({
                                "file": str(fpath.relative_to(root_path)),
                                "line": i,
                                "marker": m.group(1).upper(),
                                "text": m.group(2).strip()[:280],
                            })
                            if len(out) >= max_results:
                                return out
            except (OSError, UnicodeError):
                continue
    return out


@app.post("/api/code/scan-todos")
def scan_todos(body: ScanTodosBody):
    markers = [m.upper() for m in (body.markers or ["TODO", "FIXME", "HACK", "XXX"])]
    items = _scan_code_markers(body.path, markers, max(1, min(body.maxResults, 2000)))
    return {"count": len(items), "items": items}


@app.post("/api/code/import-todos")
def import_todos(body: ImportTodosBody, s: Session = Depends(db)):
    project = s.get(Project, body.projectId)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    column = (
        s.query(BoardColumn)
        .filter(BoardColumn.project_id == project.id)
        .order_by(BoardColumn.order.asc())
        .first()
    )
    created = 0
    for it in body.items:
        marker = (it.get("marker") or "TODO").upper()
        text = (it.get("text") or "").strip() or "(sem descrição)"
        title = f"[{marker}] {text}"[:255]
        loc = f"{it.get('file', '')}:{it.get('line', '')}"
        project.task_seq = (project.task_seq or 0) + 1
        task = Task(
            project_id=project.id,
            column_id=column.id if column else None,
            number=project.task_seq,
            title=title,
            description=f"Importado de `{loc}`",
            type="CHORE" if marker in ("TODO", "HACK", "XXX") else "BUG",
        )
        s.add(task)
        created += 1
    s.commit()
    _log(s, "project", project.id, "import_todos", f"{created} tarefa(s) de TODO/FIXME")
    return {"ok": True, "created": created}


# ---------------------------------------------------------------------------
# Time: report semanal por membro (números do board + anotação do líder)
# ---------------------------------------------------------------------------


class TeamNoteBody(BaseModel):
    member: str
    weekStart: str  # YYYY-MM-DD (normalizado para a segunda-feira)
    highlights: str = ""
    service: str = ""
    attention: str = ""
    nextStep: str = ""


@app.get("/api/projects/{project_id}/team/weekly")
def team_weekly(project_id: int, week: str | None = None, s: Session = Depends(db)):
    """Números da semana por membro, com as anotações de gestão já salvas.

    `week` pode ser qualquer dia da semana; o período é normalizado para
    segunda→domingo.
    """
    from datetime import date as _date

    from relay.team_report import compute_weekly

    project = s.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    try:
        ref = _date.fromisoformat(week) if week else None
    except ValueError:
        raise HTTPException(400, "week deve ser YYYY-MM-DD") from None
    return compute_weekly(s, project, ref)


@app.put("/api/projects/{project_id}/team/notes")
def save_team_note(project_id: int, body: TeamNoteBody, s: Session = Depends(db)):
    """Cria/atualiza a anotação de gestão de um membro em uma semana."""
    from datetime import date as _date

    from relay.db.models import TeamNote
    from relay.team_report import week_bounds

    project = s.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    try:
        semana = _date.fromisoformat(body.weekStart)
    except ValueError:
        raise HTTPException(400, "weekStart deve ser YYYY-MM-DD") from None
    semana = week_bounds(semana)[0]

    nome = (body.member or "").strip()
    if not nome:
        raise HTTPException(422, "member é obrigatório")

    nota = (
        s.query(TeamNote)
        .filter(
            TeamNote.project_id == project_id,
            TeamNote.member_name == nome,
            TeamNote.week_start == semana,
        )
        .first()
    )
    if nota is None:
        nota = TeamNote(project_id=project_id, member_name=nome, week_start=semana)
        s.add(nota)
    nota.highlights = body.highlights or ""
    nota.service = body.service or ""
    nota.attention = body.attention or ""
    nota.next_step = body.nextStep or ""
    s.commit()
    s.refresh(nota)
    return {
        "member": nota.member_name,
        "weekStart": nota.week_start.isoformat(),
        "highlights": nota.highlights or "",
        "service": nota.service or "",
        "attention": nota.attention or "",
        "nextStep": nota.next_step or "",
        "updatedAt": nota.updated_at.isoformat() if nota.updated_at else None,
    }


@app.get("/api/projects/{project_id}/team/weekly/export")
def team_weekly_export(
    project_id: int,
    week: str | None = None,
    anonymized: int = 0,
    s: Session = Depends(db),
):
    """Relatório semanal em markdown (nominal ou anonimizado)."""
    from datetime import date as _date

    from relay.team_report import compute_weekly, render_markdown

    project = s.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    try:
        ref = _date.fromisoformat(week) if week else None
    except ValueError:
        raise HTTPException(400, "week deve ser YYYY-MM-DD") from None

    dados = compute_weekly(s, project, ref)
    md = render_markdown(dados, anonimizado=bool(anonymized))
    sufixo = "-anonimizado" if anonymized else ""
    nome = f"acompanhamento-semanal{sufixo}-{dados['week']['start']}.md"
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


# ---------------------------------------------------------------------------
# Backup rápido do banco (cópia consistente via API do SQLite)
# ---------------------------------------------------------------------------


def _backup_dir() -> "Path":
    """Destino do backup: `settings.backup_dir` ou `~/relay-backups`."""
    from pathlib import Path

    from relay.config import load_config

    cfg = (load_config().get("settings") or {}).get("backup_dir")
    destino = Path(cfg).expanduser() if cfg else Path.home() / "relay-backups"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _db_atual() -> "Path":
    """Arquivo do banco em uso (o engine acompanha o workspace ativo)."""
    from pathlib import Path

    from relay.config import get_active_workspace_id, get_workspace_db_path
    from relay.db.models import get_engine

    url = get_engine().url
    if url.database and url.database != ":memory:":
        return Path(url.database)
    return Path(get_workspace_db_path(get_active_workspace_id()))


def _copia_sqlite(origem: "Path", destino: "Path") -> None:
    """Copia usando a API de backup do SQLite.

    Copiar o arquivo “na mão” pode pegar um estado no meio de uma escrita; a
    API do sqlite3 garante um instantâneo consistente (inclusive com WAL).
    """
    import sqlite3
    from pathlib import Path  # noqa: F401  (usado na assinatura)

    src = sqlite3.connect(f"file:{origem}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(destino))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


@app.post("/api/backup")
def create_backup(todos: bool = Query(False, alias="all")):
    """Backup do banco do workspace ativo (ou `?all=1` = todos os workspaces).

    Grava em `~/relay-backups/relay-<workspace>-<data-hora>.db`.
    """
    from datetime import datetime

    from relay.config import WORKSPACES_DIR, get_active_workspace_id

    destino_dir = _backup_dir()
    agora = datetime.now().strftime("%Y%m%d-%H%M%S")
    criados: list[dict] = []

    if todos:
        origens = [(pasta.parent.name, pasta) for pasta in sorted(WORKSPACES_DIR.glob("*/maestro.db"))]
    else:
        origem = _db_atual()
        if not origem.exists():
            raise HTTPException(404, "Banco de dados não encontrado")
        origens = [(get_active_workspace_id(), origem)]

    for workspace, origem in origens:
        alvo = destino_dir / f"relay-{workspace}-{agora}.db"
        try:
            _copia_sqlite(origem, alvo)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(500, f"Falha ao copiar {origem.name}: {exc}") from exc
        criados.append({
            "workspace": workspace,
            "file": alvo.name,
            "path": str(alvo),
            "bytes": alvo.stat().st_size,
        })

    return {
        "ok": True,
        "dir": str(destino_dir),
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "backups": criados,
    }


@app.get("/api/backup")
def list_backups(limit: int = 20):
    """Últimos backups gravados (mais recentes primeiro)."""
    from datetime import datetime

    destino_dir = _backup_dir()
    arquivos = sorted(
        destino_dir.glob("relay-*.db"), key=lambda p: p.stat().st_mtime, reverse=True
    )[: max(1, min(limit, 200))]
    return {
        "dir": str(destino_dir),
        "backups": [
            {
                "file": p.name,
                "path": str(p),
                "bytes": p.stat().st_size,
                "createdAt": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
            }
            for p in arquivos
        ],
    }


@app.get("/api/backup/{nome}")
def download_backup(nome: str):
    """Baixa um backup pelo nome (o arquivo precisa estar na pasta de backup)."""
    from pathlib import Path

    from fastapi.responses import FileResponse

    destino_dir = _backup_dir().resolve()
    alvo = (destino_dir / nome).resolve()
    # só serve arquivo que está de fato dentro da pasta e com nome de backup
    if alvo.parent != destino_dir or not alvo.name.startswith("relay-") or alvo.suffix != ".db":
        raise HTTPException(404, "Backup not found")
    if not alvo.exists():
        raise HTTPException(404, "Backup not found")
    return FileResponse(str(alvo), media_type="application/octet-stream", filename=alvo.name)


# ---------------------------------------------------------------------------
# Reuniões (recordings) — mesmas gravações do app desktop
# ---------------------------------------------------------------------------


class RecordingUpdate(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    transcript: Optional[str] = None
    markdown: Optional[str] = None
    tags: Optional[list[str]] = None
    kind: Optional[str] = None
    summaryJson: Optional[str] = None
    liveState: Optional[dict] = None


class ArchiveRecordingBody(BaseModel):
    archived: bool = True


class AnalyzeRecordingBody(BaseModel):
    projectId: Optional[int] = None
    save: bool = False


def _recording_base(r: Recording) -> dict:
    from pathlib import Path

    audio = (r.audio_path or "").strip()
    return {
        "id": r.id,
        "kind": r.kind or "meeting",
        "title": r.title or "",
        "topic": r.topic or "",
        "duration": r.duration or 0.0,
        "language": r.language or "",
        "tags": _recording_tags(r.tags),
        "hasAudio": bool(audio and Path(audio).exists()),
        "hasSummary": bool((r.markdown or "").strip() or (r.summary_json or "").strip()),
        "hasTranscript": bool((r.transcript or "").strip()),
        "preview": (r.transcript or r.markdown or "").strip()[:240],
        "createdAt": r.created_at.isoformat() if r.created_at else None,
        "archivedAt": r.archived_at.isoformat() if r.archived_at else None,
    }


def _recording_full(r: Recording) -> dict:
    from relay.meetings_export import parse_json, sections

    d = _recording_base(r)
    d.update({
        "transcript": r.transcript or "",
        "markdown": r.markdown or "",
        "summaryJson": r.summary_json or "",
        "liveState": parse_json(r.live_state_json, {}),
        "sections": sections({"live_state": r.live_state_json}),
    })
    return d


def _recording_tags(raw: str | None) -> list[str]:
    from relay.meetings_export import parse_json

    valor = parse_json(raw, [])
    return [str(t) for t in valor] if isinstance(valor, list) else []


@app.get("/api/recordings")
def list_recordings(
    kind: str | None = None,
    archived: str = "hide",
    q: str | None = None,
    limit: int = 200,
    s: Session = Depends(db),
):
    """Reuniões/estudos do workspace ativo.

    `archived`: `hide` (padrão), `only` ou `all`.
    `q`: busca no título, tópico e transcrição.
    """
    query = s.query(Recording)
    if kind:
        query = query.filter(Recording.kind == kind)
    if archived == "hide":
        query = query.filter(Recording.archived_at == None)  # noqa: E711
    elif archived == "only":
        query = query.filter(Recording.archived_at != None)  # noqa: E711
    if q and q.strip():
        alvo = f"%{q.strip().lower()}%"
        query = query.filter(
            func.lower(Recording.title).like(alvo)
            | func.lower(Recording.topic).like(alvo)
            | func.lower(Recording.transcript).like(alvo)
        )
    linhas = (
        query.order_by(Recording.sort_order, Recording.created_at.desc())
        .limit(max(1, min(limit, 1000)))
        .all()
    )
    return [_recording_base(r) for r in linhas]


@app.get("/api/recordings/{rec_id}")
def get_recording(rec_id: int, s: Session = Depends(db)):
    r = s.get(Recording, rec_id)
    if not r:
        raise HTTPException(404, "Recording not found")
    return _recording_full(r)


@app.patch("/api/recordings/{rec_id}")
def update_recording(rec_id: int, body: RecordingUpdate, s: Session = Depends(db)):
    import json as _json

    r = s.get(Recording, rec_id)
    if not r:
        raise HTTPException(404, "Recording not found")
    dados = body.model_dump(exclude_unset=True)
    campo = {
        "title": "title", "topic": "topic", "transcript": "transcript",
        "markdown": "markdown", "kind": "kind", "summaryJson": "summary_json",
    }
    for api_field, model_field in campo.items():
        if api_field in dados:
            setattr(r, model_field, dados[api_field])
    if "tags" in dados:
        r.tags = _json.dumps(dados["tags"] or [], ensure_ascii=False)
    if "liveState" in dados:
        r.live_state_json = _json.dumps(dados["liveState"] or {}, ensure_ascii=False)
    s.commit()
    s.refresh(r)
    return _recording_full(r)


@app.delete("/api/recordings/{rec_id}")
def delete_recording(rec_id: int, s: Session = Depends(db)):
    r = s.get(Recording, rec_id)
    if not r:
        raise HTTPException(404, "Recording not found")
    s.delete(r)
    s.commit()
    return {"ok": True}


@app.post("/api/recordings/{rec_id}/archive")
def archive_recording(rec_id: int, body: ArchiveRecordingBody, s: Session = Depends(db)):
    r = s.get(Recording, rec_id)
    if not r:
        raise HTTPException(404, "Recording not found")
    r.archived_at = datetime.utcnow() if body.archived else None
    s.commit()
    s.refresh(r)
    return _recording_base(r)


@app.get("/api/recordings/{rec_id}/export")
def export_recording(rec_id: int, format: str = "md", s: Session = Depends(db)):
    """Exporta a reunião em `md`, `txt` ou `json`."""
    import json as _json

    from relay.meetings_export import to_markdown, to_text

    r = s.get(Recording, rec_id)
    if not r:
        raise HTTPException(404, "Recording not found")

    completo = _recording_full(r)
    formato = (format or "md").lower()
    if formato == "json":
        corpo = _json.dumps(completo, ensure_ascii=False, indent=2)
        media, ext = "application/json", "json"
    elif formato == "txt":
        corpo = to_text(completo)
        media, ext = "text/plain; charset=utf-8", "txt"
    elif formato == "md":
        corpo = to_markdown(completo)
        media, ext = "text/markdown; charset=utf-8", "md"
    else:
        raise HTTPException(400, "format deve ser md, txt ou json")

    import unicodedata

    base = (r.title or r.topic or f"reuniao-{r.id}").strip()
    # nome de arquivo em ASCII: cabeçalho HTTP não aceita acento
    sem_acento = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    seguro = "".join(c if c.isalnum() or c in "-_ " else "-" for c in sem_acento).strip().replace(" ", "-")
    nome = f"{(seguro or 'reuniao')[:60]}-{r.id}.{ext}"
    return Response(
        # bytes para o download sair sempre em UTF-8 (acentos do português)
        content=corpo.encode("utf-8"),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@app.post("/api/recordings/{rec_id}/analyze")
def analyze_recording(
    rec_id: int,
    body: AnalyzeRecordingBody | None = None,
    projectId: int | None = None,
    save: bool = False,
    s: Session = Depends(db),
):
    """Analisa a reunião com o contexto do projeto (board, atrasos, dailies).

    Usa IA quando há provedor configurado; sem IA cai no modo heurístico (só
    fatos do contexto). `save=true` mescla o resultado no estado da reunião.
    """
    import json as _json

    from relay.config import get_active_ai_provider
    from relay.meeting_analysis import analyze_meeting, merge_live_state
    from relay.meeting_context import project_context

    body = body or AnalyzeRecordingBody()
    projeto = body.projectId if body.projectId is not None else projectId
    salvar = bool(body.save or save)

    r = s.get(Recording, rec_id)
    if not r:
        raise HTTPException(404, "Recording not found")

    contexto = ""
    if projeto:
        if not s.query(Project).filter(Project.id == projeto).first():
            raise HTTPException(404, "Project not found")
        contexto = project_context(s, projeto)

    usa_ia = bool(get_active_ai_provider())
    resultado = analyze_meeting(
        title=r.title or "",
        transcript=r.transcript or "",
        context=contexto,
        use_ai=usa_ia,
    )

    salvo = False
    if salvar:
        estado = {}
        try:
            estado = _json.loads(r.live_state_json) if r.live_state_json else {}
        except Exception:  # noqa: BLE001
            estado = {}
        r.live_state_json = _json.dumps(merge_live_state(estado, resultado), ensure_ascii=False)
        s.commit()
        s.refresh(r)
        salvo = True

    return {
        "recordingId": r.id,
        "projectId": projeto,
        "usedProjectContext": bool(contexto),
        "aiAvailable": usa_ia,
        "engine": resultado.get("engine", "heuristic"),
        "saved": salvo,
        "tips": resultado.get("tips", []),
        "plan": resultado.get("plan", []),
        "actionItems": resultado.get("actionItems", []),
        "decisions": resultado.get("decisions", []),
        "questions": resultado.get("questions", []),
        "sections": _recording_full(r)["sections"] if salvo else None,
    }


@app.get("/api/recordings/{rec_id}/audio")
def recording_audio(rec_id: int, s: Session = Depends(db)):
    """Áudio original da gravação (quando existir no disco)."""
    from pathlib import Path

    from fastapi.responses import FileResponse

    r = s.get(Recording, rec_id)
    if not r or not (r.audio_path or "").strip():
        raise HTTPException(404, "Audio not found")
    caminho = Path(r.audio_path)
    if not caminho.exists():
        raise HTTPException(404, "Audio file not found")
    return FileResponse(str(caminho), media_type="audio/wav", filename=caminho.name)


# ---------------------------------------------------------------------------
# Web UI (servida junto com a API, se o bundle estiver buildado em webui/dist)
# ---------------------------------------------------------------------------

def _mount_webui(_app):
    import mimetypes
    from pathlib import Path

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    # Garante content-types corretos para o PWA
    mimetypes.add_type("application/manifest+json", ".webmanifest")
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("image/svg+xml", ".svg")

    dist = Path(__file__).resolve().parents[2] / "webui" / "dist"
    if not (dist / "index.html").exists():
        return  # web UI não buildada; apenas a API responde

    assets = dist / "assets"
    if assets.exists():
        _app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @_app.get("/{full_path:path}", include_in_schema=False)
    def _spa(full_path: str):
        # rotas /api/* já foram tratadas acima; aqui é o SPA React
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(dist / "index.html"))


_mount_webui(app)
