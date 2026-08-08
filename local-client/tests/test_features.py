"""Ligar/desligar funcionalidades para enxugar a interface."""
from maestro_local import features


def test_tudo_ligado_por_padrao(temp_db):
    for f in features.FUNCIONALIDADES:
        assert features.habilitada(f.chave) is True


def test_desligar_e_religar(temp_db):
    features.definir("board", False)
    assert features.habilitada("board") is False
    features.definir("board", True)
    assert features.habilitada("board") is True


def test_configuracoes_nunca_desliga(temp_db):
    """Senão o usuário se tranca para fora — é por ali que se religa o resto."""
    features.definir(features.CHAVE_PROTEGIDA, False)
    assert features.habilitada(features.CHAVE_PROTEGIDA) is True


def test_hub_some_quando_nao_ha_ferramenta(temp_db):
    for f in features.FUNCIONALIDADES:
        if f.grupo == features.GRUPO_FERRAMENTAS:
            features.definir(f.chave, False)
    assert features.habilitada(features.CHAVE_HUB) is False


def test_hub_volta_com_uma_ferramenta(temp_db):
    for f in features.FUNCIONALIDADES:
        if f.grupo == features.GRUPO_FERRAMENTAS:
            features.definir(f.chave, False)
    features.definir("vault", True)
    assert features.habilitada(features.CHAVE_HUB) is True


def test_hub_nao_e_desligavel_diretamente(temp_db):
    """É derivado: desligar direto criaria ferramentas ativas e inalcançáveis."""
    features.definir(features.CHAVE_HUB, False)
    assert features.habilitada(features.CHAVE_HUB) is True


def test_chave_desconhecida_conta_como_ligada(temp_db):
    """Uma versão nova nunca deve esconder algo por engano."""
    assert features.habilitada("recurso-que-ainda-nao-existe") is True


def test_grupos_cobrem_todas_as_funcionalidades():
    total = sum(len(v) for v in features.por_grupo().values())
    assert total == len(features.FUNCIONALIDADES)


def test_menu_respeita_o_que_esta_ligado(qapp, temp_db):
    from maestro_local.gui.main_window import MainWindow
    antes = len(MainWindow()._nav_keys)
    for k in ("dashboard", "daily", "board"):
        features.definir(k, False)
    depois = MainWindow()._nav_keys
    assert len(depois) == antes - 3
    assert "dashboard" not in depois
    assert "settings" in depois           # a protegida continua


def test_hub_lista_so_ferramentas_ligadas(qapp, temp_db):
    from maestro_local.gui.views.tools_hub_view import ToolsHubView
    for f in features.FUNCIONALIDADES:
        if f.grupo == features.GRUPO_FERRAMENTAS:
            features.definir(f.chave, False)
    features.definir("translate", True)
    hub = ToolsHubView(lambda k: None)
    from PySide6.QtWidgets import QLabel
    rotulos = " ".join(lb.text() for lb in hub.findChildren(QLabel))
    assert "Tradutor" in rotulos
    assert "Senhas" not in rotulos


def test_lembrete_de_pendencias_respeita(qapp, temp_db, monkeypatch):
    from maestro_local.gui.main_window import MainWindow
    w = MainWindow()
    features.definir("todo_reminder", False)
    chamou = []
    monkeypatch.setattr(w.todo_reminder, "show_count", lambda n: chamou.append(n))
    w._check_todo_reminders()
    assert chamou == []
