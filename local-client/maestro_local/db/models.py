import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

DATA_DIR = Path(os.environ.get("MAESTRO_DATA_DIR", Path.home() / ".maestro-local"))
DB_PATH = str(DATA_DIR / "maestro.db")


class Base(DeclarativeBase):
    pass


task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", Integer, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    key = Column(String(20), nullable=False, unique=True)
    description = Column(Text)
    task_seq = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    columns = relationship("BoardColumn", back_populates="project", cascade="all,delete-orphan", order_by="BoardColumn.order")
    tasks = relationship("Task", back_populates="project", cascade="all,delete-orphan")


class BoardColumn(Base):
    __tablename__ = "board_columns"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    order = Column(Integer, nullable=False, default=0)
    wip_limit = Column(Integer)
    is_done = Column(Boolean, default=False)

    project = relationship("Project", back_populates="columns")
    tasks = relationship("Task", back_populates="column")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    column_id = Column(Integer, ForeignKey("board_columns.id"), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    objective = Column(Text)
    acceptance = Column(Text)
    type = Column(String(20), default="FEATURE")
    priority = Column(String(10), default="MEDIUM")
    estimate_md = Column(Float)
    parent_id = Column(Integer, ForeignKey("tasks.id"))
    rank = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)
    due_date = Column(DateTime)
    assignee = Column(String(100))
    requires_human = Column(Boolean, default=False)

    project = relationship("Project", back_populates="tasks")
    column = relationship("BoardColumn", back_populates="tasks")
    parent = relationship("Task", remote_side="Task.id", backref="subtasks")
    labels = relationship("Label", secondary=task_labels, back_populates="tasks")
    checklist = relationship("TaskChecklist", back_populates="task", cascade="all,delete-orphan", order_by="TaskChecklist.sort_order")
    comments = relationship("Comment", back_populates="task", cascade="all,delete-orphan", order_by="Comment.created_at")
    documents = relationship("Document", back_populates="task", cascade="all,delete-orphan")
    blocking = relationship("TaskDependency", foreign_keys="TaskDependency.blocker_id", back_populates="blocker", cascade="all,delete-orphan")
    blocked_by = relationship("TaskDependency", foreign_keys="TaskDependency.blocked_id", back_populates="blocked", cascade="all,delete-orphan")

    @property
    def code(self):
        return f"{self.project.key}-{self.number}" if self.project else f"?-{self.number}"

    @property
    def status(self):
        return self.column.name if self.column else ""


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True)
    name = Column(String(60), nullable=False, unique=True)
    color = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", secondary=task_labels, back_populates="labels")


class TaskChecklist(Base):
    __tablename__ = "task_checklist"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    checked = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="checklist")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    body = Column(Text, nullable=False)
    type = Column(String(20), default="COMMENT")
    author = Column(String(100), default="local")
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="comments")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    body = Column(Text, default="")
    type = Column(String(20), default="NOTES")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = relationship("Task", back_populates="documents")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True)
    blocker_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    blocked_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    blocker = relationship("Task", foreign_keys=[blocker_id], back_populates="blocking")
    blocked = relationship("Task", foreign_keys=[blocked_id], back_populates="blocked_by")


class DailyNote(Base):
    __tablename__ = "daily_notes"

    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False, unique=True)
    body = Column(Text, default="")
    report = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(40), nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String(60), nullable=False)
    detail = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


Index("ix_tasks_project_column", Task.project_id, Task.column_id)
Index("ix_tasks_deleted_at", Task.deleted_at)
Index("ix_activity_entity", ActivityLog.entity_type, ActivityLog.entity_id)

_engine = None
_SessionLocal = None
_active_db_path = None


def get_engine(db_path=None):
    global _engine, _active_db_path
    if _engine is None:
        path = db_path or _active_db_path or DB_PATH
        _active_db_path = path
        _engine = create_engine(f"sqlite:///{path}", echo=False)
    return _engine


def get_session(db_path=None) -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(db_path))
    return _SessionLocal()


def init_db(db_path=None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)


def switch_db(db_path: str):
    """Close current engine and switch to a different database file."""
    global _engine, _SessionLocal, _active_db_path
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    _active_db_path = db_path
    init_db(db_path)


DEFAULT_COLUMNS = [
    {"name": "Backlog", "order": 0},
    {"name": "A fazer", "order": 1},
    {"name": "Fazendo", "order": 2},
    {"name": "Revisão", "order": 3},
    {"name": "Concluído", "order": 4, "is_done": True},
]
