"""Assistente de reunião ao vivo: extração incremental + perguntar à reunião.

Roda em QThreads para não travar a GUI. Reusa o provedor de IA ativo via
build_chat_model. Extração é *incremental*: recebe o que já foi extraído + o
trecho novo do transcript e devolve o estado mesclado (sem reprocessar tudo),
mantendo o custo baixo em reuniões longas.
"""
from __future__ import annotations

import json
import logging

from PySide6.QtCore import QThread, Signal

from maestro_local.ai.providers import build_chat_model

from .summarizer import _parse_json_response

logger = logging.getLogger("maestro.transcricoes.live")


LIVE_EXTRACT_SYSTEM = """Você acompanha uma reunião em tempo real e mantém um resumo estruturado incremental.

Recebe o ESTADO ATUAL (JSON já extraído) e um TRECHO NOVO da transcrição. Sua tarefa é
devolver o ESTADO ATUALIZADO, mesclando as informações do trecho novo com o que já existia.

Responda SEMPRE apenas com JSON válido nesta estrutura:
{
    "action_items": [{"description": "ação", "assignee": "responsável ou null"}],
    "decisions": ["decisão"],
    "open_questions": ["pergunta em aberto"]
}

Regras:
- NUNCA remova itens que já existiam, a não ser que o trecho novo os torne claramente resolvidos.
- Se uma pergunta em aberto for respondida no trecho novo, mova-a para decisions (ou remova).
- Não duplique itens semanticamente iguais.
- Só inclua ações/decisões realmente ditas; não invente.
- Responda em português do Brasil.
"""

LIVE_EXTRACT_USER = """ESTADO ATUAL:
{state}

TRECHO NOVO DA TRANSCRIÇÃO:
{new_text}

Retorne apenas o JSON do estado atualizado."""

LIVE_ASK_SYSTEM = """Você é um assistente que responde perguntas sobre uma reunião em andamento,
usando SOMENTE o que foi dito na transcrição fornecida. Se a informação não estiver na
transcrição, diga que ainda não foi mencionado. Seja direto e responda em português do Brasil."""

LIVE_ASK_USER = """TRANSCRIÇÃO ATÉ AGORA:
{transcript}

PERGUNTA: {question}

Responda de forma objetiva, com base apenas na transcrição."""


EMPTY_STATE = {"action_items": [], "decisions": [], "open_questions": []}


def _clamp_transcript(text: str, max_words: int = 4000) -> str:
    """Limita o contexto enviado à IA (reunião longa não estoura o modelo)."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[-max_words:])


class LiveExtractWorker(QThread):
    """Faz UMA extração incremental e emite o estado mesclado."""

    done = Signal(dict)     # estado atualizado {action_items, decisions, open_questions}
    failed = Signal(str)

    def __init__(self, state: dict, new_text: str, parent=None):
        super().__init__(parent)
        self.state = state or dict(EMPTY_STATE)
        self.new_text = new_text

    def run(self) -> None:
        try:
            llm = build_chat_model(temperature=0.1)
            state_json = json.dumps(self.state, ensure_ascii=False)
            user = LIVE_EXTRACT_USER.format(
                state=state_json, new_text=_clamp_transcript(self.new_text, 1500),
            )
            resp = llm.invoke([("system", LIVE_EXTRACT_SYSTEM), ("user", user)])
            content = getattr(resp, "content", str(resp))
            parsed = _parse_json_response(content)
            if "parse_error" in parsed or "raw_response" in parsed:
                # Falhou o parse: mantém o estado anterior para não perder dados.
                self.done.emit(self.state)
                return
            merged = {
                "action_items": parsed.get("action_items", self.state.get("action_items", [])),
                "decisions": parsed.get("decisions", self.state.get("decisions", [])),
                "open_questions": parsed.get("open_questions", self.state.get("open_questions", [])),
            }
            self.done.emit(merged)
        except Exception as e:  # noqa: BLE001
            logger.warning("Live extract falhou: %s", e)
            self.failed.emit(str(e))


class LiveAskWorker(QThread):
    """Responde uma pergunta pontual com base no transcript atual."""

    answered = Signal(str)
    failed = Signal(str)

    def __init__(self, transcript: str, question: str, parent=None):
        super().__init__(parent)
        self.transcript = transcript
        self.question = question

    def run(self) -> None:
        try:
            llm = build_chat_model(temperature=0.2)
            user = LIVE_ASK_USER.format(
                transcript=_clamp_transcript(self.transcript), question=self.question,
            )
            resp = llm.invoke([("system", LIVE_ASK_SYSTEM), ("user", user)])
            self.answered.emit(getattr(resp, "content", str(resp)).strip())
        except Exception as e:  # noqa: BLE001
            logger.warning("Live ask falhou: %s", e)
            self.failed.emit(str(e))
