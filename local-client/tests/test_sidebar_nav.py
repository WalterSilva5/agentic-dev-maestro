"""Shell da aplicação: painel lateral, tela inicial e ações do topo."""
from PySide6.QtCore import Qt

from maestro_local import features
from maestro_local.gui.icons import nav_icon


def _headers(w):
    return [w.nav_list.item(i).text()
            for i in range(w.nav_list.count())
            if not w.nav_list.item(i).data(Qt.UserRole)]


def _keys(w):
    return [w.nav_list.item(i).data(Qt.UserRole)
            for i in range(w.nav_list.count())
            if w.nav_list.item(i).data(Qt.UserRole)]


def test_dashboard_e_a_tela_inicial(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert w.stack.currentWidget() is w.dashboard_view
    assert w.page_title.text() == "Dashboard"


def test_sidebar_tem_grupos(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert _headers(w) == ["PRINCIPAL", "TRABALHO", "FERRAMENTAS", "SISTEMA"]


def test_cabecalhos_nao_sao_clicaveis(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    for i in range(w.nav_list.count()):
        item = w.nav_list.item(i)
        if not item.data(Qt.UserRole):
            assert item.flags() == Qt.NoItemFlags


def test_atalhos_refletem_o_que_esta_ligado(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert w._nav_keys == _keys(w)
    antes = len(w._nav_keys)
    for k in ("dashboard", "daily", "chat"):
        features.definir(k, False)
    depois = MainWindow()._nav_keys
    assert len(depois) == antes - 3
    assert "dashboard" not in depois
    assert "settings" in depois           # a protegida continua


def test_toda_tela_do_menu_tem_icone(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    for i in range(w.nav_list.count()):
        item = w.nav_list.item(i)
        if item.data(Qt.UserRole):
            assert not item.icon().isNull(), f"sem ícone: {item.data(Qt.UserRole)}"


def test_clicar_no_menu_abre_a_tela_e_atualiza_o_titulo(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    row = w._nav_row_for("projects")
    w.nav_list.setCurrentRow(row)
    assert w.stack.currentWidget() is w.projects_view
    assert w.page_title.text() == "Projetos"


def test_sino_reflete_as_pendencias(qapp, temp_db):
    from maestro_local.db.models import Todo, get_session
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert w.notif_badge.text() == ""
    assert w.notif_badge.isVisibleTo(w) is False

    s = get_session()
    try:
        s.add(Todo(text="pendente"))
        s.commit()
    finally:
        s.close()
    w._check_todo_reminders()
    assert w.notif_badge.text() == "1"
    assert w.notif_badge.isVisibleTo(w) is True


def test_botao_reuniao_nao_encerra_reuniao_em_andamento(qapp, temp_db, monkeypatch):
    """O botão do topo abre Reuniões; parar é ação da própria tela."""
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    chamadas = []
    monkeypatch.setattr(w.transcricoes_view, "is_busy", lambda: True)
    monkeypatch.setattr(w.transcricoes_view, "toggle_record_external",
                        lambda: chamadas.append("toggle"))
    w._transcricoes_quick_toggle()
    assert chamadas == []
    assert w.stack.currentWidget() is w.transcricoes_view


def test_botao_reuniao_inicia_quando_ocioso(qapp, temp_db, monkeypatch):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    chamadas = []
    monkeypatch.setattr(w.transcricoes_view, "is_busy", lambda: False)
    monkeypatch.setattr(w.transcricoes_view, "toggle_record_external",
                        lambda: chamadas.append("toggle"))
    w._transcricoes_quick_toggle()
    assert chamadas == ["toggle"]


def test_icone_desconhecido_nao_quebra(qapp):
    assert nav_icon("chave-inexistente", "#000000").isNull()
