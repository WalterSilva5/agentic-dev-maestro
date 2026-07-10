"""Provedores de IA compatíveis com OpenAI (LM Studio, opencode, etc.).

Todos os provedores expõem o mesmo formato /v1/chat/completions, então
basta variar base_url + api_key + model.
"""
from __future__ import annotations

from maestro_local.config import get_active_ai_provider

# Provedores padrão sugeridos (todos compatíveis com OpenAI).
# api_key vazio = o usuário preenche; model vazio = o usuário define.
DEFAULT_PROVIDERS = [
    {
        "id": "lmstudio",
        "name": "LM Studio (local)",
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "model": "",
    },
    {
        "id": "ollama",
        "name": "Ollama (local)",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "",
    },
    {
        "id": "opencode",
        "name": "opencode (Zen Go)",
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_key": "",
        "model": "deepseek-v4-pro",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "",
        "model": "",
    },
    {
        "id": "groq",
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": "",
        "model": "llama-3.3-70b-versatile",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "model": "deepseek-chat",
    },
    {
        "id": "mistral",
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "api_key": "",
        "model": "mistral-large-latest",
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key": "",
        "model": "gemini-2.0-flash",
    },
    {
        "id": "together",
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "api_key": "",
        "model": "",
    },
]


def merge_missing_defaults(providers: list[dict]) -> list[dict]:
    """Adiciona provedores padrão que ainda não existem (por id), sem
    sobrescrever os que o usuário já configurou."""
    existing_ids = {p.get("id") for p in providers}
    merged = list(providers)
    for d in DEFAULT_PROVIDERS:
        if d["id"] not in existing_ids:
            merged.append(dict(d))
    return merged


class ProviderNotConfigured(Exception):
    pass


# Cache de instâncias ChatOpenAI por (base_url, model, api_key, temperatura).
# O cliente é um wrapper leve e sem estado, então reusar evita recriar a cada
# chamada (muitas features chamam o LLM em sequência).
_MODEL_CACHE: dict = {}


def build_chat_model(provider: dict | None = None, temperature: float = 0.3):
    """Constrói (ou reusa do cache) um ChatOpenAI a partir do provedor ativo.

    Import de langchain feito aqui dentro para não pesar o boot do app.
    """
    provider = provider or get_active_ai_provider()
    if not provider:
        raise ProviderNotConfigured(
            "Nenhum provedor de IA configurado. Configure em Configurações."
        )
    if not provider.get("model"):
        raise ProviderNotConfigured(
            f"O provedor '{provider.get('name')}' está sem modelo definido."
        )

    key = (
        provider["base_url"],
        provider["model"],
        provider.get("api_key") or "",
        round(float(temperature), 2),
    )
    cached = _MODEL_CACHE.get(key)
    if cached is not None:
        return cached

    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        base_url=provider["base_url"],
        api_key=provider.get("api_key") or "not-needed",
        model=provider["model"],
        temperature=temperature,
        timeout=120,
        max_retries=2,
    )
    _MODEL_CACHE[key] = model
    return model


def clear_model_cache() -> None:
    """Descarta os modelos em cache (ex.: ao trocar de provedor ativo)."""
    _MODEL_CACHE.clear()


def test_connection(provider: dict) -> tuple[bool, str]:
    """Testa se o provedor responde e lista modelos. Retorna (ok, mensagem)."""
    import json
    import urllib.error
    import urllib.request

    base = (provider.get("base_url") or "").rstrip("/")
    if not base:
        return False, "base_url vazia"
    url = f"{base}/models"
    # User-Agent de navegador: alguns provedores (ex.: opencode/Cloudflare)
    # bloqueiam o UA padrão do urllib com erro 403/1010.
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {provider.get('api_key') or 'x'}",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Maestro/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
        if models:
            preview = ", ".join(models[:5])
            return True, f"Conectado. Modelos: {preview}" + ("..." if len(models) > 5 else "")
        return True, "Conectado, mas nenhum modelo retornado."
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"Sem conexão: {e.reason}"
    except Exception as e:  # noqa: BLE001
        return False, f"Erro: {e}"
