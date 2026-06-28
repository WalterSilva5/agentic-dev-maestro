import sys

from maestro_local.config import get_active_workspace_id, get_workspace_db_path
from maestro_local.db.models import init_db
from maestro_local.api.server import start_api


def _restore_utf8_locale():
    """Restaura um locale UTF-8 no nível do C.

    O QApplication do Qt reseta o locale C (LC_CTYPE) ao iniciar. Isso faz o
    ctranslate2/faster-whisper decodificarem os arquivos do modelo em ascii e
    quebrarem com \"'ascii' codec can't decode byte 0xc3\" durante a
    transcrição (que roda em QThread). Restaurar um locale UTF-8 aqui corrige.
    """
    import locale

    # Mensagens ASCII (LC_MESSAGES=C) + ctype UTF-8. Evita que os.strerror()
    # do PyAV retorne mensagens acentuadas (pt_BR) que quebram a decodificação
    # quando o Qt reseta o LC_CTYPE para ascii.
    for loc in ("C.UTF-8", "C.utf8", "en_US.UTF-8"):
        try:
            locale.setlocale(locale.LC_ALL, loc)
            return
        except locale.Error:
            continue


def main():
    port = 9777
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg in ("--port", "-p") and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])

    ws_id = get_active_workspace_id()
    db_path = get_workspace_db_path(ws_id)
    init_db(db_path)
    start_api(port)

    from PySide6.QtWidgets import QApplication
    from maestro_local.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    _restore_utf8_locale()  # Qt zera o locale ao criar o QApplication
    app.setApplicationName("Maestro Local")
    window = MainWindow(api_port=port)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
