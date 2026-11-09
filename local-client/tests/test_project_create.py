"""Botão "+" de novo projeto junto ao seletor (como no workspace)."""
from relay.db.models import BoardColumn, Project, get_session
from relay.gui.main_window import (
    MainWindow,
    create_project_with_defaults,
    suggest_project_key,
)


def test_suggest_key(temp_db):
    assert suggest_project_key("Migração Legal") == "MIGR"
    assert suggest_project_key("ab") == "AB"
    assert suggest_project_key("   ") == ""


def test_create_project_com_colunas_padrao(temp_db):
    pid = create_project_with_defaults("Proj", "PJ")
    assert pid is not None
    s = get_session()
    try:
        cols = s.query(BoardColumn).filter_by(project_id=pid).order_by(BoardColumn.order).all()
        assert [c.name for c in cols] == ["A fazer", "Fazendo", "Feito"]
        assert sum(1 for c in cols if c.is_done) == 1
    finally:
        s.close()


def test_create_project_chave_duplicada_ganha_sufixo(temp_db):
    create_project_with_defaults("Proj", "PJ")
    pid2 = create_project_with_defaults("Proj 2", "PJ")
    assert pid2 is not None
    s = get_session()
    try:
        keys = sorted(p.key for p in s.query(Project).all())
        assert keys == ["PJ", "PJ-2"]
    finally:
        s.close()


def test_create_project_invalido(temp_db):
    assert create_project_with_defaults("   ", "") is None


def test_botao_novo_projeto_no_seletor(qapp, temp_db):
    w = MainWindow()
    assert w.new_project_btn.text() == "+"
    assert w.new_project_btn.isVisibleTo(w.sidebar)
    assert w.project_selector.count() >= 1  # ao menos "(nenhum projeto)"


def test_novo_projeto_aparece_no_seletor(qapp, temp_db, monkeypatch):
    from relay import config as config_module
    w = MainWindow()
    monkeypatch.setattr(config_module, "set_active_project_id", lambda pid: None)
    pid = create_project_with_defaults("Proj", "PJ")
    w._populate_project_selector()
    assert w.project_selector.findData(pid) >= 0
