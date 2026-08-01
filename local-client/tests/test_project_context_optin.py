"""Contexto do workspace/projeto só vai ao assistente com autorização.

Antes, nome do workspace, projeto, descrição e até 12 tarefas em aberto eram
enviados ao provedor de IA em toda reunião, sem o usuário saber. Agora é opt-in,
perguntado ao começar a gravar.
"""
import maestro_local.gui.confirm_context as confirm_context
from maestro_local.db.models import Project, get_session


def _cria_projeto(nome="Projeto X"):
    s = get_session()
    try:
        p = Project(key="PX", name=nome, description="descrição secreta")
        s.add(p)
        s.commit()
        return p.id
    finally:
        s.close()


def test_padrao_nao_inclui_projeto_nem_workspace(meetings_view):
    v = meetings_view
    pid = _cria_projeto()
    v.proj_combo.clear()
    v.proj_combo.addItem("Projeto X", pid)
    v.prep_edit.setPlainText("pauta da reunião")

    ctx = v._meeting_context()          # sem decisão tomada
    assert "pauta da reunião" in ctx     # o que é da reunião entra
    assert "Projeto X" not in ctx
    assert "descrição secreta" not in ctx
    assert "Workspace" not in ctx


def test_inclui_quando_autorizado(meetings_view):
    v = meetings_view
    pid = _cria_projeto()
    v.proj_combo.clear()
    v.proj_combo.addItem("Projeto X", pid)

    v._share_project_context = True
    ctx = v._meeting_context()
    assert "Projeto X" in ctx


def test_gravar_pergunta_uma_vez_por_reuniao(meetings_view, monkeypatch):
    v = meetings_view
    pid = _cria_projeto()
    v.proj_combo.clear()
    v.proj_combo.addItem("Projeto X", pid)

    chamadas = []
    monkeypatch.setattr(confirm_context, "confirm_share_context",
                        lambda *a, **k: chamadas.append(1) or True)

    v._perguntar_contexto_projeto()
    assert len(chamadas) == 1
    assert v._share_project_context is True

    v._perguntar_contexto_projeto()      # segunda gravação da MESMA reunião
    assert len(chamadas) == 1, "não deveria perguntar de novo na mesma reunião"


def test_recusar_mantem_o_contexto_fora(meetings_view, monkeypatch):
    v = meetings_view
    pid = _cria_projeto()
    v.proj_combo.clear()
    v.proj_combo.addItem("Projeto X", pid)
    monkeypatch.setattr(confirm_context, "confirm_share_context",
                        lambda *a, **k: False)

    v._perguntar_contexto_projeto()
    assert v._share_project_context is False
    assert "Projeto X" not in v._meeting_context()


def test_nova_reuniao_volta_a_perguntar(meetings_view, monkeypatch):
    v = meetings_view
    monkeypatch.setattr(confirm_context, "confirm_share_context",
                        lambda *a, **k: True)
    v._perguntar_contexto_projeto()
    v._new_meeting()
    assert v._share_project_context is None, "a decisão é por reunião"


def test_sem_projeto_nem_workspace_nao_pergunta(meetings_view, monkeypatch):
    """Não faz sentido perguntar quando não há nada a compartilhar."""
    v = meetings_view
    v.proj_combo.clear()
    v.proj_combo.addItem("(nenhum projeto)", None)
    monkeypatch.setattr("maestro_local.config.list_workspaces", lambda: [])

    chamadas = []
    monkeypatch.setattr(confirm_context, "confirm_share_context",
                        lambda *a, **k: chamadas.append(1) or True)
    v._perguntar_contexto_projeto()
    assert chamadas == []
    assert v._share_project_context is False
