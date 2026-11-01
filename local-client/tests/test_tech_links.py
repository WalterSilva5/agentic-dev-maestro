"""Tela de atalhos para sites de novidades de tecnologia."""
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from maestro_local.gui.views.tech_links_view import (
    DEFAULT_LINKS,
    TechLinksView,
    _LinkCard,
    carregar_links,
    salvar_links,
)


def test_links_padrao():
    nomes = {l["nome"] for l in DEFAULT_LINKS}
    for esperado in ("daily.dev", "Hacker News", "GitHub Trending", "Roadmap.sh",
                     "The Pragmatic Engineer", "DEV Community"):
        assert esperado in nomes
    assert all(l.get("categoria") for l in DEFAULT_LINKS)


def test_carregar_sem_config_usa_padrao(temp_db):
    links = carregar_links()
    assert {l["nome"] for l in links} == {l["nome"] for l in DEFAULT_LINKS}


def test_salvar_e_carregar(temp_db):
    links = [{"nome": "X", "url": "https://x.com", "categoria": "Notícias",
              "descricao": ""}]
    salvar_links(links)
    assert carregar_links() == links


def test_view_monta(qapp, temp_db):
    v = TechLinksView()
    assert v is not None


def test_clique_abre_no_navegador(qapp, monkeypatch):
    import webbrowser

    abertos = []
    monkeypatch.setattr(webbrowser, "open", lambda url: abertos.append(url))

    card = _LinkCard({"nome": "Site", "url": "https://example.com", "descricao": "d"},
                     on_remove=lambda link: None)
    ev = QMouseEvent(QEvent.MouseButtonPress, QPointF(1, 1),
                     Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    card.mousePressEvent(ev)
    assert abertos == ["https://example.com"]


def test_remover_um_link(qapp, temp_db):
    v = TechLinksView()
    antes = len(v._links)
    v._remover(v._links[0])
    assert len(v._links) == antes - 1
    assert len(carregar_links()) == antes - 1
