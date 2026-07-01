"""Assistente de estudo sob demanda (IA acionada por botões).

Cada ação (explicar, exercícios, quiz, flashcards, sugerir tópicos, tirar
dúvida) roda em uma QThread para não travar a GUI, reusando o provedor de IA
ativo. Ações "de texto" devolvem markdown; "sugerir tópicos" devolve uma lista
estruturada para adicionar ao plano com 1 clique.
"""
from __future__ import annotations

import json
import logging

from PySide6.QtCore import QThread, Signal

from maestro_local.ai.providers import build_chat_model
from maestro_local.transcricoes.summarizer import _parse_json_response

logger = logging.getLogger("maestro.study.assistant")

SYSTEM = (
    "Você é um tutor de programação experiente e didático. Responda sempre em "
    "português do Brasil, de forma clara e prática. Quando fizer sentido, use "
    "exemplos e trechos de código curtos. Formate a resposta em Markdown."
)

# Ações de texto (retornam markdown)
_PROMPTS = {
    "explain": (
        "Explique de forma didática o tópico \"{topic}\"{plan_ctx}. "
        "Comece por uma visão geral simples, depois aprofunde nos pontos "
        "principais com exemplos. Termine com um resumo de 3-5 bullets."
    ),
    "exercises": (
        "Crie de 3 a 5 exercícios práticos sobre \"{topic}\"{plan_ctx}. "
        "Para cada um: um título, o enunciado, a dificuldade (fácil/médio/difícil) "
        "e uma dica. Não dê a solução completa — apenas a dica."
    ),
    "quiz": (
        "Crie um quiz de 5 perguntas sobre \"{topic}\"{plan_ctx} para testar o "
        "conhecimento do estudante. Numere as perguntas. Ao final, em uma seção "
        "separada chamada \"Gabarito\", liste as respostas."
    ),
    "flashcards": (
        "Crie de 6 a 10 flashcards de revisão sobre \"{topic}\"{plan_ctx}. "
        "Use exatamente o formato, um por linha:\n"
        "**P:** pergunta curta\n**R:** resposta objetiva"
    ),
}

_ASK_PROMPT = (
    "O estudante está estudando \"{topic}\"{plan_ctx} e tem a seguinte dúvida:\n\n"
    "{question}\n\nResponda de forma objetiva e didática."
)

_SUGGEST_SYSTEM = (
    "Você é um mentor que monta roteiros de estudo. Responda SEMPRE apenas com "
    "JSON válido, sem texto fora do JSON."
)

_SUGGEST_PROMPT = (
    "Monte a lista de tópicos essenciais para estudar \"{plan}\", em uma ordem "
    "de aprendizado coerente (do básico ao avançado).\n"
    "{existing_ctx}\n"
    "Retorne APENAS este JSON:\n"
    "{{\"topics\": [{{\"title\": \"nome do tópico\", \"estimate_hours\": número}}]}}\n"
    "Regras: 6 a 12 tópicos; títulos curtos; estimate_hours é um inteiro de horas "
    "realista; NÃO repita tópicos que já existem."
)

TEXT_ACTIONS = set(_PROMPTS.keys())


def _plan_ctx(plan_title: str) -> str:
    return f" (dentro do plano de estudo \"{plan_title}\")" if plan_title else ""


def generate_text(action: str, *, topic: str = "", plan: str = "", question: str = "") -> str:
    """Executa uma ação de texto (explain/exercises/quiz/flashcards/ask) e
    devolve markdown. Síncrona — usada pela API e pelo worker da GUI."""
    subject = topic or plan or ""
    llm = build_chat_model(temperature=0.4)
    plan_ctx = _plan_ctx(plan)
    if action == "ask":
        user = _ASK_PROMPT.format(topic=subject, plan_ctx=plan_ctx, question=question)
    else:
        tmpl = _PROMPTS.get(action)
        if not tmpl:
            raise ValueError(f"Ação desconhecida: {action}")
        user = tmpl.format(topic=subject, plan_ctx=plan_ctx)
    resp = llm.invoke([("system", SYSTEM), ("user", user)])
    return getattr(resp, "content", str(resp)).strip()


def suggest_topics(plan: str, existing: list[str] | None = None) -> list[dict]:
    """Sugere tópicos para um plano; devolve list[{title, estimate_hours}]."""
    existing = existing or []
    llm = build_chat_model(temperature=0.3)
    existing_ctx = (
        "Tópicos que JÁ existem no plano (não repita): " + ", ".join(existing)
        if existing else "O plano ainda não tem tópicos."
    )
    user = _SUGGEST_PROMPT.format(plan=plan, existing_ctx=existing_ctx)
    resp = llm.invoke([("system", _SUGGEST_SYSTEM), ("user", user)])
    parsed = _parse_json_response(getattr(resp, "content", str(resp)))
    topics: list[dict] = []
    for item in parsed.get("topics", []) if isinstance(parsed, dict) else []:
        if isinstance(item, dict) and item.get("title"):
            topics.append({
                "title": str(item["title"]).strip()[:200],
                "estimate_hours": item.get("estimate_hours"),
            })
        elif isinstance(item, str) and item.strip():
            topics.append({"title": item.strip()[:200], "estimate_hours": None})
    return topics


def run_action(action: str, *, topic: str = "", plan: str = "",
               question: str = "", existing: list[str] | None = None):
    """Despacha uma ação e devolve str (texto) ou list[dict] (suggest_topics)."""
    if action == "suggest_topics":
        return suggest_topics(plan or topic, existing)
    return generate_text(action, topic=topic, plan=plan, question=question)


_TOPICS_FROM_MATERIAL_SYSTEM = (
    "Você é um mentor que monta roteiros de estudo. Recebe a definição de um plano "
    "(título, categoria, descrição) e, opcionalmente, um MATERIAL anexado (ebooks, "
    "apostilas, documentos). Responda SEMPRE apenas com JSON válido, sem texto fora do JSON."
)

_TOPICS_FROM_MATERIAL_PROMPT = (
    "Monte a lista de tópicos de estudo para o plano abaixo, em uma ordem de aprendizado coerente.\n"
    "PLANO: título=\"{title}\" | categoria={category}\n"
    "{description}\n"
    "{material_intro}{content}\n\n"
    "Retorne APENAS este JSON:\n"
    "{{\"topics\": [{{\"title\": \"tópico\", \"estimate_hours\": número}}]}}\n"
    "Regras: 6 a 15 tópicos; títulos curtos; estimate_hours é um inteiro de horas realista. "
    "Quando houver MATERIAL, os tópicos devem cobrir o conteúdo dele; sem material, baseie-se no título/descrição."
)


def topics_from_material(material: str = "", *, title: str = "",
                         category: str = "", description: str = "") -> list[dict]:
    """Gera os tópicos de um plano a partir dos campos + material anexado (opcional).

    Retorna list[{title, estimate_hours}].
    """
    words = material.split()
    clamped = " ".join(words[:6000]) if len(words) > 6000 else material
    material_intro = "MATERIAL ANEXADO (pode estar truncado):\n" if clamped.strip() else ""
    desc = f"Descrição: {description}" if description else ""
    llm = build_chat_model(temperature=0.3)
    user = _TOPICS_FROM_MATERIAL_PROMPT.format(
        title=title or "(sem título)", category=category or "CURSO",
        description=desc, material_intro=material_intro, content=clamped,
    )
    resp = llm.invoke([("system", _TOPICS_FROM_MATERIAL_SYSTEM), ("user", user)])
    parsed = _parse_json_response(getattr(resp, "content", str(resp)))
    topics: list[dict] = []
    for item in (parsed.get("topics", []) if isinstance(parsed, dict) else []):
        if isinstance(item, dict) and item.get("title"):
            topics.append({
                "title": str(item["title"]).strip()[:200],
                "estimate_hours": item.get("estimate_hours"),
            })
        elif isinstance(item, str) and item.strip():
            topics.append({"title": item.strip()[:200], "estimate_hours": None})
    return topics


class StudyAIWorker(QThread):
    """Executa UMA ação do assistente e emite o resultado.

    result(action, payload): payload é str (markdown) para ações de texto e
    para "ask"; para "suggest_topics" é uma list[dict] {title, estimate_hours}.
    """

    result = Signal(str, object)
    failed = Signal(str, str)   # (action, error)

    def __init__(self, action: str, *, topic: str = "", plan: str = "",
                 question: str = "", existing: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.action = action
        self.topic = topic or plan or ""
        self.plan = plan
        self.question = question
        self.existing = existing or []

    def run(self) -> None:
        try:
            payload = run_action(
                self.action, topic=self.topic, plan=self.plan,
                question=self.question, existing=self.existing,
            )
            self.result.emit(self.action, payload)
        except Exception as e:  # noqa: BLE001
            logger.warning("Study AI (%s) falhou: %s", self.action, e)
            self.failed.emit(self.action, str(e))
