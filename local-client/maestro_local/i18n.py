"""Internacionalização simples baseada em catálogo PT->EN.

O idioma-fonte do código é o português. `t("texto em pt")` retorna a
tradução em inglês quando o idioma ativo é "en"; caso contrário devolve
o próprio texto. A troca de idioma exige reiniciar o app (as telas são
construídas com o idioma vigente no startup).
"""
from __future__ import annotations

SUPPORTED = {"pt": "Português", "en": "English"}
DEFAULT_LANG = "pt"

_lang = DEFAULT_LANG


def init_language() -> None:
    """Carrega o idioma salvo na config (chamar no startup)."""
    global _lang
    try:
        from maestro_local.config import get_language
        code = get_language()
        if code in SUPPORTED:
            _lang = code
    except Exception:  # noqa: BLE001
        _lang = DEFAULT_LANG


def current_language() -> str:
    return _lang


def set_runtime_language(code: str) -> None:
    global _lang
    if code in SUPPORTED:
        _lang = code


def t(text: str) -> str:
    """Traduz `text` (em pt) para o idioma ativo."""
    if _lang == "pt":
        return text
    from maestro_local.i18n_catalog import CATALOG
    return CATALOG.get(_lang, {}).get(text, text)


def tf(text: str, **kwargs) -> str:
    """Traduz e formata: t(text).format(**kwargs)."""
    return t(text).format(**kwargs)
