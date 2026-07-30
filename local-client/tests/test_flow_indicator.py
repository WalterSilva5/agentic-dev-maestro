"""B3 — indicador do fluxo da reunião (preparar → gravar → transcrever → analisar)."""
from maestro_local.gui.meetings.flow_indicator import STAGES, FlowIndicator


def test_estagio_inicial_e_preparar(qapp):
    fi = FlowIndicator()
    assert fi.stage() == "preparar"


def test_set_stage_muda_e_ignora_invalido(qapp):
    fi = FlowIndicator()
    fi.set_stage("gravar")
    assert fi.stage() == "gravar"
    fi.set_stage("etapa-que-nao-existe")
    assert fi.stage() == "gravar"  # ignorado, mantém o estágio válido anterior


def test_todos_os_estagios_sao_aceitos(qapp):
    fi = FlowIndicator()
    for stage in STAGES:
        fi.set_stage(stage)
        assert fi.stage() == stage


def test_view_calcula_preparar_por_padrao(meetings_view):
    v = meetings_view
    v._refresh_flow_indicator()
    assert v.flow_indicator.stage() == "preparar"


def test_view_calcula_gravar_durante_gravacao(meetings_view):
    v = meetings_view
    v._session = type("S", (), {"is_recording": True})()
    v._refresh_flow_indicator()
    assert v.flow_indicator.stage() == "gravar"


def test_view_calcula_transcrever_com_progresso_visivel(meetings_view):
    v = meetings_view
    v.progress.setVisible(True)
    v._refresh_flow_indicator()
    assert v.flow_indicator.stage() == "transcrever"


def test_view_calcula_transcrever_com_transcricao_sem_analise(meetings_view):
    v = meetings_view
    v._set_transcript_text("já foi transcrito")
    v._refresh_flow_indicator()
    assert v.flow_indicator.stage() == "transcrever"


def test_view_calcula_analisar_com_markdown(meetings_view):
    v = meetings_view
    v._current["markdown"] = "# resumo"
    v._refresh_flow_indicator()
    assert v.flow_indicator.stage() == "analisar"


def test_gravando_tem_prioridade_sobre_markdown_antigo(meetings_view):
    """Reabrir uma reunião analisada e começar a regravar deve voltar a 'gravar'."""
    v = meetings_view
    v._current["markdown"] = "# resumo antigo"
    v._session = type("S", (), {"is_recording": True})()
    v._refresh_flow_indicator()
    assert v.flow_indicator.stage() == "gravar"
