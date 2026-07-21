"""Estado de uma reunião em edição.

Reúne num só objeto o que antes eram vários atributos soltos na view
(`_current`, `_live_state`, `_context_items`, `_md_source`, ...). Separa
explicitamente:

* **entradas** — preparação e contexto, que o usuário monta ANTES de gravar e
  que sobrevivem ao início de uma nova gravação;
* **saídas** — transcrição, resumo e itens do assistente, que são zerados a
  cada gravação nova.

Só dados: nada de Qt nem de banco aqui.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

EMPTY_LIVE_STATE = {
    "action_items": [],
    "decisions": [],
    "questions": [],
    "plan": [],
    "tips": [],
}

LIVE_KEYS = tuple(EMPTY_LIVE_STATE)


def empty_live_state() -> dict:
    """Cópia nova do estado vazio (evita compartilhar as listas)."""
    return {k: [] for k in LIVE_KEYS}


def live_state_from_summary(summary: dict) -> dict:
    """Deriva os itens da tela (abas) a partir do resumo da análise.

    Serve de retrocompatibilidade: gravações analisadas antes de existirem as
    abas guardaram só o `summary_json`. Ao reabrir, montamos as abas a partir
    dele — ações, decisões e perguntas em aberto — para nada ficar invisível.
    """
    st = empty_live_state()
    if not isinstance(summary, dict):
        return st
    for d in summary.get("decisions") or []:
        if isinstance(d, str) and d.strip():
            st["decisions"].append(d.strip())
    for a in summary.get("action_items") or []:
        if isinstance(a, dict):
            desc = (a.get("description") or "").strip()
            if desc:
                st["action_items"].append(
                    {"description": desc, "assignee": a.get("assignee") or ""})
        elif isinstance(a, str) and a.strip():
            st["action_items"].append({"description": a.strip(), "assignee": ""})
    for q in summary.get("open_questions") or []:
        if isinstance(q, str) and q.strip():
            st["questions"].append(
                {"question": q.strip(), "answer": "", "resolved": False})
    return st


@dataclass
class ContextItem:
    """Um anexo de contexto (arquivo, imagem ou captura de tela já lida)."""
    label: str
    text: str


@dataclass
class MeetingSession:
    """Reunião em edição — entradas, saídas e o vínculo com o registro salvo."""

    # --- vínculo com o banco ---
    rec_id: int | None = None

    # --- entradas (preparação) ---
    kind: str = "meeting"          # meeting | study
    topic: str = ""
    prep: str = ""
    context_items: list[ContextItem] = field(default_factory=list)

    # --- saídas ---
    transcript: str = ""
    markdown: str = ""             # resumo da IA (fonte markdown)
    summary_json: str = ""
    live_state: dict = field(default_factory=empty_live_state)
    title: str = ""
    tags: list = field(default_factory=list)
    duration: float = 0.0
    language: str = ""
    audio_path: str = ""

    # --- transitório (não persiste) ---
    screen_text: str = ""          # última leitura do monitor observado

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def reset_outputs(self) -> None:
        """Zera as SAÍDAS, preservando preparação/contexto (entradas).

        É o que acontece ao iniciar uma gravação: a reunião anterior não deve
        deixar transcrição/itens para trás, mas a pauta que o usuário acabou de
        escrever para ESTA reunião continua valendo.
        """
        self.rec_id = None
        self.transcript = ""
        self.markdown = ""
        self.summary_json = ""
        self.live_state = empty_live_state()
        self.title = ""
        self.tags = []
        self.duration = 0.0
        self.language = ""
        self.audio_path = ""

    def reset_all(self) -> None:
        """Reunião do zero: limpa entradas E saídas ('Nova reunião')."""
        self.reset_outputs()
        self.topic = ""
        self.prep = ""
        self.context_items = []
        self.screen_text = ""

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def has_live_items(self) -> bool:
        return any(self.live_state.get(k) for k in LIVE_KEYS)

    def has_content(self) -> bool:
        """Há algo que valha salvar/exportar?"""
        return bool(self.transcript.strip() or self.markdown.strip()
                    or self.has_live_items())

    @property
    def questions(self) -> list:
        return self.live_state.setdefault("questions", [])

    # ------------------------------------------------------------------
    # Perguntas & respostas
    # ------------------------------------------------------------------
    def set_answer(self, index: int, text: str) -> bool:
        """Define a resposta de uma pergunta. Responder marca como resolvida."""
        qs = self.questions
        if not (0 <= index < len(qs)):
            return False
        text = (text or "").strip()
        q = qs[index]
        if isinstance(q, dict):
            q["answer"] = text
            q["resolved"] = bool(text) or bool(q.get("resolved"))
        else:  # tolera string simples (formato antigo)
            qs[index] = {"question": str(q), "answer": text, "resolved": bool(text)}
        return True

    def toggle_resolved(self, index: int) -> bool:
        qs = self.questions
        if not (0 <= index < len(qs)):
            return False
        q = qs[index]
        if isinstance(q, dict):
            q["resolved"] = not q.get("resolved")
        else:
            qs[index] = {"question": str(q), "answer": "", "resolved": True}
        return True

    def merge_live_state(self, new_state: dict) -> dict:
        """Aplica um estado vindo do agente preservando respostas já dadas.

        O modelo às vezes reemite uma pergunta sem a resposta; respostas
        (inclusive as digitadas à mão) são informação confirmada e não podem
        ser perdidas.
        """
        old = {str(q.get("question", "")).strip(): q
               for q in self.questions if isinstance(q, dict)}
        for q in new_state.get("questions", []) or []:
            if not isinstance(q, dict):
                continue
            prev = old.get(str(q.get("question", "")).strip())
            if prev and not str(q.get("answer") or "").strip() \
                    and str(prev.get("answer") or "").strip():
                q["answer"] = prev["answer"]
                q["resolved"] = prev.get("resolved", q.get("resolved"))
        merged = {k: new_state.get(k, self.live_state.get(k, [])) for k in LIVE_KEYS}
        self.live_state = merged
        return merged

    # ------------------------------------------------------------------
    # Contexto anexado
    # ------------------------------------------------------------------
    def add_context(self, label: str, text: str) -> None:
        self.context_items.append(ContextItem(label=label, text=text))

    def remove_context(self, index: int) -> bool:
        if 0 <= index < len(self.context_items):
            self.context_items.pop(index)
            return True
        return False

    # ------------------------------------------------------------------
    # Serialização do estado do assistente (coluna live_state_json)
    # ------------------------------------------------------------------
    def live_state_json(self) -> str:
        return json.dumps(self.live_state, ensure_ascii=False)

    def load_live_state_json(self, raw: str | None) -> None:
        try:
            data = json.loads(raw) if raw else {}
        except Exception:  # noqa: BLE001 - json inválido não pode derrubar a tela
            data = {}
        base = empty_live_state()
        if isinstance(data, dict):
            base.update({k: v for k, v in data.items() if k in LIVE_KEYS})
        self.live_state = base
