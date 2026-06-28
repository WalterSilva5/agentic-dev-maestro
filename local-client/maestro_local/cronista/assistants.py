"""Assistentes de reunião e estudo: transcrição -> resumo estruturado."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .prompts import (
    MEETING_SYSTEM_PROMPT,
    MEETING_USER_PROMPT,
    STUDY_SYSTEM_PROMPT,
    STUDY_USER_PROMPT,
)
from .summarizer import summarize

logger = logging.getLogger("maestro.cronista.assistants")


# --------------------------- Reunião ---------------------------

@dataclass
class ActionItem:
    description: str
    assignee: str | None = None


@dataclass
class MeetingSummary:
    title: str = ""
    key_points: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    raw_transcript: str = ""
    duration: float = 0.0
    language: str = ""


def analyze_meeting(transcript_text: str, duration: float = 0.0, language: str = "") -> MeetingSummary:
    result = summarize(transcript_text, MEETING_SYSTEM_PROMPT, MEETING_USER_PROMPT)
    s = MeetingSummary(raw_transcript=transcript_text, duration=duration, language=language)
    if "error" in result or "parse_error" in result:
        s.title = "Reunião (erro na análise)"
        s.key_points = [result.get("raw_response", str(result))]
        return s
    s.title = result.get("title", "Reunião sem título")
    s.key_points = result.get("key_points", [])
    s.decisions = result.get("decisions", [])
    s.open_questions = result.get("open_questions", [])
    s.tags = result.get("tags", [])
    for item in result.get("action_items", []):
        if isinstance(item, dict):
            s.action_items.append(ActionItem(item.get("description", ""), item.get("assignee")))
        elif isinstance(item, str):
            s.action_items.append(ActionItem(item))
    return s


# --------------------------- Estudo ---------------------------

@dataclass
class KeyConcept:
    concept: str
    explanation: str


@dataclass
class Exercise:
    title: str
    description: str
    difficulty: str = "medio"
    hints: list[str] = field(default_factory=list)


@dataclass
class RelatedTopic:
    topic: str
    reason: str


@dataclass
class StudyNotes:
    topic: str = ""
    summary: str = ""
    key_concepts: list[KeyConcept] = field(default_factory=list)
    review_points: list[str] = field(default_factory=list)
    practical_exercises: list[Exercise] = field(default_factory=list)
    related_topics: list[RelatedTopic] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    raw_content: str = ""
    duration: float = 0.0


def analyze_study(content: str, topic: str = "", duration: float = 0.0) -> StudyNotes:
    result = summarize(content, STUDY_SYSTEM_PROMPT, STUDY_USER_PROMPT, topic=topic or "geral")
    n = StudyNotes(raw_content=content, duration=duration)
    if "error" in result or "parse_error" in result:
        n.topic = topic or "Estudo (erro na análise)"
        n.summary = result.get("raw_response", str(result))
        return n
    n.topic = result.get("topic", topic)
    n.summary = result.get("summary", "")
    n.review_points = result.get("review_points", [])
    n.resources = result.get("resources", [])
    n.tags = result.get("tags", [])
    for item in result.get("key_concepts", []):
        if isinstance(item, dict):
            n.key_concepts.append(KeyConcept(item.get("concept", ""), item.get("explanation", "")))
    for item in result.get("practical_exercises", []):
        if isinstance(item, dict):
            n.practical_exercises.append(Exercise(
                item.get("title", ""), item.get("description", ""),
                item.get("difficulty", "medio"), item.get("hints", []),
            ))
    for item in result.get("related_topics", []):
        if isinstance(item, dict):
            n.related_topics.append(RelatedTopic(item.get("topic", ""), item.get("reason", "")))
    return n
