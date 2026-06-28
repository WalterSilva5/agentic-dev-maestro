"""Provedores de IA compatíveis com OpenAI (LM Studio, opencode, etc.).

Todos os provedores expõem o mesmo formato /v1/chat/completions, então
basta variar base_url + api_key + model.
"""
from __future__ import annotations

from maestro_local.config import get_active_ai_provider

# Provedores padrão sugeridos na primeira execução. api_key vazio = o usuário preenche.
DEFAULT_PROVIDERS = [
    {
        "id": "lmstudio",
        "name": "LM Studio (local)",
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "model": "",
    },
    {
        "id": "opencode",
        "name": "opencode",
        "base_url": "https://api.opencode.ai/v1",
        "api_key": "",
        "model": "",
    },
]


class ProviderNotConfigured(Exception):
    pass


def build_chat_model(provider: dict | None = None, temperature: float = 0.3):
    """Constrói um ChatOpenAI a partir do provedor ativo (ou informado).

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

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=provider["base_url"],
        api_key=provider.get("api_key") or "not-needed",
        model=provider["model"],
        temperature=temperature,
        timeout=120,
        max_retries=1,
    )


def test_connection(provider: dict) -> tuple[bool, str]:
    """Testa se o provedor responde e lista modelos. Retorna (ok, mensagem)."""
    import json
    import urllib.error
    import urllib.request

    base = (provider.get("base_url") or "").rstrip("/")
    if not base:
        return False, "base_url vazia"
    url = f"{base}/models"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {provider.get('api_key') or 'x'}",
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
