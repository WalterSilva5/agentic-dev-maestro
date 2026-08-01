"""Modal de foco do dia: mensagem configurável + pendências, uma vez por dia."""
from datetime import date, datetime, timedelta

import maestro_local.config as config_module
from maestro_local.db.models import Todo, get_session
from maestro_local.gui.daily_focus_dialog import (
    DailyFocusDialog,
    marcar_concluido,
    todos_abertos,
)


def _todo(texto, prioridade="MEDIUM", due=None, done=False):
    s = get_session()
    try:
        td = Todo(text=texto, priority=prioridade, due_at=due, done=done)
        s.add(td)
        s.commit()
        return td.id
    finally:
        s.close()


def test_mensagem_padrao(temp_db):
    assert config_module.get_daily_focus_config()["message"] == "FOCO NO OBJETIVO"


def test_mensagem_personalizavel(temp_db):
    config_module.set_daily_focus_config(message="ENTREGAR A RELEASE")
    assert config_module.get_daily_focus_config()["message"] == "ENTREGAR A RELEASE"


def test_mensagem_vazia_volta_ao_padrao(temp_db):
    """Sem isso o modal apareceria com o topo em branco."""
    config_module.set_daily_focus_config(message="   ")
    assert config_module.get_daily_focus_config()["message"] == "FOCO NO OBJETIVO"


def test_aparece_uma_vez_por_dia(temp_db):
    hoje = date.today().isoformat()
    assert config_module.daily_focus_pending(hoje) is True
    config_module.set_daily_focus_config(last_shown=hoje)
    assert config_module.daily_focus_pending(hoje) is False
    assert config_module.daily_focus_pending("2099-01-01") is True


def test_desabilitado_nao_aparece(temp_db):
    config_module.set_daily_focus_config(enabled=False)
    assert config_module.daily_focus_pending(date.today().isoformat()) is False


def test_lista_so_pendencias_em_aberto(temp_db):
    _todo("pendente")
    _todo("ja feito", done=True)
    textos = [td["text"] for td in todos_abertos()]
    assert textos == ["pendente"]


def test_ordena_por_prioridade_e_vencimento(temp_db):
    _todo("baixa", "LOW")
    _todo("urgente", "URGENT")
    _todo("media", "MEDIUM")
    _todo("alta", "HIGH")
    assert [td["text"] for td in todos_abertos()] == \
        ["urgente", "alta", "media", "baixa"]


def test_vencimento_desempata_dentro_da_prioridade(temp_db):
    _todo("depois", "HIGH", due=datetime.now() + timedelta(days=5))
    _todo("antes", "HIGH", due=datetime.now() + timedelta(days=1))
    assert [td["text"] for td in todos_abertos()][:2] == ["antes", "depois"]


def test_concluir_pelo_modal(temp_db):
    tid = _todo("terminar isso")
    marcar_concluido(tid)
    assert todos_abertos() == []
    s = get_session()
    try:
        assert s.get(Todo, tid).completed_at is not None
    finally:
        s.close()


def test_dialogo_mostra_mensagem_e_pendencias(qapp, temp_db):
    _todo("uma pendência")
    dlg = DailyFocusDialog(None, "MEU FOCO", todos_abertos())
    assert dlg.msg_label.text() == "MEU FOCO"


def test_dialogo_sem_pendencias_nao_quebra(qapp, temp_db):
    dlg = DailyFocusDialog(None, "MEU FOCO", [])
    assert dlg.concluidos() == set()


def test_salvar_configuracoes_preserva_last_shown(qapp, temp_db):
    """Regressão: `settings` é reescrito inteiro ao salvar; sem preservar o
    last_shown, mexer em qualquer opção faria o modal reaparecer no mesmo dia."""
    from maestro_local.gui.views.settings_view import SettingsView
    hoje = date.today().isoformat()
    config_module.set_daily_focus_config(last_shown=hoje, message="X")

    view = SettingsView()
    view.pomodoro_duration.setValue(30)   # dispara _save_settings

    assert config_module.get_daily_focus_config()["last_shown"] == hoje
    assert config_module.daily_focus_pending(hoje) is False
