"""Encerramento sem abortar o processo.

Sair com uma QThread em execução faz o destrutor do QThread disparar qFatal —
o processo morre com SIGABRT e core dump. Estes testes cobrem a parada dos
workers; o caminho de saída dura (os._exit) é verificado por subprocesso, já
que por definição encerra o interpretador.
"""
import subprocess
import sys
import textwrap
import time

from PySide6.QtCore import QThread


class _Travado(QThread):
    """Simula uma chamada de IA travada (não é interrompível)."""

    def run(self):
        time.sleep(30)


def test_stop_all_sem_workers_reporta_sucesso(qapp):
    from maestro_local.transcricoes.agent_service import MeetingAgentService
    svc = MeetingAgentService()
    assert svc.stop_all(msecs=100) is True


def test_stop_all_reporta_falha_com_worker_travado(qapp):
    """Quem chama precisa saber que sobrou thread viva — é o que evita o abort."""
    from maestro_local.transcricoes.agent_service import MeetingAgentService
    svc = MeetingAgentService()
    stuck = _Travado()
    stuck.start()
    try:
        time.sleep(0.2)
        svc._live_extractor = stuck
        assert svc.stop_all(msecs=100) is False
    finally:
        stuck.terminate()
        stuck.wait(2000)


def test_view_shutdown_para_o_que_da_e_reporta(meetings_view):
    v = meetings_view
    assert v.shutdown(msecs=100) is True   # nada rodando
    assert v._live_transcriber is None
    assert v._session is None


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)],
                          capture_output=True, text=True, timeout=90)


def test_fechar_com_worker_travado_nao_aborta():
    """Regressão do crash relatado: SIGABRT (-6/134) ao fechar durante IA."""
    proc = _run("""
        import os, time, tempfile, pathlib
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QThread
        app = QApplication([])
        from maestro_local.db import models
        models.switch_db(str(pathlib.Path(tempfile.mkdtemp())/"t.db"))
        from maestro_local.gui.main_window import MainWindow
        w = MainWindow(); w._open_key("transcricoes")
        class Travado(QThread):
            def run(self): time.sleep(30)
        stuck = Travado(); stuck.start(); time.sleep(0.3)
        w.transcricoes_view.agent._live_extractor = stuck
        w.close()
    """)
    assert proc.returncode == 0, (
        f"esperava saida limpa, veio {proc.returncode} "
        f"(-6/134 = SIGABRT do QThread destruido rodando)\n{proc.stderr[-500:]}")


def test_fechar_sem_nada_rodando_sai_limpo():
    proc = _run("""
        import os, tempfile, pathlib
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        from maestro_local.db import models
        models.switch_db(str(pathlib.Path(tempfile.mkdtemp())/"t.db"))
        from maestro_local.gui.main_window import MainWindow
        w = MainWindow(); w._open_key("transcricoes")
        w.close()
        print("CLOSE_LIMPO")
    """)
    assert proc.returncode == 0, proc.stderr[-500:]
    # Sem thread presa, não deve tomar o atalho do os._exit.
    assert "CLOSE_LIMPO" in proc.stdout
