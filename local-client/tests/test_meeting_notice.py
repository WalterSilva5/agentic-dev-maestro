"""Reunião em curso: suspende a pausa para os olhos e avisa o SO a cada 15 min.

O aviso é do **sistema operacional** (bandeja/notify-send), nunca o toast da
interface — durante a reunião a tela não deve ser invadida pelo app.
"""
import pytest


@pytest.fixture
def janela(qapp, temp_db, monkeypatch):
    from relay.gui.main_window import MainWindow

    w = MainWindow()
    # nenhum teste deve disparar notificação real no X/DBus
    monkeypatch.setattr(w, "_notificar_sistema", lambda *a, **k: None)
    yield w
    w.close()


def test_reuniao_marca_estado_e_suspende_pausa(janela):
    assert janela._em_reuniao() is False

    janela._on_recording_state(True, 0)
    assert janela._em_reuniao() is True

    janela._on_recording_state(False, 0)
    assert janela._em_reuniao() is False


def test_timer_de_aviso_liga_e_desliga_com_a_gravacao(janela):
    assert janela._meeting_notice_timer.isActive() is False

    janela._on_recording_state(True, 0)
    assert janela._meeting_notice_timer.isActive() is True

    janela._on_recording_state(False, 0)
    assert janela._meeting_notice_timer.isActive() is False


def test_aviso_de_15_minutos_vai_para_o_sistema(janela, monkeypatch):
    enviados = []
    monkeypatch.setattr(janela, "_notificar_sistema", lambda t_, m: enviados.append((t_, m)))
    toast = []
    monkeypatch.setattr(janela, "show_toast", lambda *a, **k: toast.append(a))

    janela._on_recording_state(True, 15 * 60)
    janela._notificar_reuniao_em_curso()

    assert enviados == [("Reunião em progresso", "Em andamento há 15 min")]
    assert toast == []          # não usa a notificação da interface


def test_aviso_para_quando_a_reuniao_termina(janela, monkeypatch):
    enviados = []
    monkeypatch.setattr(janela, "_notificar_sistema", lambda t_, m: enviados.append((t_, m)))
    janela._on_recording_state(False, 0)

    janela._notificar_reuniao_em_curso()

    assert enviados == []
    assert janela._meeting_notice_timer.isActive() is False


def test_reuniao_iniciada_fecha_a_pausa_aberta(janela):
    class _PausaFalsa:
        encerrou = False

        def encerrar(self):
            self.encerrou = True

    pausa = _PausaFalsa()
    janela._eyecare_overlay = pausa

    janela._on_recording_state(True, 0)

    assert pausa.encerrou is True
    assert janela._eyecare_overlay is None


def test_pausa_nao_aparece_durante_reuniao(janela, monkeypatch):
    """`_maybe_show_eyecare` respeita o estado de reunião."""
    from relay import eyecare

    monkeypatch.setattr(eyecare, "devida", lambda **k: not k.get("em_reuniao"))

    janela._on_recording_state(True, 0)
    janela._maybe_show_eyecare()
    assert janela._eyecare_overlay is None

    janela._on_recording_state(False, 0)
    janela._maybe_show_eyecare()
    # fora da reunião a pausa é criada (não abrimos de verdade no teste)
    assert janela._eyecare_overlay is not None
    janela._eyecare_overlay.encerrar()
    janela._eyecare_overlay = None


def test_sessao_de_estudo_nao_avisa_como_reuniao(janela, monkeypatch):
    enviados = []
    monkeypatch.setattr(janela, "_notificar_sistema", lambda t_, m: enviados.append((t_, m)))
    janela.transcricoes_view.kind_combo.setCurrentIndex(
        janela.transcricoes_view.kind_combo.findData("study"))
    janela._on_recording_state(True, 15 * 60)

    janela._notificar_reuniao_em_curso()

    assert enviados == []
