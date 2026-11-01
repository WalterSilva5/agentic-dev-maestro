"""Tela de atalhos para sites de novidades de tecnologia."""
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from maestro_local.gui.views.tech_links_view import LINKS, _LinkCard, TechLinksView


def test_links_definidos():
    nomes = [n for n, _, _ in LINKS]
    assert "daily.dev" in nomes
    assert "GitHub Trending" in nomes
    assert "Roadmap.sh" in nomes
    assert len(LINKS) >= 5


def test_view_monta(qapp):
    v = TechLinksView()
    assert v is not None


def test_clique_abre_no_navegador(qapp, monkeypatch):
    import webbrowser

    abertos = []
    monkeypatch.setattr(webbrowser, "open", lambda url: abertos.append(url))

    card = _LinkCard("Site", "https://example.com", "descrição")
    ev = QMouseEvent(QEvent.MouseButtonPress, QPointF(1, 1),
                     Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    card.mousePressEvent(ev)
    assert abertos == ["https://example.com"]
