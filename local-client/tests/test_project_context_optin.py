"""A reunião é independente do projeto.

Iniciar uma reunião não pergunta mais sobre o projeto e o contexto enviado
ao copiloto não inclui dados de workspace/projeto — a gravação é salva sem
vínculo de projeto.
"""
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


def test_contexto_nao_inclui_projeto_nem_workspace(meetings_view):
    v = meetings_view
    pid = _cria_projeto()
    v.proj_combo.clear()
    v.proj_combo.addItem("Projeto X", pid)
    v.prep_edit.setPlainText("pauta da reunião")

    ctx = v._meeting_context()
    assert "pauta da reunião" in ctx      # o que é da reunião entra
    assert "Projeto X" not in ctx
    assert "descrição secreta" not in ctx
    assert "Workspace" not in ctx


def test_nao_ha_mais_prompt_de_contexto(meetings_view):
    """A pergunta ao gravar foi removida junto com o opt-in."""
    assert not hasattr(meetings_view, "_perguntar_contexto_projeto")
