"""Pausa para os olhos (estilo SafeEyes): ciclo, adiamento e reuniões."""
from datetime import datetime, timedelta

from maestro_local import eyecare, features

AGORA = datetime(2026, 8, 1, 10, 0, 0)


def test_primeira_execucao_nao_interrompe(temp_db):
    """Abrir o programa não pode disparar uma pausa de cara."""
    assert eyecare.devida(AGORA) is False


def test_antes_do_intervalo_nao_e_devida(temp_db):
    eyecare.marcar_pausa_feita(AGORA)
    assert eyecare.devida(AGORA + timedelta(minutes=19)) is False


def test_depois_do_intervalo_e_devida(temp_db):
    eyecare.marcar_pausa_feita(AGORA)
    assert eyecare.devida(AGORA + timedelta(minutes=21)) is True


def test_reuniao_segura_a_pausa(temp_db):
    """O pedido central: não aparecer no meio de reunião."""
    eyecare.marcar_pausa_feita(AGORA)
    depois = AGORA + timedelta(minutes=21)
    assert eyecare.devida(depois, em_reuniao=True) is False


def test_pausa_segurada_nao_e_perdida(temp_db):
    """Terminada a reunião, ela aparece — não pula o ciclo."""
    eyecare.marcar_pausa_feita(AGORA)
    depois = AGORA + timedelta(minutes=21)
    eyecare.devida(depois, em_reuniao=True)
    assert eyecare.devida(depois, em_reuniao=False) is True


def test_adiar_silencia_pelo_periodo(temp_db):
    eyecare.marcar_pausa_feita(AGORA)
    devida_em = AGORA + timedelta(minutes=21)
    eyecare.adiar(5, devida_em)
    assert eyecare.devida(devida_em + timedelta(minutes=1)) is False
    assert eyecare.devida(devida_em + timedelta(minutes=6)) is True


def test_fazer_a_pausa_reinicia_o_ciclo(temp_db):
    eyecare.marcar_pausa_feita(AGORA)
    depois = AGORA + timedelta(minutes=21)
    eyecare.marcar_pausa_feita(depois)
    assert eyecare.devida(depois + timedelta(minutes=1)) is False


def test_fazer_a_pausa_cancela_o_adiamento(temp_db):
    eyecare.marcar_pausa_feita(AGORA)
    eyecare.adiar(30, AGORA)
    eyecare.marcar_pausa_feita(AGORA)
    assert eyecare.config()["adiada_ate"] is None


def test_valores_ficam_dentro_dos_limites(temp_db):
    eyecare.definir(intervalo_min=9999, duracao_seg=0, adiar_min=999)
    c = eyecare.config()
    assert c["intervalo_min"] == 180
    assert c["duracao_seg"] == 5
    assert c["adiar_min"] == 60


def test_configuracao_corrompida_cai_no_padrao(temp_db):
    from maestro_local.config import load_config, save_config
    cfg = load_config()
    cfg.setdefault("settings", {})["eyecare"] = {
        "intervalo_min": "abc", "ultima_pausa": "não é data"}
    save_config(cfg)
    c = eyecare.config()
    assert c["intervalo_min"] == eyecare.PADROES["intervalo_min"]
    assert c["ultima_pausa"] is None


def test_estado_sobrevive_ao_reinicio(temp_db):
    """Fechar o programa não pode zerar o ciclo nem cancelar um adiamento."""
    eyecare.marcar_pausa_feita(AGORA)
    ate = eyecare.adiar(10, AGORA)
    lido = eyecare.config()
    assert lido["ultima_pausa"] == AGORA
    assert lido["adiada_ate"] == ate.replace(microsecond=0)


def test_e_desligavel_nas_funcionalidades(temp_db):
    assert features.habilitada("eyecare") is True
    features.definir("eyecare", False)
    assert features.habilitada("eyecare") is False


def test_janela_conta_regressivamente(qapp, temp_db):
    from maestro_local.gui.eyecare_break import EyecareBreak
    from PySide6.QtWidgets import QWidget
    host = QWidget()
    br = EyecareBreak(host, duracao_seg=3)
    assert br.segundos_restantes() == 3
    br._on_tick()
    assert br.segundos_restantes() == 2


def test_pular_conta_como_pausa_feita(qapp, temp_db):
    """Pular reinicia o ciclo em vez de insistir logo em seguida."""
    from maestro_local.gui.eyecare_break import EyecareBreak
    from PySide6.QtWidgets import QWidget
    host = QWidget()
    br = EyecareBreak(host, duracao_seg=20)
    recebido = []
    br.concluida.connect(lambda: recebido.append(True))
    br._on_pular()
    assert recebido == [True]


def test_cancelar_adiamento_libera_a_pausa(temp_db):
    """Ação 'Retomar agora' da bandeja."""
    eyecare.marcar_pausa_feita(AGORA)
    devida_em = AGORA + timedelta(minutes=21)
    eyecare.adiar(30, devida_em)
    assert eyecare.devida(devida_em) is False
    eyecare.cancelar_adiamento()
    assert eyecare.devida(devida_em) is True


def test_cancelar_adiamento_nao_mexe_no_ciclo(temp_db):
    eyecare.marcar_pausa_feita(AGORA)
    eyecare.adiar(30, AGORA)
    eyecare.cancelar_adiamento()
    assert eyecare.config()["ultima_pausa"] is not None


def test_pausa_e_janela_separada(qapp, temp_db):
    """O pedido: sair de dentro da janela do Maestro."""
    from maestro_local.gui.eyecare_break import EyecareBreak
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget
    host = QWidget()
    br = EyecareBreak(host, duracao_seg=5)
    assert br.isWindow()
    assert br.windowFlags() & Qt.FramelessWindowHint


def test_todos_os_monitores_sao_cobertos(qapp, temp_db):
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QWidget

    from maestro_local.gui.eyecare_break import EyecareBreak
    host = QWidget()
    br = EyecareBreak(host, duracao_seg=5)
    br.iniciar()
    # a própria janela cobre uma tela; as demais recebem uma cobertura
    assert len(br._coberturas) == len(QGuiApplication.screens()) - 1
    br._encerrar()
    assert br._coberturas == []


def test_esc_adia_em_vez_de_so_fechar(qapp, temp_db):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QWidget

    from maestro_local.gui.eyecare_break import EyecareBreak
    host = QWidget()
    br = EyecareBreak(host, duracao_seg=20)
    adiado = []
    br.adiada.connect(lambda: adiado.append(True))
    br.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    assert adiado == [True]


def test_dicas_nao_repetem_em_pausas_seguidas(temp_db):
    vistas = [eyecare.proxima_dica() for _ in range(len(eyecare.DICAS))]
    assert len(set(vistas)) == len(eyecare.DICAS)   # o ciclo passa por todas


def test_rotacao_de_dicas_da_a_volta(temp_db):
    for _ in range(len(eyecare.DICAS)):
        eyecare.proxima_dica()
    assert eyecare.proxima_dica() == eyecare.DICAS[0]


def test_rotacao_sobrevive_ao_reinicio(temp_db):
    primeira = eyecare.proxima_dica()
    # nova leitura da configuração = como se o programa tivesse reaberto
    assert eyecare.proxima_dica() != primeira


def test_indice_corrompido_nao_quebra_a_pausa(temp_db):
    from maestro_local.config import load_config, save_config
    cfg = load_config()
    cfg.setdefault("settings", {}).setdefault("eyecare", {})["dica"] = "xyz"
    save_config(cfg)
    assert eyecare.proxima_dica() in eyecare.DICAS


def test_a_janela_da_pausa_mostra_uma_dica(qapp, temp_db):
    from PySide6.QtWidgets import QWidget

    from maestro_local.gui.eyecare_break import EyecareBreak
    br = EyecareBreak(QWidget(), duracao_seg=5)
    assert br.dica.text() in eyecare.DICAS


def test_dica_longa_nao_fica_cortada(qapp, temp_db):
    """wordWrap sem heightForWidth cortava a última linha da dica."""
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QWidget

    from maestro_local.gui.eyecare_break import EyecareBreak
    # começa pela dica mais longa, que é onde o corte aparecia
    mais_longa = max(range(len(eyecare.DICAS)), key=lambda i: len(eyecare.DICAS[i]))
    from maestro_local.config import load_config, save_config
    cfg = load_config()
    cfg.setdefault("settings", {}).setdefault("eyecare", {})["dica"] = mais_longa
    save_config(cfg)

    br = EyecareBreak(QWidget(), duracao_seg=5)
    br._ajustar_dica(QGuiApplication.primaryScreen())
    largura = br.dica.width()
    assert br.dica.minimumHeight() >= br.dica.heightForWidth(largura)


def test_dica_cabe_em_tela_estreita(qapp, temp_db):
    from PySide6.QtWidgets import QWidget

    from maestro_local.gui.eyecare_break import EyecareBreak

    class TelaFalsa:
        def geometry(self):
            from PySide6.QtCore import QRect
            return QRect(0, 0, 500, 400)

    br = EyecareBreak(QWidget(), duracao_seg=5)
    br._ajustar_dica(TelaFalsa())
    assert br.dica.width() <= 500 - 80
