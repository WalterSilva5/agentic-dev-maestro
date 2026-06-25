import sys

from maestro_local.db.models import init_db
from maestro_local.api.server import start_api


def main():
    port = 9777
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg in ("--port", "-p") and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])

    init_db()
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
