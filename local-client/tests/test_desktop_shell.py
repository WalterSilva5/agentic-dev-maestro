"""Shell de desktop (pywebview) — só a lógica testável sem janela/display real."""
import sys

from maestro_local import desktop_shell


def test_parse_port_default():
    argv = sys.argv
    try:
        sys.argv = ["maestro-shell"]
        assert desktop_shell._parse_port() == 9777
    finally:
        sys.argv = argv


def test_parse_port_via_flag():
    argv = sys.argv
    try:
        sys.argv = ["maestro-shell", "--port", "8888"]
        assert desktop_shell._parse_port() == 8888
    finally:
        sys.argv = argv


def test_parse_port_via_env(monkeypatch):
    argv = sys.argv
    try:
        sys.argv = ["maestro-shell"]
        monkeypatch.setenv("MAESTRO_WEB_PORT", "7000")
        assert desktop_shell._parse_port() == 7000
    finally:
        sys.argv = argv


def test_wait_for_api_timeout_rapido_sem_servidor():
    """Sem API rodando na porta, desiste dentro do timeout (não trava)."""
    import time
    start = time.monotonic()
    ok = desktop_shell._wait_for_api(port=59999, timeout=0.3)
    elapsed = time.monotonic() - start
    assert ok is False
    assert elapsed < 2.0


def test_main_sem_pywebview_falha_graciosamente(monkeypatch, capsys):
    """Sem o extra 'shell' instalado, orienta o usuário em vez de estourar traceback."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "webview":
            raise ModuleNotFoundError("No module named 'webview'")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    rc = desktop_shell.main()
    assert rc == 1
    err = capsys.readouterr().err
    assert "pywebview" in err
    assert "python -m maestro_local" in err  # orienta o fallback
