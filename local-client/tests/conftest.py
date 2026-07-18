"""Configuração dos testes.

A GUI roda offscreen e cada teste usa um banco SQLite temporário — os dados
reais do usuário (~/.local/share/... ) nunca são tocados.
"""
from __future__ import annotations

import os

# Precisa vir antes de qualquer import do Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONUTF8", "1")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """QApplication única para a sessão de testes."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Banco temporário isolado, ativo durante o teste."""
    from maestro_local.db import models

    db_path = tmp_path / "test.db"
    models.switch_db(str(db_path))
    yield db_path
    # Volta o engine para um estado limpo entre testes
    models.switch_db(str(db_path))


@pytest.fixture
def meetings_view(qapp, temp_db, monkeypatch):
    """View de Reuniões pronta, sem provedor de IA (nada dispara a rede)."""
    from maestro_local.gui.views.transcricoes_view import TranscricoesView

    view = TranscricoesView()
    # Sem IA: garante que nenhum teste faça chamada real ao LLM.
    monkeypatch.setattr(view, "_provider_ready", lambda: False)
    yield view
