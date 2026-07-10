"""Camada central de chamadas ao LLM.

Um único ponto para: reusar o modelo (cache em build_chat_model), obter JSON de
forma robusta (with_structured_output do LangChain quando o provedor suporta
function-calling; senão, fallback para parse manual) e chamadas de texto.

Todos os assistentes (triagem, digest, tradutor, code review, inglês, reunião ao
vivo, etc.) devem usar `invoke_json`/`invoke_text` em vez de falar com o
ChatOpenAI direto — assim otimizações (retry, cache, structured output) ficam
num lugar só.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("maestro.ai.llm")

# Modelos que não suportam structured output (function-calling/json schema).
# Descoberto por tentativa: uma vez que falha, cai direto no fallback.
_NO_STRUCTURED: set[str] = set()


def get_chat_model(temperature: float = 0.3, provider: dict | None = None):
    """Modelo de chat (reusado do cache). Levanta ProviderNotConfigured."""
    from maestro_local.ai.providers import build_chat_model
    return build_chat_model(provider=provider, temperature=temperature)


def _model_id(model) -> str:
    return (getattr(model, "model_name", None)
            or getattr(model, "model", None) or str(type(model)))


def invoke_text(messages, temperature: float = 0.3, provider: dict | None = None) -> str:
    """Chamada de texto simples. `messages`: lista de (role, content)."""
    model = get_chat_model(temperature, provider)
    resp = model.invoke(messages)
    return getattr(resp, "content", str(resp))


def invoke_vision(image_bytes: bytes, prompt: str, mime: str = "image/png",
                  temperature: float = 0.2, provider: dict | None = None) -> str:
    """Envia uma imagem + prompt para um modelo com visão e retorna texto.

    A imagem vai como data URL base64 no formato multimodal do OpenAI/LangChain.
    Levanta exceção se o provedor/modelo ativo não suportar visão — o chamador
    deve tratar o fallback (ex.: registrar só o nome do arquivo).
    """
    import base64

    from langchain_core.messages import HumanMessage

    b64 = base64.b64encode(image_bytes).decode("ascii")
    url = f"data:{mime};base64,{b64}"
    model = get_chat_model(temperature, provider)
    msg = HumanMessage(content=[
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": url}},
    ])
    resp = model.invoke([msg])
    return getattr(resp, "content", str(resp))


def invoke_json(messages, schema=None, temperature: float = 0.2,
                provider: dict | None = None) -> dict:
    """Chamada que retorna um dict.

    Se `schema` (um pydantic BaseModel) for dado e o provedor suportar, usa
    `with_structured_output` (saída garantidamente no formato). Caso contrário
    (ou se falhar), cai no parse manual robusto do texto.

    `messages`: lista de (role, content).
    """
    from maestro_local.transcricoes.summarizer import _parse_json_response

    model = get_chat_model(temperature, provider)
    mid = _model_id(model)

    if schema is not None and mid not in _NO_STRUCTURED:
        try:
            result = model.with_structured_output(schema).invoke(messages)
            if hasattr(result, "model_dump"):
                return result.model_dump()
            if isinstance(result, dict):
                return result
            logger.info("structured_output devolveu tipo inesperado (%s); fallback", type(result))
        except Exception as e:  # noqa: BLE001
            logger.info("structured_output indisponível em '%s' (%s); usando fallback", mid, e)
            _NO_STRUCTURED.add(mid)

    resp = model.invoke(messages)
    return _parse_json_response(getattr(resp, "content", str(resp)))
