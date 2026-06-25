import threading

import uvicorn

_thread = None


def start_api(port: int = 9777):
    global _thread
    if _thread and _thread.is_alive():
        return
    from maestro_local.api.app import app

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    _thread = threading.Thread(target=server.run, daemon=True)
    _thread.start()
