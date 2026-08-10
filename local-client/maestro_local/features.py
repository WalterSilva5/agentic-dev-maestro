"""Funcionalidades que o usuário pode ligar/desligar.

Com tudo habilitado a interface fica cheia: 18 telas somando o menu e o hub de
Ferramentas, mais os extras da barra lateral. Aqui ficam quais existem, o padrão
de cada uma e a leitura/gravação da escolha — num só lugar, para não virar um
punhado de flags espalhadas pelas telas.

Duas regras protegem o usuário de se trancar para fora:

- **Configurações nunca some** — é por onde se religa o resto.
- **Ferramentas é derivada**: aparece enquanto houver ao menos uma ferramenta
  ligada, e some sozinha quando não houver. Assim não dá para desligar o hub e
  deixar as ferramentas ativas porém inalcançáveis.
"""
from __future__ import annotations

from dataclasses import dataclass

from maestro_local.config import load_config, save_config

GRUPO_PRINCIPAIS = "Telas principais"
GRUPO_FERRAMENTAS = "Ferramentas"
GRUPO_EXTRAS = "Extras da interface"


@dataclass(frozen=True)
class Funcionalidade:
    chave: str
    rotulo: str
    grupo: str
    descricao: str = ""
    padrao: bool = True


# Chave da tela que nunca pode ser desligada.
CHAVE_PROTEGIDA = "settings"
# Chave da tela derivada (visibilidade calculada, não escolhida).
CHAVE_HUB = "ferramentas"

FUNCIONALIDADES: tuple[Funcionalidade, ...] = (
    # --- telas do menu ---
    Funcionalidade("transcricoes", "Reuniões", GRUPO_PRINCIPAIS,
                   "Gravação, transcrição e copiloto ao vivo"),
    Funcionalidade("dashboard", "Dashboard", GRUPO_PRINCIPAIS,
                   "Visão geral, métricas e atividade"),
    Funcionalidade("daily", "Meu Dia", GRUPO_PRINCIPAIS,
                   "Notas do dia, relatório e sync do Obsidian"),
    Funcionalidade("board", "Board", GRUPO_PRINCIPAIS,
                   "Kanban de tarefas e sprints"),
    Funcionalidade("chat", "Assistente", GRUPO_PRINCIPAIS,
                   "Conversa com a IA sobre o trabalho"),
    Funcionalidade("projects", "Projetos", GRUPO_PRINCIPAIS,
                   "Criar e gerenciar projetos"),
    Funcionalidade("skills", "Skills", GRUPO_PRINCIPAIS,
                   "Instalação de skills para agentes"),
    Funcionalidade("guide", "Instruções", GRUPO_PRINCIPAIS,
                   "Documentação de uso do aplicativo"),

    # --- hub de ferramentas ---
    Funcionalidade("study", "Estudos", GRUPO_FERRAMENTAS,
                   "Planos e tópicos de estudo"),
    Funcionalidade("vault", "Senhas", GRUPO_FERRAMENTAS,
                   "Cofre KeePass"),
    Funcionalidade("library", "Biblioteca", GRUPO_FERRAMENTAS,
                   "Snippets, runbooks, code review, git, tempo"),
    Funcionalidade("apitester", "Testador de API", GRUPO_FERRAMENTAS,
                   "Requisições HTTP salvas"),
    Funcionalidade("kb", "Base de conhecimento", GRUPO_FERRAMENTAS,
                   "Notas com backlinks e Q&A"),
    Funcionalidade("memory", "Memória agentic", GRUPO_FERRAMENTAS,
                   "Fatos e decisões com busca semântica"),
    Funcionalidade("english", "Praticar Inglês", GRUPO_FERRAMENTAS,
                   "Conversação por voz"),
    Funcionalidade("translate", "Tradutor", GRUPO_FERRAMENTAS,
                   "Tradução entre idiomas"),

    # --- extras da interface ---
    Funcionalidade("quick_record", "Gravação rápida na barra lateral",
                   GRUPO_EXTRAS, "Botão de gravar sempre à mão"),
    Funcionalidade("todo_reminder", "Lembrete de pendências",
                   GRUPO_EXTRAS, "Aviso periódico de TODOs vencidos"),
    Funcionalidade("pomodoro", "Pomodoro no Dashboard",
                   GRUPO_EXTRAS, "Cronômetro de foco"),
    Funcionalidade("eyecare", "Pausa para os olhos", GRUPO_EXTRAS,
                   "Lembrete periódico de descanso visual (não aparece durante reuniões)"),
)

_POR_CHAVE = {f.chave: f for f in FUNCIONALIDADES}
_CHAVES_FERRAMENTAS = tuple(f.chave for f in FUNCIONALIDADES
                            if f.grupo == GRUPO_FERRAMENTAS)


def _armazenadas() -> dict:
    return load_config().get("settings", {}).get("features", {}) or {}


def habilitada(chave: str) -> bool:
    """A funcionalidade está ligada? Chaves desconhecidas contam como ligadas,
    para uma versão nova nunca esconder algo por engano."""
    if chave == CHAVE_PROTEGIDA:
        return True
    if chave == CHAVE_HUB:
        return any(habilitada(k) for k in _CHAVES_FERRAMENTAS)
    f = _POR_CHAVE.get(chave)
    if f is None:
        return True
    return bool(_armazenadas().get(chave, f.padrao))


def definir(chave: str, valor: bool) -> None:
    """Liga/desliga. Ignora as chaves protegida e derivada."""
    if chave in (CHAVE_PROTEGIDA, CHAVE_HUB) or chave not in _POR_CHAVE:
        return
    cfg = load_config()
    feats = cfg.setdefault("settings", {}).setdefault("features", {})
    feats[chave] = bool(valor)
    save_config(cfg)


def por_grupo() -> dict[str, list[Funcionalidade]]:
    grupos: dict[str, list[Funcionalidade]] = {}
    for f in FUNCIONALIDADES:
        grupos.setdefault(f.grupo, []).append(f)
    return grupos
