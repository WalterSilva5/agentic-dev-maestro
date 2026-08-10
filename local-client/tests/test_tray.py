"""Menu da bandeja: montado sob demanda, com as ações do protetor de olhos."""
import pytest
from PySide6.QtWidgets import QWidget

from maestro_local import eyecare, features


class JanelaFalsa(QWidget):
    def __init__(self):
        super().__init__()
        self.testado = False
        self.toasts = []

    def _em_reuniao(self):
        return False

    def testar_eyecare(self):
        self.testado = True

    def show_toast(self, msg, duration=2000):
        self.toasts.append(msg)


@pytest.fixture()
def tray(qapp, temp_db):
    from maestro_local.gui.tray import MaestroTray
    janela = JanelaFalsa()
    return MaestroTray(janela)


def _rotulos(menu):
    return [a.text() for a in menu.actions()]


def test_menu_traz_as_acoes_do_protetor(tray):
    tray._remontar()
    rotulos = _rotulos(tray.contextMenu())
    assert any("pausa agora" in r.lower() for r in rotulos)
    assert any("Adiar" == r for r in rotulos)


def test_protetor_desligado_some_do_menu(tray):
    features.definir("eyecare", False)
    tray._remontar()
    rotulos = " ".join(_rotulos(tray.contextMenu()))
    assert "olhos" not in rotulos.lower()
    assert "Sair" in _rotulos(tray.contextMenu())


def test_retomar_so_aparece_com_adiamento(tray):
    tray._remontar()
    assert not any("Retomar" in r for r in _rotulos(tray.contextMenu()))
    eyecare.adiar(30)
    tray._remontar()
    assert any("Retomar" in r for r in _rotulos(tray.contextMenu()))


def test_adiar_pelo_menu_silencia_a_pausa(tray):
    tray._adiar(15)
    assert eyecare.config()["adiada_ate"] is not None
    assert tray._janela.toasts        # avisa até quando


def test_fazer_agora_dispara_a_pausa(tray):
    tray._remontar()
    for a in tray.contextMenu().actions():
        if "pausa agora" in a.text().lower():
            a.trigger()
    assert tray._janela.testado is True
