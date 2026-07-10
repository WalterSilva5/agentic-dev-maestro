"""Agente estratégico interno (LangGraph + ferramentas da aplicação)."""
from __future__ import annotations

from maestro_local.ai.providers import build_chat_model
from maestro_local.ai.tools import ALL_TOOLS
from maestro_local.config import get_active_ai_provider

SYSTEM_PROMPT = (
    "Você é o assistente estratégico do Agentic Dev Maestro, uma aplicação local "
    "de gestão de tarefas para desenvolvedores. Você ajuda o desenvolvedor a "
    "organizar o trabalho: resume o estado do board, sugere prioridades, solicita "
    "revisões de tarefas, cria TODOs, comenta tarefas, consulta métricas e a base "
    "de conhecimento.\n\n"
    "Ferramentas disponíveis:\n"
    "- Leitura: list_projects, get_board_summary, list_tasks, get_project_metrics, "
    "list_pending_todos, get_recent_activity, search_knowledge_base.\n"
    "- Ação: request_task_review, add_task_comment, create_todo.\n\n"
    "Regras:\n"
    "- Você é um AUXILIAR. Nunca faz commits, pushs ou decisões de arquitetura.\n"
    "- Antes de agir sobre tarefas, use as ferramentas de leitura para se situar.\n"
    "- Consulte search_knowledge_base quando a pergunta envolver decisões, "
    "procedimentos ou anotações já registradas.\n"
    "- Ao solicitar revisão, sempre explique o motivo de forma clara.\n"
    "- Seja conciso e direto. Responda em português do Brasil.\n"
    "- Se não houver projeto ou dados, oriente o usuário a criar primeiro."
)

# Cache do grafo compilado por (base_url, model, temperatura). Evita recompilar
# o ReAct a cada mensagem do chat.
_AGENT_CACHE: dict = {}


def build_agent(temperature: float = 0.3):
    """Constrói (ou reusa do cache) o agente ReAct com as ferramentas internas.
    Pode lançar ProviderNotConfigured se não houver provedor/modelo configurado."""
    provider = get_active_ai_provider() or {}
    key = (provider.get("base_url"), provider.get("model"), round(float(temperature), 2))
    cached = _AGENT_CACHE.get(key)
    if cached is not None:
        return cached

    llm = build_chat_model(temperature=temperature)
    from langgraph.prebuilt import create_react_agent

    agent = create_react_agent(llm, ALL_TOOLS, prompt=SYSTEM_PROMPT)
    _AGENT_CACHE[key] = agent
    return agent


def clear_agent_cache() -> None:
    """Descarta os agentes em cache (ex.: ao trocar de provedor)."""
    _AGENT_CACHE.clear()


def run_agent(messages: list[dict]) -> str:
    """Executa o agente com o histórico de mensagens (role/content) e retorna o texto final.

    messages: lista de {"role": "user"|"assistant", "content": str}
    """
    agent = build_agent()
    lc_messages = [(m["role"], m["content"]) for m in messages]
    result = agent.invoke({"messages": lc_messages})
    final = result["messages"][-1]
    return getattr(final, "content", str(final))
