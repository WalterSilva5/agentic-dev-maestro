"""Maestro Local — FastAPI application.

All endpoints are open (no auth). The response shapes mirror the web version
so that agents can use the same API format against both backends.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from maestro_local.db.models import (
    ActivityLog,
    BoardColumn,
    Comment,
    DailyNote,
    Document,
    Label,
    Project,
    StudyPlan,
    StudySession,
    StudyTopic,
    Task,
    TaskChecklist,
    TaskDependency,
    Todo,
    get_session,
    task_labels,
    DEFAULT_COLUMNS,
)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="Maestro Local", version="0.1.0")

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
    dueDate: str | None = None
    assignee: str | None = None
    requiresHuman: bool | None = None


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
    rank: Optional[str] = None
    dueDate: str | None = None
    assignee: str | None = None
    requiresHuman: bool | None = None


class MoveBody(BaseModel):
    columnId: int


class ChecklistBody(BaseModel):
    title: str


class DependencyBody(BaseModel):
    blockerCode: str


class LabelCreate(BaseModel):
    name: str
    color: Optional[str] = None


class CommentCreate(BaseModel):
    taskId: int
    body: str
    type: Optional[str] = "COMMENT"


class CommentUpdate(BaseModel):
    body: str


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
        "parentId": t.parent_id,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
        "updatedAt": t.updated_at.isoformat() if t.updated_at else None,
        "labels": [_label_dict(lb) for lb in t.labels],
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
        "createdAt": p.created_at.isoformat() if p.created_at else None,
    }


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
    p = Project(name=body.name, key=body.key.upper(), description=body.description)
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


@app.get("/api/projects/{project_id}/board")
def project_board(project_id: int, s: Session = Depends(db)):
    p = s.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return {
        **_project_dict(p),
        "columns": [_column_dict(c, include_tasks=True) for c in p.columns],
    }


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
    s.commit()
    return _project_dict(p)


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
        "rank": "rank",
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


@app.post("/api/tasks/{code}/move")
def move_task(code: str, body: MoveBody, s: Session = Depends(db)):
    task = _resolve_task(code, s)
    old_col = task.column
    new_col = s.query(BoardColumn).filter(BoardColumn.id == body.columnId).first()
    if not new_col:
        raise HTTPException(404, "Column not found")
    if new_col.name.lower() in ("revisão", "revisao", "review"):
        has_review = (
            s.query(Comment)
            .filter(Comment.task_id == task.id, Comment.type == "CODE_REVIEW")
            .first()
        )
        if not has_review:
            raise HTTPException(
                422,
                "Code review obrigatorio antes de mover para Revisao. "
                "Crie um comentario com type=CODE_REVIEW na tarefa.",
            )
    task.column_id = new_col.id
    task.updated_at = datetime.utcnow()
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
    c = Comment(task_id=body.taskId, body=body.body, type=body.type)
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


class TodoUpdate(BaseModel):
    text: Optional[str] = None
    done: Optional[bool] = None


def _todo_dict(t: Todo) -> dict:
    return {
        "id": t.id,
        "text": t.text,
        "done": t.done,
        "sortOrder": t.sort_order,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
        "completedAt": t.completed_at.isoformat() if t.completed_at else None,
    }


@app.get("/api/todos")
def list_todos(done: Optional[bool] = None, s: Session = Depends(db)):
    q = s.query(Todo)
    if done is not None:
        q = q.filter(Todo.done.is_(done))
    todos = q.order_by(Todo.done, Todo.sort_order, Todo.id).all()
    return [_todo_dict(t) for t in todos]


@app.post("/api/todos")
def create_todo(body: TodoCreate, s: Session = Depends(db)):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text é obrigatório")
    t = Todo(text=text, sort_order=s.query(Todo).count())
    s.add(t)
    s.commit()
    s.refresh(t)
    return _todo_dict(t)


@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate, s: Session = Depends(db)):
    t = s.query(Todo).get(todo_id)
    if not t:
        raise HTTPException(status_code=404, detail="TODO não encontrado")
    if body.text is not None:
        t.text = body.text.strip()
    if body.done is not None:
        t.done = body.done
        t.completed_at = datetime.utcnow() if body.done else None
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
    from maestro_local.skills.catalog import SKILLS, CATEGORIES

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
    from maestro_local.skills.catalog import SKILLS

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
    from maestro_local.config import get_active_workspace_id, list_workspaces
    return {"active": get_active_workspace_id(), "workspaces": list_workspaces()}


@app.post("/api/workspaces/active")
def set_active_workspace_ep(body: dict):
    from maestro_local.config import get_workspace_db_path, set_active_workspace
    from maestro_local.db.models import switch_db
    ws_id = body.get("id")
    if not ws_id:
        raise HTTPException(status_code=400, detail="id é obrigatório")
    set_active_workspace(ws_id)
    switch_db(get_workspace_db_path(ws_id))
    return {"ok": True, "active": ws_id}


# ---------------------------------------------------------------------------
# Assistente (agente interno)
# ---------------------------------------------------------------------------


class AssistantChat(BaseModel):
    messages: list[dict]


@app.post("/api/assistant/chat")
def assistant_chat(body: AssistantChat):
    from maestro_local.ai.agent import run_agent
    try:
        reply = run_agent(body.messages)
        return {"reply": reply}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseModel):
    language: Optional[str] = None
    activeProviderId: Optional[str] = None
    aiProviders: Optional[list] = None
    whisperModel: Optional[str] = None


def _settings_dict() -> dict:
    from maestro_local.config import (
        get_active_ai_provider,
        get_language,
        list_ai_providers,
        load_config,
    )
    cron = load_config().get("settings", {}).get("transcricoes", {})
    active = get_active_ai_provider()
    return {
        "language": get_language(),
        "aiProviders": list_ai_providers(),
        "activeProviderId": active["id"] if active else None,
        "whisperModel": cron.get("whisper_model", "small"),
    }


@app.get("/api/settings")
def get_settings():
    return _settings_dict()


@app.put("/api/settings")
def put_settings(body: SettingsUpdate):
    from maestro_local.config import (
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
    return _settings_dict()


# ---------------------------------------------------------------------------
# Web UI (servida junto com a API, se o bundle estiver buildado em webui/dist)
# ---------------------------------------------------------------------------

def _mount_webui(_app):
    from pathlib import Path

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    dist = Path(__file__).resolve().parents[2] / "webui" / "dist"
    if not (dist / "index.html").exists():
        return  # web UI não buildada; apenas a API responde

    assets = dist / "assets"
    if assets.exists():
        _app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @_app.get("/{full_path:path}", include_in_schema=False)
    def _spa(full_path: str):
        # rotas /api/* já foram tratadas acima; aqui é o SPA React
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(dist / "index.html"))


_mount_webui(app)
