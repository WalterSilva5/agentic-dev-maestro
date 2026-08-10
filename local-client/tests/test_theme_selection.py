"""Escolha e persistência de tema (claro / escuro / hacker)."""
from maestro_local import config
from maestro_local.gui import theme


def test_tres_temas_registrados():
    assert set(theme.TEMAS) == {"light", "dark", "hacker"}


def test_rodizio_volta_ao_inicio():
    assert theme.proximo_tema("light") == "dark"
    assert theme.proximo_tema("dark") == "hacker"
    assert theme.proximo_tema("hacker") == "light"


def test_rodizio_tolera_nome_invalido():
    assert theme.proximo_tema("inexistente") == "dark"


def test_nome_do_tema():
    assert theme.nome_do_tema(theme.HACKER) == "hacker"
    assert theme.nome_do_tema(theme.LIGHT) == "light"


def test_tema_e_persistido(temp_db):
    """Antes o tema não era salvo e voltava ao claro a cada abertura."""
    assert config.get_theme_name() == "light"
    config.set_theme_name("hacker")
    assert config.get_theme_name() == "hacker"


def test_hacker_usa_fonte_monoespacada():
    assert "mono" in theme.HACKER.font_family.lower()
    assert "mono" not in theme.LIGHT.font_family.lower()


def test_hacker_separa_sucesso_do_accent():
    """O accent é verde; sucesso verde também ficaria indistinguível."""
    assert theme.HACKER.accent != theme.HACKER.success


def test_folha_de_estilo_usa_a_fonte_do_tema():
    css = theme.build_stylesheet(theme.HACKER)
    assert theme.HACKER.font_family in css
