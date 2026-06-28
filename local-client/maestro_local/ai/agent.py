"""Agente estratégico interno (LangGraph + ferramentas da aplicação)."""
from __future__ import annotations

from maestro_local.ai.providers import build_chat_model
from maestro_local.ai.tools import ALL_TOOLS

SYSTEM_PROMPT = (
    "Você é o assistente estratégico do Agentic Dev Maestro, uma aplicação local "
    "de gestão de tarefas para desenvolvedores. Você ajuda o desenvolvedor a "
    "organizar o trabalho: resume o estado do board, sugere prioridades, solicita "
    "revisões de tarefas, cria TODOs e comenta tarefas.\n\n"
    "Regras:\n"
    "- Você é um AUXILIAR. Nunca faz commits, pushs ou decisões de arquitetura.\n"
    "- Antes de agir sobre tarefas, use as ferramentas de leitura (list_projects, "
    "get_board_summary, list_tasks) para se situar.\n"
    "- Ao solicitar revisão, sempre explique o motivo de forma clara.\n"
    "- Seja conciso e direto. Responda em português do Brasil.\n"
    "- Se não houver projeto ou dados, oriente o usuário a criar primeiro."
)


def build_agent(temperature: float = 0.3):
    """Constrói o agente ReAct com as ferramentas internas. Pode lançar
    ProviderNotConfigured se não houver provedor/modelo configurado."""
    llm = build_chat_model(temperature=temperature)
    from langgraph.prebuilt import create_react_agent

    return create_react_agent(llm, ALL_TOOLS, prompt=SYSTEM_PROMPT)


def run_agent(messages: list[dict]) -> str:
    """Executa o agente com o histórico de mensagens (role/content) e retorna o texto final.

    messages: lista de {"role": "user"|"assistant", "content": str}
    """
    agent = build_agent()
    lc_messages = [(m["role"], m["content"]) for m in messages]
    result = agent.invoke({"messages": lc_messages})
    final = result["messages"][-1]
    return getattr(final, "content", str(final))
