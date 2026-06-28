import sys


def _ensure_utf8():
    """Garante modo UTF-8 do interpretador.

    Quando o app é iniciado num ambiente com locale ascii (comum em
    autostart/sessões mínimas), o default encoding vira ascii e a
    transcrição (faster-whisper) quebra com UnicodeDecodeError ao ler
    arquivos do modelo com acentos. Re-executa em modo UTF-8 só nesse caso.
    """
    import os

    if sys.flags.utf8_mode or os.environ.get("MAESTRO_UTF8_REEXEC") == "1":
        return
    import locale
    enc = (locale.getpreferredencoding(False) or "").lower().replace("-", "")
    fs_enc = (sys.getfilesystemencoding() or "").lower().replace("-", "")
    ascii_like = {"ascii", "ansix3.41968", "usascii", ""}
    if enc not in ascii_like and fs_enc not in ascii_like:
        return
    os.environ["MAESTRO_UTF8_REEXEC"] = "1"
    os.environ["PYTHONUTF8"] = "1"
    try:
        os.execv(sys.executable, [sys.executable, "-X", "utf8", "-m", "maestro_local", *sys.argv[1:]])
    except Exception:  # noqa: BLE001 - se falhar, segue sem re-exec
        pass


_ensure_utf8()

from maestro_local.config import get_active_workspace_id, get_workspace_db_path
from maestro_local.db.models import init_db
from maestro_local.api.server import start_api


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
    app.setApplicationName("Maestro Local")
    window = MainWindow(api_port=port)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
