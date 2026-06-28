"""Geração de markdown a partir dos resumos (sem dependência de templates externos)."""
from __future__ import annotations

from .assistants import MeetingSummary, StudyNotes


def format_duration(seconds: float) -> str:
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h > 0:
        return f"{h}h {m:02d}min {s:02d}s"
    return f"{m}min {s:02d}s"


def meeting_to_markdown(summary: MeetingSummary, date_str: str) -> str:
    out = [f"# {summary.title or 'Reunião'}", ""]
    out.append(f"**Data:** {date_str}  ")
    if summary.duration:
        out.append(f"**Duração:** {format_duration(summary.duration)}  ")
    if summary.tags:
        out.append(f"**Tags:** {', '.join(summary.tags)}  ")
    out.append("")

    if summary.key_points:
        out.append("## Pontos-chave")
        out += [f"- {p}" for p in summary.key_points]
        out.append("")
    if summary.decisions:
        out.append("## Decisões")
        out += [f"- {d}" for d in summary.decisions]
        out.append("")
    if summary.action_items:
        out.append("## Ações")
        for a in summary.action_items:
            who = f" _({a.assignee})_" if a.assignee else ""
            out.append(f"- [ ] {a.description}{who}")
        out.append("")
    if summary.open_questions:
        out.append("## Perguntas em aberto")
        out += [f"- {q}" for q in summary.open_questions]
        out.append("")
    if summary.raw_transcript:
        out.append("## Transcrição")
        out.append(summary.raw_transcript)
        out.append("")
    return "\n".join(out)


def study_to_markdown(notes: StudyNotes, date_str: str) -> str:
    out = [f"# Estudo: {notes.topic or 'Sessão'}", ""]
    out.append(f"**Data:** {date_str}  ")
    if notes.duration:
        out.append(f"**Duração:** {format_duration(notes.duration)}  ")
    if notes.tags:
        out.append(f"**Tags:** {', '.join(notes.tags)}  ")
    out.append("")

    if notes.summary:
        out.append("## Resumo")
        out.append(notes.summary)
        out.append("")
    if notes.key_concepts:
        out.append("## Conceitos-chave")
        for c in notes.key_concepts:
            out.append(f"- **{c.concept}**: {c.explanation}")
        out.append("")
    if notes.review_points:
        out.append("## Pontos para revisar")
        out += [f"- {p}" for p in notes.review_points]
        out.append("")
    if notes.practical_exercises:
        out.append("## Exercícios práticos")
        for ex in notes.practical_exercises:
            out.append(f"### {ex.title} _({ex.difficulty})_")
            out.append(ex.description)
            for h in ex.hints:
                out.append(f"  - 💡 {h}")
            out.append("")
    if notes.related_topics:
        out.append("## Tópicos relacionados")
        for rt in notes.related_topics:
            out.append(f"- **{rt.topic}**: {rt.reason}")
        out.append("")
    if notes.resources:
        out.append("## Recursos")
        out += [f"- {r}" for r in notes.resources]
        out.append("")
    if notes.raw_content:
        out.append("## Conteúdo bruto")
        out.append(notes.raw_content)
        out.append("")
    return "\n".join(out)
