"""Ícones da navegação: SVG monocromático de traço, colorido pelo tema.

Por que SVG embutido e não emoji/glifo:

- emoji são coloridos e de estilos diferentes entre si; numa lista densa eles
  competem com os rótulos e dão aspecto de brinquedo;
- glifos geométricos do Unicode (▤ ◈ ◱) parecem tipografia antiga, não ícone;
- fontes de ícone (Nerd/Font Awesome) resolveriam, mas dependeriam de a fonte
  estar instalada na máquina do usuário.

Desenhados numa grade 24×24 com traço de 2px e pontas arredondadas — o padrão
das bibliotecas de ícone de linha atuais. A cor entra por interpolação, então o
mesmo ícone serve para tema claro, escuro e para o estado selecionado.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Cada valor é o CONTEÚDO do <svg> (sem o wrapper, que é montado em _svg).
_PATHS: dict[str, str] = {
    # painéis
    "dashboard": (
        '<rect x="3" y="3" width="7" height="9" rx="1.5"/>'
        '<rect x="14" y="3" width="7" height="5" rx="1.5"/>'
        '<rect x="14" y="12" width="7" height="9" rx="1.5"/>'
        '<rect x="3" y="16" width="7" height="5" rx="1.5"/>'
    ),
    # calendário
    "daily": (
        '<rect x="3" y="5" width="18" height="16" rx="2"/>'
        '<line x1="3" y1="10" x2="21" y2="10"/>'
        '<line x1="8" y1="3" x2="8" y2="7"/>'
        '<line x1="16" y1="3" x2="16" y2="7"/>'
    ),
    # colunas do kanban
    "board": (
        '<rect x="3" y="4" width="5" height="16" rx="1.5"/>'
        '<rect x="9.5" y="4" width="5" height="11" rx="1.5"/>'
        '<rect x="16" y="4" width="5" height="7" rx="1.5"/>'
    ),
    # microfone
    "transcricoes": (
        '<rect x="9" y="3" width="6" height="11" rx="3"/>'
        '<path d="M5 11a7 7 0 0 0 14 0"/>'
        '<line x1="12" y1="18" x2="12" y2="21"/>'
    ),
    # balão de conversa
    "chat": (
        '<rect x="3" y="4" width="18" height="13" rx="2.5"/>'
        '<path d="M8 17l-2.5 4v-4"/>'
    ),
    # pasta
    "projects": (
        '<path d="M3 7.5a2 2 0 0 1 2-2h3.8l2 3H19a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5'
        'a2 2 0 0 1-2-2z"/>'
    ),
    # caixa de ferramentas
    "ferramentas": (
        '<rect x="3" y="8" width="18" height="12" rx="2"/>'
        '<path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<line x1="3" y1="13" x2="21" y2="13"/>'
    ),
    # estrela (habilidades)
    "skills": (
        '<path d="M12 3.5l2.6 5.3 5.9.9-4.2 4.1 1 5.8-5.3-2.8-5.3 2.8 1-5.8'
        '-4.2-4.1 5.9-.9z"/>'
    ),
    # ajuda
    "guide": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M9.6 9.4a2.5 2.5 0 1 1 3.4 2.4c-.7.3-1 .9-1 1.6"/>'
        '<line x1="12" y1="16.8" x2="12" y2="16.9"/>'
    ),
    # controles (configurações)
    "settings": (
        '<line x1="4" y1="6" x2="20" y2="6"/><circle cx="9" cy="6" r="2"/>'
        '<line x1="4" y1="12" x2="20" y2="12"/><circle cx="15" cy="12" r="2"/>'
        '<line x1="4" y1="18" x2="20" y2="18"/><circle cx="9" cy="18" r="2"/>'
    ),
}

_CACHE: dict[tuple[str, str, int], QIcon] = {}


def _svg(body: str, color: str) -> bytes:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    ).encode("utf-8")


def nav_icon(key: str, color: str, size: int = 18) -> QIcon:
    """Ícone da navegação na cor pedida. Vazio se a chave não tiver desenho."""
    body = _PATHS.get(key)
    if not body:
        return QIcon()
    cache_key = (key, color, size)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    renderer = QSvgRenderer(QByteArray(_svg(body, color)))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()

    icon = QIcon(pix)
    _CACHE[cache_key] = icon
    return icon


def clear_cache() -> None:
    """Descarta os ícones (ao trocar de tema as cores mudam)."""
    _CACHE.clear()
