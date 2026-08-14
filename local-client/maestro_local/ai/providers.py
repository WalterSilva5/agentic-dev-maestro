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


def build_chat_model(provider: dict | None = None, temperature: float = 0.3,
                     timeout: int = 120):
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
        int(timeout),          # o timeout faz parte da identidade do modelo
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
        timeout=timeout,
        max_retries=2,
    )
    _MODEL_CACHE[key] = model
    return model


def clear_model_cache() -> None:
    """Descarta os modelos em cache (ex.: ao trocar de provedor ativo)."""
    _MODEL_CACHE.clear()


def test_connection(provider: dict) -> tuple[bool, str]:
    """Testa se o provedor responde. Retorna (ok, mensagem).

    Mantido para quem só quer o resultado; a lista de modelos vem de
    `listar_modelos`.
    """
    ok, msg, _ = listar_modelos(provider)
    return ok, msg


def listar_modelos(provider: dict) -> tuple[bool, str, list[str]]:
    """Testa o provedor e devolve (ok, mensagem, modelos).

    A lista completa importa: o nome do modelo é digitado à mão na
    configuração e errar um caractere só aparece depois, como falha de
    chamada. Ver o nome exato e copiar evita isso.
    """
    import json
    import urllib.error
    import urllib.request

    base = (provider.get("base_url") or "").rstrip("/")
    if not base:
        return False, "base_url vazia", []
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
        models = sorted({m.get("id") for m in data.get("data", []) if m.get("id")})
        if models:
            return True, f"Conectado. {len(models)} modelo(s) disponível(is).", models
        return True, "Conectado, mas nenhum modelo retornado.", []
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}", []
    except urllib.error.URLError as e:
        return False, f"Sem conexão: {e.reason}", []
    except Exception as e:  # noqa: BLE001
        return False, f"Erro: {e}", []


def verificar_modelo(provider: dict, modelo: str) -> tuple[bool, str]:
    """Confirma se o modelo realmente responde. Devolve (ok, mensagem).

    Por que existe: `/models` é um catálogo, não uma lista de permissões. Ele
    devolve só id/object/created/owned_by — nada sobre região, plano ou opt-in.
    Um modelo listado pode ser recusado na chamada (403 RegionError, 401 "not
    supported"), e sem esta verificação a falha só aparecia muito depois, no
    meio de uma reunião, como "Live extract falhou".

    Faz uma chamada real, mínima (um token), então custa. Por isso é acionada
    por botão, nunca sozinha.
    """
    import json
    import urllib.error
    import urllib.request

    base = (provider.get("base_url") or "").rstrip("/")
    if not base:
        return False, "base_url vazia"
    if not (modelo or "").strip():
        return False, "nenhum modelo informado"

    corpo = json.dumps({
        "model": modelo,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=corpo, method="POST", headers={
            "Authorization": f"Bearer {provider.get('api_key') or 'x'}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Maestro/1.0",
            "Accept": "application/json",
        })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return True, f"{modelo} respondeu."
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {_mensagem_de_erro(e)}"
    except urllib.error.URLError as e:
        return False, f"Sem conexão: {e.reason}"
    except Exception as e:  # noqa: BLE001
        return False, f"Erro: {e}"


def _mensagem_de_erro(erro) -> str:
    """Texto que o provedor mandou, e não só o código do HTTP.

    A recusa útil vem no corpo — "requires explicit opt in" com o link, ou
    "Model X is not supported". Mostrar apenas "HTTP 403" esconderia o que o
    usuário precisa saber para resolver.
    """
    import json
    try:
        dados = json.loads(erro.read())
    except Exception:  # noqa: BLE001
        return getattr(erro, "reason", "") or "sem detalhe"
    if isinstance(dados, dict):
        alvo = dados.get("error", dados)
        if isinstance(alvo, dict):
            return str(alvo.get("message") or alvo.get("mensagem") or alvo)
        if alvo:
            return str(alvo)
    return str(dados)
