"""Shell de desktop (pywebview) — abre a web UI React numa janela nativa.

Primeiro passo (E1) da migração para a rota web — ver
`docs/planos/migracao-frontend-responsivo`. Sobe o daemon local (a mesma API
FastAPI usada pela GUI Qt) num thread e renderiza `http://127.0.0.1:{port}/`
(a web UI React responsiva, já buildada em `webui/dist`) numa janela nativa.

A GUI Qt continua disponível via `python -m maestro_local`. Este shell é uma
alternativa opt-in, sem substituir nada por enquanto.

Uso:
    python -m maestro_local.desktop_shell [--port 9777]
    maestro-shell                         (após instalar o extra)

Requer o extra de shell:
    pip install -e '.[shell]'    (ou: pip install pywebview)
"""
from __future__ import annotations

import os
import sys
import time
import urllib.request


def _parse_port(default: int = 9777) -> int:
    port = default
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg in ("--port", "-p") and i < len(sys.argv) - 1:
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass
    return int(os.environ.get("MAESTRO_WEB_PORT", port))


def _wait_for_api(port: int, timeout: float = 20.0) -> bool:
    """Aguarda a API responder /api/health antes de abrir a janela."""
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:  # noqa: S310
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.2)
    return False


def main() -> int:
    try:
        import webview
    except ModuleNotFoundError:
        sys.stderr.write(
            "pywebview não está instalado.\n"
            "Instale com:  pip install -e '.[shell]'   (ou: pip install pywebview)\n"
            "Enquanto isso, a GUI desktop segue disponível: python -m maestro_local\n")
        return 1

    from maestro_local.api.server import start_api
    from maestro_local.config import get_active_workspace_id, get_workspace_db_path
    from maestro_local.db.models import init_db
    from maestro_local.i18n import init_language

    port = _parse_port()
    init_language()
    init_db(get_workspace_db_path(get_active_workspace_id()))
    start_api(port)

    if not _wait_for_api(port):
        sys.stderr.write(
            f"A API não respondeu em http://127.0.0.1:{port}/ — abortando o shell.\n")
        return 1

    webview.create_window(
        "Agentic Dev Maestro",
        url=f"http://127.0.0.1:{port}/",
        width=1280, height=820, min_size=(860, 600),
    )
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
