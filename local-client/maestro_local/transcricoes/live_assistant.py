"""Assistente de reunião ao vivo: acompanha, planeja e dá dicas em tempo real.

Roda em QThreads para não travar a GUI. Reusa o provedor de IA ativo via
build_chat_model. A extração é *incremental*: recebe o que já foi extraído + o
trecho novo do transcript e devolve o estado mesclado (sem reprocessar tudo).
Além de ações/decisões/perguntas, o assistente sugere um **plano de ação** e
**dicas** conforme a reunião avança, usando o CONTEXTO do workspace/projeto
selecionado quando fornecido.
"""
from __future__ import annotations

import json
import logging

from PySide6.QtCore import QThread, Signal
from pydantic import BaseModel, Field

logger = logging.getLogger("maestro.transcricoes.live")


class _LiveAction(BaseModel):
    description: str = ""
    assignee: str = ""


class LiveStateSchema(BaseModel):
    """Estado incremental da reunião ao vivo (para structured output)."""
    action_items: list[_LiveAction] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    resolved_questions: list[str] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)


LIVE_EXTRACT_SYSTEM = """Você é um assistente que acompanha uma reunião em tempo real. Você mantém um
resumo estruturado incremental E ATUA COMO COPILOTO: sugere um plano de ação e dá dicas úteis
conforme a reunião avança, levando em conta o CONTEXTO do workspace/projeto quando fornecido.

Recebe o CONTEXTO (workspace/projeto atual), o ESTADO ATUAL (JSON já produzido) e um TRECHO NOVO
da transcrição. Devolva o ESTADO ATUALIZADO, mesclando o trecho novo com o que já existia.

Responda SEMPRE apenas com JSON válido nesta estrutura:
{
    "action_items": [{"description": "ação", "assignee": "responsável ou null"}],
    "decisions": ["decisão tomada"],
    "open_questions": ["pergunta ainda em aberto"],
    "resolved_questions": ["pergunta que já foi respondida durante a reunião"],
    "plan": ["passo objetivo do plano de ação, em ordem de execução"],
    "tips": ["dica/observação proativa do assistente"]
}

Regras:
- NUNCA remova action_items/decisions que já existiam, a não ser que o trecho novo os torne resolvidos.
- Se uma pergunta que estava em "open_questions" for respondida durante a reunião, MOVA-A para
  "resolved_questions" (mantendo o texto original da pergunta) — NÃO a apague. Uma pergunta nunca
  deve estar nas duas listas ao mesmo tempo.
- "plan": derive um plano de ação prático do que foi discutido/decidido (5 a 8 passos no máximo);
  refine-o a cada trecho novo em vez de recomeçar. Se houver contexto de projeto, alinhe os passos a ele.
- "tips": sugestões proativas do copiloto — riscos, pontos esquecidos, boas práticas, dependências,
  ou algo do CONTEXTO do projeto que seja relevante (máx. 5). Não repita o que já é óbvio na transcrição.
- Não invente fatos; para plan/tips você pode inferir recomendações, deixando claro que são sugestões.
- Responda em português do Brasil.
"""

LIVE_EXTRACT_USER = """CONTEXTO:
{context}

ESTADO ATUAL:
{state}

TRECHO NOVO DA TRANSCRIÇÃO:
{new_text}

Retorne apenas o JSON do estado atualizado."""

LIVE_ASK_SYSTEM = """Você é um copiloto de reunião. Responde perguntas sobre a reunião em andamento
usando a transcrição fornecida e, se útil, o CONTEXTO do workspace/projeto. Se algo não foi dito na
reunião, diga isso claramente. Seja direto e responda em português do Brasil."""

LIVE_ASK_USER = """CONTEXTO:
{context}

TRANSCRIÇÃO ATÉ AGORA:
{transcript}

PERGUNTA: {question}

Responda de forma objetiva."""


EMPTY_STATE = {
    "action_items": [],
    "decisions": [],
    "open_questions": [],
    "resolved_questions": [],
    "plan": [],
    "tips": [],
}


def _clamp_transcript(text: str, max_words: int = 4000) -> str:
    """Limita o contexto enviado à IA (reunião longa não estoura o modelo)."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[-max_words:])


class LiveExtractWorker(QThread):
    """Faz UMA passada incremental e emite o estado mesclado (com plano e dicas)."""

    done = Signal(dict)     # {action_items, decisions, open_questions, plan, tips}
    failed = Signal(str)

    def __init__(self, state: dict, new_text: str, context: str = "", parent=None):
        super().__init__(parent)
        self.state = {**EMPTY_STATE, **(state or {})}
        self.new_text = new_text
        self.context = context or "(sem contexto de projeto)"

    def run(self) -> None:
        from maestro_local.ai.llm import invoke_json
        try:
            state_json = json.dumps(self.state, ensure_ascii=False)
            user = LIVE_EXTRACT_USER.format(
                context=_clamp_transcript(self.context, 600),
                state=state_json,
                new_text=_clamp_transcript(self.new_text, 1500),
            )
            parsed = invoke_json([("system", LIVE_EXTRACT_SYSTEM), ("user", user)],
                                 schema=LiveStateSchema, temperature=0.2)
            if not isinstance(parsed, dict) or "parse_error" in parsed or "raw_response" in parsed:
                # Falhou o parse: mantém o estado anterior para não perder dados.
                self.done.emit(self.state)
                return
            merged = {
                key: parsed.get(key, self.state.get(key, []))
                for key in ("action_items", "decisions", "open_questions",
                            "resolved_questions", "plan", "tips")
            }
            # Garante que uma pergunta resolvida não continue aparecendo como aberta.
            resolved = {str(q).strip().lower() for q in merged.get("resolved_questions", [])}
            merged["open_questions"] = [
                q for q in merged.get("open_questions", [])
                if str(q).strip().lower() not in resolved
            ]
            self.done.emit(merged)
        except Exception as e:  # noqa: BLE001
            logger.warning("Live extract falhou: %s", e)
            self.failed.emit(str(e))


class LiveAskWorker(QThread):
    """Responde uma pergunta pontual com base no transcript (e no contexto)."""

    answered = Signal(str)
    failed = Signal(str)

    def __init__(self, transcript: str, question: str, context: str = "", parent=None):
        super().__init__(parent)
        self.transcript = transcript
        self.question = question
        self.context = context or "(sem contexto de projeto)"

    def run(self) -> None:
        from maestro_local.ai.llm import invoke_text
        try:
            user = LIVE_ASK_USER.format(
                context=_clamp_transcript(self.context, 600),
                transcript=_clamp_transcript(self.transcript),
                question=self.question,
            )
            text = invoke_text([("system", LIVE_ASK_SYSTEM), ("user", user)], temperature=0.2)
            self.answered.emit((text or "").strip())
        except Exception as e:  # noqa: BLE001
            logger.warning("Live ask falhou: %s", e)
            self.failed.emit(str(e))
