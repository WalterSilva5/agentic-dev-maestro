"""Board acessível de imediato e menu lateral recolhível."""
from relay import features
from relay.db.models import BoardColumn, Project, get_session
from relay.gui.main_window import MainWindow


def _projeto_com_coluna():
    s = get_session()
    p = Project(name="P", key="P")
    s.add(p)
    s.flush()
    pid = p.id
    s.add(BoardColumn(project_id=pid, name="A fazer", order=0))
    s.commit()
    s.close()
    return pid


def test_board_desligado_por_padrao_no_desktop(temp_db):
    # Board vive na versão web; no desktop vem desligado (reativável em
    # Configurações → Funcionalidades).
    assert features.habilitada("board") is False


def test_nav_minimo_do_desktop(qapp, temp_db):
    from relay.gui.main_window import MainWindow
    w = MainWindow()
    assert w._nav_keys == ["transcricoes", "chat", "vault", "guide", "settings"]


def test_abrir_board_vai_direto_ao_kanban(qapp, temp_db):
    from relay.config import set_active_project_id
    pid = _projeto_com_coluna()
    set_active_project_id(pid)
    w = MainWindow()
    w._open_key("board")
    assert w.stack.currentWidget() is w.board_view
    assert w.board_view.project_id == pid
    assert w.board_view.empty_widget.isVisibleTo(w) is False


def test_toggle_sidebar_oculta_e_mostra(qapp, temp_db):
    w = MainWindow()
    w.show()
    assert w.sidebar.isVisible()
    w._toggle_sidebar()
    assert not w.sidebar.isVisible()
    assert "Mostrar" in w.menu_toggle_btn.toolTip()
    w._toggle_sidebar()
    assert w.sidebar.isVisible()
    assert "Ocultar" in w.menu_toggle_btn.toolTip()


def test_sidebar_oculta_persiste_entre_sessoes(qapp, temp_db):
    from relay.config import load_config
    w = MainWindow()
    w._toggle_sidebar(False)
    assert load_config().get("settings", {}).get("sidebar_visible") is False
    w2 = MainWindow()
    assert not w2.sidebar.isVisible()


def test_botao_menu_tem_destaque(qapp, temp_db):
    w = MainWindow()
    assert w.menu_toggle_btn.objectName() == "menuToggle"
    assert (w.menu_toggle_btn.width(), w.menu_toggle_btn.height()) == (34, 34)


def test_stack_usa_minimo_da_pagina_atual(qapp, temp_db):
    from relay.gui.main_window import ResponsiveStack
    w = MainWindow()
    assert isinstance(w.stack, ResponsiveStack)
    w._open_key("dashboard")
    assert w.stack.minimumSizeHint().width() == w.dashboard_view.minimumSizeHint().width()
    w._open_key("transcricoes")
    assert w.stack.minimumSizeHint().width() == w.transcricoes_view.minimumSizeHint().width()


def test_sidebar_expande_em_janela_estreita(qapp, temp_db):
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    w._splitter.setSizes([420, 480])
    assert w.sidebar.width() >= 280


def test_botao_web_existe_e_abre_navegador(qapp, temp_db, monkeypatch):
    from PySide6.QtCore import QUrl

    from relay.gui.main_window import MainWindow
    abertos = []
    monkeypatch.setattr(
        "PySide6.QtGui.QDesktopServices.openUrl",
        lambda url: abertos.append(url.toString()),
    )
    w = MainWindow()
    assert "versão web" in w.web_btn.toolTip()
    # atalho com destaque: deixou de ser ícone discreto e virou botão primário
    assert w.web_btn.objectName() == "webShortcut"
    assert w.web_btn.text() == "Abrir web"
    w.web_btn.click()
    assert abertos == [f"http://127.0.0.1:{w.api_port}/"]


def test_initial_view_alias(qapp, temp_db):
    from relay.gui.main_window import MainWindow
    w = MainWindow(initial_view="reunioes")
    assert w.stack.currentWidget() is w.transcricoes_view
    w2 = MainWindow(initial_view="vault")
    assert w2.stack.currentWidget() is not None
    assert w2._last_screen == "vault"
