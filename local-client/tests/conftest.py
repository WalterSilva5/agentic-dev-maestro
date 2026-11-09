"""Configuração dos testes.

A GUI roda offscreen e cada teste usa um banco SQLite temporário — os dados
reais do usuário (~/.local/share/... ) nunca são tocados.
"""
from __future__ import annotations

import os

# Precisa vir antes de qualquer import do Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONUTF8", "1")
# atalhos globais (pynput/X Record) não podem subir na suíte: várias janelas
# na mesma sessão derrubam o processo com segfault
os.environ.setdefault("RELAY_DISABLE_HOTKEYS", "1")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """QApplication única para a sessão de testes."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Banco temporário isolado, ativo durante o teste.

    Também isola `config.json` (usado por SettingsView e outras telas): sem
    isso, qualquer teste que dispare `_save_settings` grava no arquivo REAL do
    usuário em `~/.relay/config.json` — já aconteceu numa verificação
    manual durante o desenvolvimento (mutou o whisper_model de verdade).
    """
    from relay.db import models
    import relay.config as config_module

    db_path = tmp_path / "test.db"
    models.switch_db(str(db_path))
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    yield db_path
    # Volta o engine para um estado limpo entre testes
    models.switch_db(str(db_path))


@pytest.fixture
def meetings_view(qapp, temp_db, monkeypatch):
    """View de Reuniões pronta, sem provedor de IA (nada dispara a rede)."""
    from relay.gui.views.transcricoes_view import TranscricoesView

    view = TranscricoesView()
    # Sem IA: garante que nenhum teste faça chamada real ao LLM.
    monkeypatch.setattr(view, "_provider_ready", lambda: False)
    yield view
