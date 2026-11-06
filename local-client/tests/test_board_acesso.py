"""Board acessível de imediato e menu lateral recolhível."""
from maestro_local import features
from maestro_local.db.models import BoardColumn, Project, get_session
from maestro_local.gui.main_window import MainWindow


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


def test_board_ligado_por_padrao(temp_db):
    assert features.habilitada("board") is True


def test_board_vem_logo_depois_do_dashboard(qapp, temp_db):
    w = MainWindow()
    assert w._nav_keys[:2] == ["dashboard", "board"]


def test_abrir_board_vai_direto_ao_kanban(qapp, temp_db):
    from maestro_local.config import set_active_project_id
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
    from maestro_local.config import load_config
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
    from maestro_local.gui.main_window import ResponsiveStack
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
    assert w.sidebar.width() > 300
