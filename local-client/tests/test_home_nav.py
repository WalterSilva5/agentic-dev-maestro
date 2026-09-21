"""Tela inicial (home): lançador por seções, sem painel lateral."""
from maestro_local import features
from maestro_local.gui.icons import nav_icon


def test_home_e_a_tela_inicial(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert w.stack.currentWidget() is w.home_view
    # o painel lateral deixou de existir
    assert not hasattr(w, "nav_list")
    assert not hasattr(w, "sidebar")


def test_home_mostra_um_cartao_por_funcionalidade_ligada(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    chaves = {c._chave for c in w.home_view.cards}
    assert "transcricoes" in chaves
    assert "dashboard" in chaves
    assert "settings" in chaves        # a protegida precisa estar acessível
    # board é padrao=False (escondido por enquanto)
    assert "board" not in chaves
    # um cartão para cada atalho visível
    assert chaves == set(w._nav_keys)


def test_reunioes_e_o_primeiro_atalho(qapp, temp_db):
    """Reuniões é o eixo do produto — primeiro cartão da home."""
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    assert w._nav_keys[0] == "transcricoes"


def test_atalhos_refletem_o_que_esta_ligado(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    antes = len(MainWindow()._nav_keys)
    for k in ("dashboard", "daily", "chat"):
        features.definir(k, False)
    depois = MainWindow()._nav_keys
    assert len(depois) == antes - 3
    assert "dashboard" not in depois
    assert "settings" in depois           # a protegida continua


def test_toda_secao_tem_icone(qapp, temp_db):
    """Cada cartão da home precisa de um desenho em icons.py."""
    from maestro_local.gui.views.home_view import SECOES
    for _, chaves in SECOES:
        for chave in chaves:
            assert not nav_icon(chave, "#000000").isNull(), f"sem ícone: {chave}"


def test_icone_desconhecido_nao_quebra(qapp):
    assert nav_icon("chave-inexistente", "#000000").isNull()


def test_troca_de_tema_descarta_o_cache(qapp):
    from maestro_local.gui import icons
    icons.nav_icon("dashboard", "#111111")
    assert icons._CACHE
    icons.clear_cache()
    assert not icons._CACHE


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
