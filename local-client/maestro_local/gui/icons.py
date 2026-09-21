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

import os
import tempfile

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
    # livro aberto (estudos)
    "study": (
        '<path d="M12 6.5C10.4 5 7.8 4.5 4 4.5v14c3.8 0 6.4.5 8 2 1.6-1.5 4.2-2 8-2v-14'
        'c-3.8 0-6.4.5-8 2z"/><line x1="12" y1="6.5" x2="12" y2="20.5"/>'
    ),
    # cadeado (cofre de senhas)
    "vault": (
        '<rect x="4" y="10" width="16" height="10" rx="2"/>'
        '<path d="M8 10V7a4 4 0 0 1 8 0v3"/><circle cx="12" cy="15" r="1.4"/>'
    ),
    # pilha de livros (biblioteca)
    "library": (
        '<rect x="4" y="4" width="4" height="16" rx="1"/>'
        '<rect x="10" y="4" width="4" height="16" rx="1"/>'
        '<path d="M16.6 4.9l3.4.9-3 15-3.4-.9z"/>'
    ),
    # janela de terminal (testador de API)
    "apitester": (
        '<rect x="3" y="4" width="18" height="16" rx="2"/>'
        '<polyline points="7,9 10,12 7,15"/><line x1="12" y1="15" x2="17" y2="15"/>'
    ),
    # lâmpada (base de conhecimento)
    "kb": (
        '<path d="M9.5 18h5"/><path d="M10.5 21h3"/>'
        '<path d="M12 3a6 6 0 0 0-3.6 10.8c.5.4.9 1 .9 1.7V16h5.4v-.5'
        'c0-.7.4-1.3.9-1.7A6 6 0 0 0 12 3z"/>'
    ),
    # chip (memória agentic)
    "memory": (
        '<rect x="7" y="7" width="10" height="10" rx="2"/>'
        '<path d="M10 3v2M14 3v2M10 19v2M14 19v2M3 10h2M3 14h2M19 10h2M19 14h2"/>'
    ),
    # balão de fala (praticar inglês)
    "english": (
        '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v7'
        'a2.5 2.5 0 0 1-2.5 2.5H10l-4 4v-4H6.5A2.5 2.5 0 0 1 4 12.5z"/>'
    ),
    # idiomas (tradutor)
    "translate": (
        '<path d="M4 6h9"/><path d="M8.5 6c0 5-2 8.5-5.5 10.5"/>'
        '<path d="M6 10.5c1.2 2.6 3.2 4.4 5.5 5.5"/>'
        '<line x1="12.5" y1="20" x2="17" y2="9"/><line x1="15" y1="20" x2="19.5" y2="9"/>'
        '<line x1="13.8" y1="17" x2="18.7" y2="17"/>'
    ),
    # sino (notificações)
    "bell": (
        '<path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6"/>'
        '<path d="M10.5 20a1.8 1.8 0 0 0 3 0"/>'
    ),
    # casa (início)
    "home": (
        '<path d="M4 11l8-6.5 8 6.5"/>'
        '<path d="M6 10v9a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-9"/>'
    ),
    # lupa (busca)
    "search": (
        '<circle cx="11" cy="11" r="6"/><line x1="15.5" y1="15.5" x2="20" y2="20"/>'
    ),
    # olho (pausa para os olhos)
    "eye": (
        '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>'
        '<circle cx="12" cy="12" r="3"/>'
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

# --- marca de seleção dos checkboxes -----------------------------------------
#
# O QSS precisa de um ARQUIVO para `image:`. E precisamos dele porque, assim que
# o indicador recebe `background-color`, o Qt deixa de desenhar o ✓ nativo — o
# checkbox marcado virava um quadrado colorido sólido, sem sinal de marcação.
#
# Os arquivos vão para um diretório temporário do processo, não para a pasta de
# dados do usuário: são cache descartável e não devem sujar nada permanente.
_DIR_CHECK: str | None = None
_CACHE_CHECK: dict[tuple[str, int], str] = {}

_CHECK_SVG = '<polyline points="4,12.5 9,17.5 20,6.5"/>'


def caminho_do_check(cor: str, tamanho: int = 16) -> str:
    """Caminho de um PNG com o ✓ na cor pedida, pronto para `image:` no QSS."""
    global _DIR_CHECK
    chave = (cor, tamanho)
    existente = _CACHE_CHECK.get(chave)
    if existente and os.path.exists(existente):
        return existente

    if _DIR_CHECK is None:
        _DIR_CHECK = tempfile.mkdtemp(prefix="maestro-check-")

    renderer = QSvgRenderer(QByteArray(_svg(_CHECK_SVG, cor)))
    pix = QPixmap(tamanho, tamanho)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()

    destino = os.path.join(_DIR_CHECK, f"check-{abs(hash(chave))}.png")
    pix.save(destino, "PNG")
    _CACHE_CHECK[chave] = destino
    return destino


# --- ícone do aplicativo (bandeja / janela) ----------------------------------
#
# Cor fixa, não a do tema: o fundo da bandeja é do painel do sistema, que o
# programa não conhece. Um "M" claro sobre um quadrado teal se lê tanto em
# painel claro quanto escuro.
_APP_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<rect x="1" y="1" width="22" height="22" rx="6" fill="#0D9488"/>'
    '<path d="M6 17V8l6 6 6-6v9" fill="none" stroke="#FFFFFF" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
_ICONE_APP: QIcon | None = None


def icone_do_app() -> QIcon:
    """Ícone do programa, em vários tamanhos (a bandeja escolhe o que couber)."""
    global _ICONE_APP
    if _ICONE_APP is not None:
        return _ICONE_APP
    renderer = QSvgRenderer(QByteArray(_APP_SVG.encode("utf-8")))
    icon = QIcon()
    for tamanho in (16, 22, 24, 32, 48, 64):
        pix = QPixmap(tamanho, tamanho)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pix)
    _ICONE_APP = icon
    return icon
