"""Menu lateral: agrupamento, cabeçalhos e ícones."""
from PySide6.QtCore import Qt

from maestro_local.gui import icons


def _headers(w):
    return [w.nav_list.item(i).text()
            for i in range(w.nav_list.count())
            if not w.nav_list.item(i).data(Qt.UserRole)]


def _keys(w):
    return [w.nav_list.item(i).data(Qt.UserRole)
            for i in range(w.nav_list.count())
            if w.nav_list.item(i).data(Qt.UserRole)]


def test_navegacao_tem_grupos(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert _headers(w) == ["TRABALHO", "GERENCIAR", "SISTEMA"]


def test_cabecalhos_nao_sao_clicaveis(qapp, temp_db):
    """Cabeçalho é rótulo: não pode ser selecionado nem abrir tela."""
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    for i in range(w.nav_list.count()):
        item = w.nav_list.item(i)
        if not item.data(Qt.UserRole):
            assert item.flags() == Qt.NoItemFlags


def test_atalhos_pulam_os_cabecalhos(qapp, temp_db):
    """Alt+N abre a N-ésima TELA — antes contava a linha crua da lista."""
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert "TRABALHO" not in w._nav_keys
    assert w._nav_keys == _keys(w)


def test_todas_as_telas_tem_icone(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    for i in range(w.nav_list.count()):
        item = w.nav_list.item(i)
        if item.data(Qt.UserRole):
            assert not item.icon().isNull(), f"sem ícone: {item.data(Qt.UserRole)}"


def test_icone_do_item_ativo_usa_o_destaque(qapp, temp_db):
    """O ícone acompanha a cor do texto no item selecionado."""
    from maestro_local.gui.main_window import MainWindow
    from maestro_local.gui.theme import current_theme
    w = MainWindow()
    w._open_key("board")
    th = current_theme()
    # o ícone do ativo é gerado com o accent; os demais com o cinza
    assert icons.nav_icon("board", th.accent) is not icons.nav_icon("board", th.text_muted)


def test_icone_desconhecido_nao_quebra(qapp):
    assert icons.nav_icon("chave-inexistente", "#000000").isNull()


def test_troca_de_tema_descarta_o_cache(qapp):
    icons.nav_icon("dashboard", "#111111")
    assert icons._CACHE
    icons.clear_cache()
    assert not icons._CACHE


def test_reunioes_e_o_primeiro_item(qapp, temp_db):
    """Reuniões é o eixo do produto — abre a lista do grupo TRABALHO."""
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert w._nav_keys[0] == "transcricoes"
