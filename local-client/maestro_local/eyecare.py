"""Pausa para os olhos — lembrete periódico no estilo SafeEyes.

Regra 20-20-20: a cada ~20 minutos, olhar para longe por ~20 segundos.

Três coisas seguram a pausa, em ordem de prioridade:

1. **Reunião em andamento** — automático. Pedir "adie antes de começar" seria
   transferir para o usuário um controle que o programa consegue deduzir.
2. **Adiada manualmente** até um instante futuro.
3. **Desligada** nas funcionalidades.

O estado (`ultima_pausa`, `adiada_ate`) fica na configuração, então fechar e
reabrir o programa não zera o ciclo nem cancela um adiamento.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from maestro_local.config import load_config, save_config

PADROES = {
    "intervalo_min": 20,     # 20-20-20
    "duracao_seg": 20,
    "adiar_min": 5,
}
_LIMITES = {
    "intervalo_min": (5, 180),
    "duracao_seg": (5, 300),
    "adiar_min": (1, 60),
}
_FMT = "%Y-%m-%dT%H:%M:%S"


def _bruto() -> dict:
    return load_config().get("settings", {}).get("eyecare", {}) or {}


def _num(bruto: dict, chave: str) -> int:
    minimo, maximo = _LIMITES[chave]
    try:
        valor = int(bruto.get(chave, PADROES[chave]))
    except (TypeError, ValueError):
        valor = PADROES[chave]
    return max(minimo, min(maximo, valor))


def _instante(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        return datetime.strptime(texto, _FMT)
    except ValueError:
        return None


def config() -> dict:
    b = _bruto()
    return {
        "intervalo_min": _num(b, "intervalo_min"),
        "duracao_seg": _num(b, "duracao_seg"),
        "adiar_min": _num(b, "adiar_min"),
        "ultima_pausa": _instante(b.get("ultima_pausa")),
        "adiada_ate": _instante(b.get("adiada_ate")),
    }


def definir(intervalo_min: int | None = None, duracao_seg: int | None = None,
            adiar_min: int | None = None) -> None:
    cfg = load_config()
    olhos = cfg.setdefault("settings", {}).setdefault("eyecare", {})
    for chave, valor in (("intervalo_min", intervalo_min),
                         ("duracao_seg", duracao_seg),
                         ("adiar_min", adiar_min)):
        if valor is not None:
            minimo, maximo = _LIMITES[chave]
            olhos[chave] = max(minimo, min(maximo, int(valor)))
    save_config(cfg)


def _gravar_instante(chave: str, quando: datetime | None) -> None:
    cfg = load_config()
    olhos = cfg.setdefault("settings", {}).setdefault("eyecare", {})
    olhos[chave] = quando.strftime(_FMT) if quando else ""
    save_config(cfg)


def marcar_pausa_feita(agora: datetime | None = None) -> None:
    """Reinicia o ciclo e cancela um adiamento pendente."""
    agora = agora or datetime.now()
    _gravar_instante("ultima_pausa", agora)
    _gravar_instante("adiada_ate", None)


def adiar(minutos: int | None = None, agora: datetime | None = None) -> datetime:
    """Empurra a próxima pausa. Devolve até quando ficará silenciada."""
    agora = agora or datetime.now()
    minutos = minutos if minutos is not None else config()["adiar_min"]
    ate = agora + timedelta(minutes=max(1, int(minutos)))
    _gravar_instante("adiada_ate", ate)
    return ate


def proxima_pausa(agora: datetime | None = None) -> datetime:
    """Quando a próxima pausa é devida (ignora reunião em andamento)."""
    agora = agora or datetime.now()
    c = config()
    base = c["ultima_pausa"] or agora
    devida = base + timedelta(minutes=c["intervalo_min"])
    adiada = c["adiada_ate"]
    return max(devida, adiada) if adiada else devida


def devida(agora: datetime | None = None, em_reuniao: bool = False) -> bool:
    """A pausa deve aparecer agora?

    `em_reuniao` segura a pausa sem reiniciar o ciclo: assim que a reunião
    termina, ela aparece na verificação seguinte em vez de ser perdida.
    """
    if em_reuniao:
        return False
    agora = agora or datetime.now()
    c = config()
    if c["ultima_pausa"] is None:
        # Primeira execução: não interrompe de cara — conta a partir de agora.
        marcar_pausa_feita(agora)
        return False
    return agora >= proxima_pausa(agora)


def cancelar_adiamento() -> None:
    """Volta a valer o ciclo normal (usado pelo menu da bandeja)."""
    _gravar_instante("adiada_ate", None)


# ---------------------------------------------------------------------------
# Dicas exibidas durante a pausa
#
# São de ergonomia e hábito, não de tratamento: o programa não tem como saber
# de sintoma nenhum. Quando o assunto passa disso, a dica manda procurar um
# oftalmologista em vez de sugerir conduta.
#
# A rotação é sequencial e guardada na configuração, não sorteada: sorteio
# repete a mesma dica em pausas seguidas com frequência incômoda, e depois de
# ver a mesma frase três vezes ninguém lê a quarta.
# ---------------------------------------------------------------------------

DICAS: tuple[str, ...] = (
    "Pisque algumas vezes de propósito. Diante da tela a gente pisca bem menos, "
    "e é isso que resseca os olhos.",
    "Olhe para algo a uns 6 metros. O músculo que foca de perto passa horas "
    "contraído — longe é o que o solta.",
    "Deixe a tela a mais ou menos um braço de distância, com o topo na altura "
    "dos olhos ou um pouco abaixo.",
    "Compare o brilho da tela com o da parede atrás dela. Tela muito mais clara "
    "que o ambiente cansa a vista.",
    "Aumente o tamanho da fonte em vez de aproximar o rosto da tela.",
    "Desvie o ar do ventilador ou do ar-condicionado do rosto: vento direto "
    "resseca os olhos mais rápido que a tela.",
    "Posicione a luz de forma que não reflita na tela. Reflexo faz apertar os "
    "olhos sem perceber.",
    "Beba água. Olho seco também vem de desidratação, não só do tempo de tela.",
    "Levante e caminhe um pouco: a pausa vale para a postura e a circulação "
    "tanto quanto para os olhos.",
    "Ardência, vista embaçada ou dor de cabeça que não passam com pausa são "
    "caso de oftalmologista, não de ajuste de tela.",
    "Se usa óculos, confira se o grau está em dia — grau vencido faz forçar a "
    "vista o dia inteiro.",
)


def proxima_dica() -> str:
    """Dica da vez, avançando a rotação para a pausa seguinte."""
    bruto = _bruto()
    try:
        indice = int(bruto.get("dica", 0))
    except (TypeError, ValueError):
        indice = 0
    indice %= len(DICAS)

    cfg = load_config()
    cfg.setdefault("settings", {}).setdefault("eyecare", {})["dica"] = (
        (indice + 1) % len(DICAS))
    save_config(cfg)
    return DICAS[indice]
