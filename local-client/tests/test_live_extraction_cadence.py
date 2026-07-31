"""Cadência da atualização dos itens durante a reunião.

Queixa que originou: "o agente demora a atualizar a lista de itens". Três
causas tratadas aqui — a verificação depender só do tique da gravação, o
último trecho falado só entrar depois da transcrição completa, e o texto
enviado numa extração que falha ser perdido para sempre.
"""
from maestro_local.transcricoes.constants import LIVE_AI_INTERVAL_MS, LIVE_AI_TIMEOUT


def test_timer_periodico_configurado(meetings_view):
    v = meetings_view
    assert v._live_poll.interval() == LIVE_AI_INTERVAL_MS
    assert not v._live_poll.isActive()   # só roda durante o ao vivo


def test_stop_live_para_o_timer(meetings_view):
    v = meetings_view
    v._live_poll.start()
    v._stop_live()
    assert not v._live_poll.isActive()


def test_falha_devolve_o_trecho_para_a_fila(meetings_view):
    """Sem isso, o que foi dito enquanto a IA falhava nunca entra nos itens."""
    v = meetings_view
    v._live_pending = "trecho novo"
    v._live_inflight = ""
    v._provider_ready = lambda: True
    v._start_live_extract()
    assert v._live_pending == ""          # saiu da fila ao ser enviado
    assert v._live_inflight == "trecho novo"

    v._on_live_extract_error("timeout")
    assert "trecho novo" in v._live_pending, "o trecho foi perdido"
    assert v._live_inflight == ""


def test_falha_preserva_a_ordem_do_texto(meetings_view):
    v = meetings_view
    v._live_inflight = "primeiro trecho"
    v._live_pending = "segundo trecho"
    v._on_live_extract_error("erro")
    assert v._live_pending == "primeiro trecho segundo trecho"


def test_sucesso_limpa_o_trecho_em_voo(meetings_view):
    v = meetings_view
    v._live_inflight = "trecho"
    v._on_live_extracted({"action_items": [], "decisions": [], "questions": [],
                          "plan": [], "tips": []})
    assert v._live_inflight == ""


def test_flush_extrai_ignorando_os_limiares(meetings_view):
    """Ao encerrar, um trecho curto (abaixo do limiar) precisa ser extraído."""
    v = meetings_view
    v._provider_ready = lambda: True
    v._live_pending = "poucas palavras"   # abaixo de LIVE_AI_MIN_WORDS
    v._live_secs_since = 0                # e abaixo de LIVE_AI_MIN_SECONDS

    v._maybe_extract_live()
    assert v._live_pending == "poucas palavras", "não deveria disparar pelos limiares"

    v._flush_live_extract()
    assert v._live_pending == "", "o flush deveria ter enviado o trecho"


def test_flush_sem_texto_nao_chama_a_ia(meetings_view):
    v = meetings_view
    v._provider_ready = lambda: True
    v._live_pending = "   "
    chamou = []
    v.agent.extract_live = lambda *a, **k: chamou.append(1)
    v._flush_live_extract()
    assert chamou == []


def test_flush_sem_provedor_nao_chama_a_ia(meetings_view):
    v = meetings_view
    v._provider_ready = lambda: False
    v._live_pending = "texto"
    chamou = []
    v.agent.extract_live = lambda *a, **k: chamou.append(1)
    v._flush_live_extract()
    assert chamou == []


def test_timeout_do_ao_vivo_e_curto():
    """O padrão do provedor (120s + retries) não serve para o ao vivo."""
    assert LIVE_AI_TIMEOUT < 120


def test_invoke_json_repassa_o_timeout(monkeypatch):
    """O timeout precisa chegar ao modelo, senão a mudança não vale de nada."""
    import maestro_local.ai.llm as llm
    recebido = {}

    class _FakeModel:
        def invoke(self, messages):
            class R:
                content = "{}"
            return R()

    def fake_get(temperature=0.3, provider=None, timeout=120):
        recebido["timeout"] = timeout
        return _FakeModel()

    monkeypatch.setattr(llm, "get_chat_model", fake_get)
    llm.invoke_json([("user", "oi")], timeout=45)
    assert recebido["timeout"] == 45


def test_resultado_ao_vivo_nao_sobrescreve_analise_completa(meetings_view, monkeypatch):
    """Ao parar, os dois workers podem se cruzar; a análise completa vence."""
    v = meetings_view
    v._live_state = {"decisions": ["da análise completa"], "action_items": [],
                     "questions": [], "plan": [], "tips": []}
    monkeypatch.setattr(v.agent, "is_extracting", lambda: True)   # completa em curso
    v._on_live_extracted({"decisions": ["do ao vivo, mais antigo"], "action_items": [],
                          "questions": [], "plan": [], "tips": []})
    assert v._live_state["decisions"] == ["da análise completa"]


def test_resultado_ao_vivo_aplica_quando_nao_ha_analise(meetings_view, monkeypatch):
    v = meetings_view
    monkeypatch.setattr(v.agent, "is_extracting", lambda: False)
    v._on_live_extracted({"decisions": ["do ao vivo"], "action_items": [],
                          "questions": [], "plan": [], "tips": []})
    assert v._live_state["decisions"] == ["do ao vivo"]
