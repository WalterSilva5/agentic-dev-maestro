# 14 — Copiloto de ambiente: Reuniões como eixo do produto

> Objetivo: transformar Reuniões de "uma tela entre outras" no **eixo do
> aplicativo** e ampliá-la de assistente de reunião para **copiloto do
> programador** — ajuda contextual enquanto se trabalha, não só enquanto se
> conversa. Referência de produto: [Cluely](https://cluely.com/).
>
> Tarefas, subtarefas e roadmap; esforço em **homem-dia (HD)**. Alocação e
> cronograma são decisão de liderança.

## 1. O que a referência faz (levantado no site, não de memória)

| Pilar | Como funciona no Cluely |
|---|---|
| **Sem bot na reunião** | Captura o áudio da máquina; não entra como participante |
| **Overlay flutuante** | Janela local sobre as demais, movível, invisível no compartilhamento de tela |
| **Pergunta instantânea** | Atalho (Cmd/Ctrl+Enter) responde usando a reunião **e o que está na tela** |
| **Transcrição ao vivo** | ~300 ms de resposta, 12+ idiomas |
| **Notas em tempo real** | Resumo formatado e compartilhável |

## 2. O que o Maestro já tem (medido no código)

Boa parte da fundação **já existe** — o pivô é menos "construir do zero" e mais
"tirar de dentro da tela de Reuniões e reduzir latência".

| Peça | Estado | Arquivo |
|---|---|---|
| Captura de áudio do sistema (sem bot) | ✅ funciona | `transcricoes/audio.py` (267 l.) |
| Transcrição local (Whisper) | ✅ funciona | `transcricoes/transcriber.py` (209 l.) |
| Copiloto ao vivo (plano/ações/decisões/perguntas) | ✅ funciona | `transcricoes/live_assistant.py` (218 l.) |
| Perguntar com contexto | ✅ funciona | `agent_service.ask()` |
| Atalho global | ⚠️ parcial | `transcricoes/hotkeys.py` (34 l.) |
| Dicas proativas | ✅ funciona | `coach.py` (141 l.) |
| Histórico + busca | ✅ funciona | `transcricoes/repository.py` |
| **Ver a tela** | ❌ **quebrado** | ver seção 3 |

## 3. Achado que muda o plano: ver a tela não funciona

O "observador de tela" existe na interface, mas **não captura nada nesta
máquina**. Verificado:

```
plataforma Qt: wayland
pixmap nulo? True | tamanho: 0 x 0     ← screen.grabWindow(0)
```

`QScreen.grabWindow()` não funciona em **Wayland nativo** — é uma API herdada do
X11. A sessão aqui é Wayland (`XDG_SESSION_TYPE=wayland`), então a funcionalidade
está morta desde sempre nesse ambiente, falhando em silêncio.

O caminho correto no Wayland é o **XDG Desktop Portal (ScreenCast) + PipeWire**,
que está disponível na máquina (`kde.portal`, `gtk.portal` presentes). Isso
também traz o consentimento explícito do sistema (o compositor pergunta o que
compartilhar), em vez de captura silenciosa.

**Consequência:** "ver a tela" é pré-requisito do copiloto de programação e
precisa ser reconstruído, não ajustado. É a maior tarefa isolada do plano.

## 4. Distância entre hoje e o alvo

| Dimensão | Hoje | Alvo |
|---|---|---|
| **Onde vive** | Dentro da janela principal, uma aba | Overlay flutuante sempre acessível |
| **Quando ajuda** | Só durante uma "reunião" gravando | Ambiente: enquanto se trabalha |
| **Latência da fala** | Janelas de 10 s (`LIVE_WINDOW_SECONDS`) | Segmentos curtos, ordem de 1–2 s |
| **Latência dos itens** | 15 s ou 40 palavras, timeout 45 s | Pergunta sob demanda responde já |
| **Ver a tela** | Quebrado no Wayland | Portal + PipeWire, sob consentimento |
| **Histórico** | Lista dentro de Reuniões | Superfície de primeira classe, busca global |

## 5. Fases, tarefas e subtarefas

### F1 — Ver a tela de verdade (~4–6 HD) — **desbloqueia o resto**

- [ ] **F1.1 — Captura via portal** (~3–4 HD)
  - · `ScreenCast` do XDG Portal + PipeWire; sessão persistente (pede permissão
    uma vez, não a cada frame)
  - · Fallback para `grabWindow` quando a sessão for X11 (ainda funciona lá)
  - · Detectar e **avisar** quando não houver captura disponível — hoje falha
    calada
- [ ] **F1.2 — Frame sob demanda** (~1 HD)
  - · Um frame no momento da pergunta, em vez de captura periódica: menos custo
    de visão e menos dado sensível trafegando
- [ ] **F1.3 — Controle de privacidade** (~1 HD)
  - · Indicador visível enquanto a tela está sendo lida; desligar num clique
  - · Escolher monitor/janela; lembrar a escolha

### F2 — Overlay do copiloto (~5–7 HD)

- [ ] **F2.1 — Janela flutuante** (~2–3 HD)
  - · Sempre no topo, movível, compacta; abre/fecha por atalho
  - · **Restrição Wayland**: o cliente não controla posição nem "always on top"
    de forma portátil. Avaliar `layer-shell` (KDE/wlroots) e documentar o
    comportamento por compositor — não prometer o que o protocolo não dá
- [ ] **F2.2 — Pergunta instantânea** (~2 HD)
  - · Atalho global abre o overlay já com o cursor no campo
  - · Responde com o contexto disponível: transcrição recente + frame da tela
  - · Resposta em streaming (aparecer token a token, não esperar o fim)
- [ ] **F2.3 — Sugestões proativas** (~1–2 HD)
  - · Reaproveitar o `coach.py`, mas disparando por **evento de contexto** (erro
    na tela, pergunta feita na chamada), não só por tempo

### F3 — Latência (~3–5 HD)

- [ ] **F3.1 — Segmentos curtos com VAD** (~2–3 HD)
  - · Detecção de fala para cortar em pausas, em vez de janelas fixas de 10 s
  - · Modelo menor no caminho ao vivo; o modelo bom fica para o texto final
- [ ] **F3.2 — Resposta sob demanda tem prioridade** (~1 HD)
  - · Pergunta do usuário passa na frente da extração periódica em vez de
    esperar o worker livre
- [ ] **F3.3 — Medir** (~1 HD)
  - · Registrar latência fala→texto e pergunta→resposta; sem número não há como
    dizer se melhorou

### F4 — Modo ambiente, além da reunião (~4–6 HD)

- [ ] **F4.1 — Sessão de trabalho** (~2–3 HD)
  - · Separar "sessão" de "reunião": gravar áudio é opcional; a sessão pode ser
    só tela + perguntas
  - · O modelo `MeetingSession` já separa entradas de saídas — estender, não
    reescrever
- [ ] **F4.2 — Contexto de código** (~2–3 HD)
  - · Ler o que está na tela do editor e responder sobre o código visível
  - · Ligar às tarefas do board quando o usuário autorizar (já é opt-in)

### F5 — Histórico como superfície principal (~3–4 HD)

- [ ] **F5.1 — Busca global** (~2 HD)
  - · Buscar em transcrições, respostas e itens; atalho dedicado
- [ ] **F5.2 — Linha do tempo** (~1–2 HD)
  - · Sessões e reuniões numa timeline única, filtrável por projeto/período

### F6 — Reposicionar na navegação (~1 HD)

- [ ] **F6.1** — Reuniões/Copiloto no topo do grupo TRABALHO, com o histórico
  acessível direto do menu

**Total estimado: ~20–29 HD.**

## 6. Roadmap

```
F1 Ver a tela ──► F2 Overlay ──► F4 Modo ambiente ──► F5 Histórico ──► F6 Navegação
  (4–6 HD)        (5–7 HD)        (4–6 HD)            (3–4 HD)        (1 HD)
       └──────► F3 Latência (3–5 HD) ─────┘
```

F1 desbloqueia F2 e F4 (sem ver a tela, o copiloto de programação não existe).
F3 corre em paralelo a partir de F2.

## 7. Riscos e restrições

| Risco | Impacto | Observação |
|---|---|---|
| **Wayland limita overlay** | Alto | Posição e "always on top" não são portáteis; depende de `layer-shell` do compositor |
| **Portal exige consentimento** | Médio | É uma qualidade, não um defeito — mas muda a experiência (uma permissão por sessão) |
| **Atalho global no Wayland** | Médio | `pynput` inicia, mas captura eventos via X11/XWayland; teclas em apps Wayland nativos podem não chegar |
| **Latência de 300 ms** | Médio | Cluely usa serviço na nuvem; com Whisper local a meta realista é 1–2 s, não 300 ms. **Não prometer paridade** |
| **Custo de IA** | Médio | Copiloto ambiente chama o modelo com muito mais frequência que uma reunião pontual |

## 8. Decisão pendente: até onde imitar a referência

O Cluely se posiciona explicitamente como **indetectável** — não aparece na
lista de participantes nem no compartilhamento de tela, e o material de
divulgação sugere uso em entrevistas e negociações.

Vale separar duas coisas:

- **Overlay local que não polui o compartilhamento de tela**: útil e sem
  problema — são as suas anotações, ninguém precisa vê-las.
- **Ocultar deliberadamente da outra parte que há uma IA assistindo**: é uma
  escolha de produto com implicações de consentimento, e em várias jurisdições
  gravar o áudio de terceiros exige aviso.

Este plano constrói o **copiloto**; a "indetectabilidade" como objetivo de
produto fica como decisão explícita do dono do projeto, não como padrão herdado
da referência.

- [ ] Construir só o copiloto (recomendado)
- [ ] Perseguir também a indetectabilidade
