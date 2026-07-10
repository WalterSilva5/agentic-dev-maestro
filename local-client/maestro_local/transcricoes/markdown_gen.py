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


def live_meeting_to_markdown(
    *, title: str, kind: str, date_str: str, duration: float, topic: str,
    state: dict, transcript: str = "", summary_md: str = "", prep: str = "",
) -> str:
    """Documento único e estruturado da reunião: junta todos os itens de todas as
    abas do assistente ao vivo (plano, dicas, ações, decisões, perguntas) +
    (opcional) preparação/informações prévias + resumo da IA + transcrição."""
    is_study = kind == "study"
    default_title = (topic if is_study and topic else ("Estudo" if is_study else "Reunião"))
    out = [f"# {title or default_title}", ""]
    out.append(f"**Tipo:** {'Estudo' if is_study else 'Reunião'}  ")
    out.append(f"**Data:** {date_str}  ")
    if duration:
        out.append(f"**Duração:** {format_duration(duration)}  ")
    if topic:
        out.append(f"**Tópico:** {topic}  ")
    out.append("")

    if prep and prep.strip():
        out.append("## 🧭 Preparação")
        out.append(prep.strip())
        out.append("")

    plan = state.get("plan") or []
    if plan:
        out.append("## 🗺 Plano")
        out += [f"{i}. {s}" for i, s in enumerate(plan, 1)]
        out.append("")
    tips = state.get("tips") or []
    if tips:
        out.append("## 💡 Dicas")
        out += [f"- {tp}" for tp in tips]
        out.append("")
    actions = state.get("action_items") or []
    if actions:
        out.append("## ✅ Ações")
        for a in actions:
            if isinstance(a, dict):
                desc, who = a.get("description", ""), a.get("assignee")
            else:
                desc, who = str(a), None
            out.append(f"- [ ] {desc}" + (f" _({who})_" if who else ""))
        out.append("")
    decisions = state.get("decisions") or []
    if decisions:
        out.append("## 📌 Decisões")
        out += [f"- {d}" for d in decisions]
        out.append("")
    questions = state.get("questions") or []
    if questions:
        out.append("## ❓ Perguntas & respostas")
        for q in questions:
            if isinstance(q, dict):
                text = str(q.get("question") or "").strip()
                ans = str(q.get("answer") or "").strip()
                resolved = bool(q.get("resolved"))
            else:
                text, ans, resolved = str(q), "", False
            if not text:
                continue
            mark = "x" if resolved else " "
            out.append(f"- [{mark}] **{text}**")
            if ans:
                out.append(f"  - _Resposta:_ {ans}")
        out.append("")

    if summary_md and summary_md.strip():
        body = summary_md.strip().splitlines()
        if body and body[0].startswith("# "):  # evita título duplicado
            body = body[1:]
        out.append("## 📝 Resumo estruturado (IA)")
        out.append("\n".join(body).strip())
        out.append("")

    if transcript and transcript.strip():
        out.append("## 🎙 Transcrição")
        out.append(transcript.strip())
        out.append("")

    return "\n".join(out).rstrip() + "\n"


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
