"""B4 — ações contextuais: cada botão só habilita quando faz sentido.

Antes os botões ficavam sempre clicáveis e o motivo só aparecia DEPOIS do
clique, como mensagem de erro ("Nenhuma ação encontrada", "Nada para
exportar"). Agora o estado e o tooltip dizem antes.
"""


def test_reuniao_vazia_desabilita_tudo(meetings_view):
    v = meetings_view
    v._new_meeting()
    v._refresh_actions()
    assert not v.analyze_btn.isEnabled()
    assert not v.export_btn.isEnabled()
    assert not v.copy_btn.isEnabled()
    assert not v.tasks_btn.isEnabled()
    assert not v.save_day_btn.isEnabled()


def test_com_transcricao_libera_exportar_e_copiar(meetings_view):
    v = meetings_view
    v._set_transcript_text("Texto da reunião")
    v._refresh_actions()
    assert v.export_btn.isEnabled()
    assert v.copy_btn.isEnabled()


def test_analisar_exige_provedor_de_ia(meetings_view, monkeypatch):
    v = meetings_view
    v._set_transcript_text("Texto da reunião")
    monkeypatch.setattr(v, "_provider_ready", lambda: False)
    v._refresh_actions()
    assert not v.analyze_btn.isEnabled()

    monkeypatch.setattr(v, "_provider_ready", lambda: True)
    v._refresh_actions()
    assert v.analyze_btn.isEnabled()


def test_analisar_bloqueado_durante_a_gravacao(meetings_view, monkeypatch):
    """O texto ainda está crescendo — analisar no meio não faz sentido."""
    v = meetings_view
    v._set_transcript_text("Texto parcial")
    monkeypatch.setattr(v, "_provider_ready", lambda: True)
    v._session = type("S", (), {"is_recording": True})()
    try:
        v._refresh_actions()
        assert not v.analyze_btn.isEnabled()
    finally:
        v._session = None


def test_analisar_bloqueado_com_analise_em_andamento(meetings_view, monkeypatch):
    v = meetings_view
    v._set_transcript_text("Texto da reunião")
    monkeypatch.setattr(v, "_provider_ready", lambda: True)
    monkeypatch.setattr(v.agent, "is_analyzing", lambda: True)
    v._refresh_actions()
    assert not v.analyze_btn.isEnabled()
    assert "andamento" in v.analyze_btn.toolTip()


def test_criar_tarefas_exige_acoes_e_projeto(meetings_view):
    v = meetings_view
    # sem ações
    v._refresh_actions()
    assert not v.tasks_btn.isEnabled()

    # com ações, mas sem projeto selecionado
    v._live_state = {"action_items": [{"description": "Migrar o banco"}],
                     "decisions": [], "questions": [], "plan": [], "tips": []}
    v.proj_combo.clear()
    v.proj_combo.addItem("(nenhum projeto)", None)
    v._refresh_actions()
    assert not v.tasks_btn.isEnabled()
    assert "projeto" in v.tasks_btn.toolTip().lower()

    # com ações e projeto
    v.proj_combo.addItem("Projeto X", 1)
    v.proj_combo.setCurrentIndex(1)
    v._refresh_actions()
    assert v.tasks_btn.isEnabled()


def test_meu_dia_exige_resumo_gerado(meetings_view):
    v = meetings_view
    v._set_transcript_text("Só transcrição, sem análise")
    v._refresh_actions()
    assert not v.save_day_btn.isEnabled()

    v._current["markdown"] = "# Resumo"
    v._refresh_actions()
    assert v.save_day_btn.isEnabled()


def test_tooltip_explica_o_motivo_do_bloqueio(meetings_view):
    """O usuário precisa saber POR QUE está desabilitado, sem clicar."""
    v = meetings_view
    v._new_meeting()
    v._refresh_actions()
    assert "Disponível" in v.export_btn.toolTip()
    assert "Disponível" in v.tasks_btn.toolTip()
    assert "Disponível" in v.save_day_btn.toolTip()
