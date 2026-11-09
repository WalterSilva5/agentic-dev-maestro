"""Executa apenas a API + web UI (sem a GUI desktop).

Útil para acessar o Relay pelo navegador em uma máquina sem interface
gráfica, ou para servir a web UI. A GUI desktop continua disponível via
`python -m relay`.
"""
import os
import sys


def main():
    from relay.config import get_active_workspace_id, get_workspace_db_path
    from relay.db.models import init_db

    port = 9777
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg in ("--port", "-p") and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])
    port = int(os.environ.get("RELAY_WEB_PORT", os.environ.get("MAESTRO_WEB_PORT", port)))

    init_db(get_workspace_db_path(get_active_workspace_id()))

    import uvicorn

    from relay.api.app import app

    print(f"Relay web + API em http://127.0.0.1:{port}/")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
