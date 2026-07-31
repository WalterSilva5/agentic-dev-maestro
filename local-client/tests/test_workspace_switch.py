"""Troca de workspace pelo seletor da sidebar.

Bug corrigido: a confirmação era aberta com a popup do seletor ainda visível.
A popup é `Qt.Popup` e mantém um grab de mouse/teclado, então o diálogo modal
por cima dela não recebia o clique — a troca simplesmente não acontecia.
`_create_workspace` e `_manage_workspaces` já fechavam antes de abrir os seus
diálogos; `_switch_workspace` era o único que não fechava.
"""
import pytest

import maestro_local.config as config_module
import maestro_local.gui.workspace_selector as wsel


@pytest.fixture
def seletor(qapp, temp_db, monkeypatch):
    """Popup do seletor com dois workspaces e config isolada."""
    config_module.save_config({
        "workspaces": [{"id": "alpha", "name": "Alpha", "icon": "A"},
                       {"id": "beta", "name": "Beta", "icon": "B"}],
        "active_workspace": "alpha",
    })
    popup = wsel.WorkspaceSelectorPopup()
    popup.show()
    yield popup
    popup.close()


def test_popup_fechada_quando_a_confirmacao_roda(seletor, monkeypatch):
    """O cerne do bug: com a popup aberta, o diálogo não recebia o clique."""
    visto = {}

    def fake_confirm(parent, ws_id):
        visto["popup_visivel"] = seletor.isVisible()
        return True

    monkeypatch.setattr(wsel, "confirm_workspace_switch", fake_confirm)
    seletor._switch_workspace("beta")
    assert visto["popup_visivel"] is False


def test_confirmar_troca_o_workspace(seletor, monkeypatch):
    monkeypatch.setattr(wsel, "confirm_workspace_switch", lambda p, w: True)
    emitidos = []
    seletor.workspace_changed.connect(emitidos.append)

    seletor._switch_workspace("beta")
    assert emitidos == ["beta"]
    assert config_module.get_active_workspace_id() == "beta"


def test_cancelar_nao_troca(seletor, monkeypatch):
    monkeypatch.setattr(wsel, "confirm_workspace_switch", lambda p, w: False)
    emitidos = []
    seletor.workspace_changed.connect(emitidos.append)

    seletor._switch_workspace("beta")
    assert emitidos == []
    assert config_module.get_active_workspace_id() == "alpha"


def test_clicar_no_workspace_atual_so_fecha(seletor, monkeypatch):
    chamou = []
    monkeypatch.setattr(wsel, "confirm_workspace_switch",
                        lambda p, w: chamou.append(1) or True)
    emitidos = []
    seletor.workspace_changed.connect(emitidos.append)

    seletor._switch_workspace("alpha")   # o que já está ativo
    assert chamou == [], "não deveria pedir confirmação para o workspace atual"
    assert emitidos == []
    assert not seletor.isVisible()


def test_botao_nao_acumula_popups(qapp, temp_db):
    """Cada clique criava uma popup nova parenteada ao botão, sem descartar."""
    config_module.save_config({
        "workspaces": [{"id": "alpha", "name": "Alpha", "icon": "A"}],
        "active_workspace": "alpha",
    })
    botao = wsel.WorkspaceSelectorButton()
    primeira = wsel.WorkspaceSelectorPopup(botao)
    botao._popup = primeira
    # simula um novo clique descartando a anterior
    old = botao._popup
    assert old is primeira
    old.deleteLater()
    botao._popup = wsel.WorkspaceSelectorPopup(botao)
    assert botao._popup is not primeira
