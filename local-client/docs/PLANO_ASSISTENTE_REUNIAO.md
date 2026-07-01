# Plano — Assistente de Reunião em Tempo Real

Evolução do módulo **Transcrições** (`maestro_local/transcricoes/`) de "grava → para →
transcreve → resume" para **acompanhamento ao vivo** durante a reunião, com ponte
direta para o board. Esforço em homem-dia (hd); staffing/cronograma fica a critério da
liderança.

---

## 1. Objetivo

Durante uma reunião/estudo, o app:
- Transcreve **continuamente** (painel de transcrição ao vivo);
- Extrai **incrementalmente** ações, decisões e perguntas em aberto;
- Permite **perguntar à reunião** ("o que decidimos sobre X?");
- Ao fim, transforma as **ações em tarefas** no board com 1 clique.

Diferencial: tudo local (áudio + Whisper) + IA com o provedor já configurado
(LM Studio/opencode/etc.), sem enviar áudio para a nuvem.

---

## 2. Experiência (UX)

Layout da tela Transcrições em modo "ao vivo" (3 colunas):
- **Esquerda**: controles + histórico (como hoje).
- **Centro**: transcrição ao vivo rolando, com marcação de blocos por pausa (VAD).
- **Direita**: painel dinâmico com abas **Ações · Decisões · Perguntas**, atualizado a
  cada bloco. Caixa **"Perguntar à reunião"** no rodapé.

Ao parar: resumo estruturado (como hoje) + botão **"Criar tarefas das ações"** e
**"Salvar no Meu Dia"**.

---

## 3. Arquitetura (como encaixa no código atual)

| Camada | Onde | O que muda |
|---|---|---|
| Captura | `transcricoes/audio.py` | Já é contínua (`parec`). Expor um buffer rolante (ring buffer) consumível sem parar a gravação. |
| Transcrição | `transcricoes/transcriber.py` | Novo `LiveTranscriber` (QThread) que a cada janela pega o buffer, aplica VAD e transcreve só o trecho novo; emite `partial_text`. |
| IA ao vivo | `transcricoes/live_assistant.py` (novo) | Debounce: a cada N segundos ou M palavras novas, manda o transcript acumulado ao provedor e faz **extração incremental** (merge com o que já foi extraído). Reusa `ai/providers.build_chat_model`. |
| Perguntar à reunião | mesmo módulo | Chamada pontual com o transcript como contexto. |
| Ações → tarefas | `api/app.py` + view | Endpoint/каminho para criar tarefas a partir das ações (usa `POST /api/tasks` já existente). |
| UI | `gui/views/transcricoes_view.py` | Modo ao vivo (3 colunas), painéis reativos, threads não bloqueiam a GUI. |

Princípios: manter tudo em **QThreads** (transcrição e IA nunca no thread da GUI);
**degradar com elegância** (se não houver provedor de IA, só a transcrição ao vivo roda).

---

## 4. Fases e tarefas

> Status: Fases 1–4 **implementadas** (verificadas em smoke test offscreen). Falta
> exercício ponta a ponta com áudio real numa máquina com microfone.

### Fase 1 — Transcrição ao vivo (~2–3 hd) ✅
- [x] Buffer rolante no `audio.py` (`snapshot_audio()` lê sem parar a gravação; mixagem refatorada em `_mix`).
- [x] `LiveTranscriber` (QThread): janela deslizante (10s) + VAD, emite `partial`.
- [x] Painel de transcrição ao vivo na tela, com autoscroll.
- [x] Constantes de janela/modelo (`LIVE_*`); modo ao vivo usa `base` por padrão.

### Fase 2 — Extração incremental ao vivo (~2 hd) ✅
- [x] `live_assistant.py`: `LiveExtractWorker` com extração incremental (recebe "já extraído" + "novo trecho", devolve o merge; contexto limitado).
- [x] Painel Ações/Decisões/Perguntas reativo (abas com contadores).
- [x] "Perguntar à reunião" (`LiveAskWorker`, resposta pontual com contexto do transcript).
- [x] Debounce por tempo (`LIVE_AI_MIN_SECONDS`) OU palavras novas (`LIVE_AI_MIN_WORDS`), 1 extração por vez.

### Fase 3 — Ponte reunião → board (~1 hd) ✅
- [x] Botão "Criar tarefas das ações": cada ação vira tarefa (tipo CHORE, `requires_human=True`), no projeto escolhido.
- [x] Fallback: usa ações do assistente ao vivo ou, se não houver, do resumo de IA final.

### Fase 4 — Polimento (~1 hd) ✅
- [x] Indicadores de estado (transcrevendo / sem IA / pensando).
- [x] Reunião longa: contexto enviado à IA limitado (`_clamp_transcript`).
- [x] Toggle "Assistente ao vivo"; painel só aparece durante a gravação ao vivo.
- [ ] Screenshot final com áudio real (pendente — precisa de máquina com microfone).

**Total estimado: ~6–7 hd.** Fases 1→2→3 já entregam valor de ponta a ponta; a 3 sozinha (sem tempo real) é a de melhor custo/benefício se quiser começar leve.

---

## 5. Dicas técnicas

- **Janelamento com overlap**: transcreva janelas com ~1s de sobreposição e faça
  dedupe do texto repetido nas bordas — evita cortar palavras entre blocos.
- **VAD para cortar em pausas**: o faster-whisper já tem `vad_filter=True`; use as
  pausas para fechar blocos "estáveis" (não reprocessar trecho já confirmado).
- **Modelo por modo**: `small` para o resumo final (precisão), `base`/`tiny` para o
  ao vivo (latência). Deixar configurável em Configurações → Transcrições.
- **Locale C.UTF-8 no worker**: manter o fix já aplicado (Qt reseta o LC_CTYPE e o
  PyAV quebra) — vale para qualquer novo worker de áudio.
- **Debounce da IA**: não chamar o provedor a cada palavra; disparar a cada ~15s ou
  ~40 palavras novas. Cancelar chamada anterior se chegar bloco novo.
- **Contexto limitado**: em reunião longa, enviar só a "janela recente + resumo
  acumulado" para não estourar o contexto/custo do provedor.
- **Tudo em QThread**: transcrição e IA fora do thread da GUI; comunicar via signals.
- **Falha graciosa**: sem provedor de IA → só transcrição ao vivo; sem `parec` →
  aviso claro (já existe o padrão no código).

## 6. Dicas de UX

- Mostrar o **estado** com clareza (chip "IA pensando…", "transcrevendo…").
- Ações/decisões extraídas devem ser **editáveis** antes de virar tarefa (a IA erra).
- Um clique para **descartar** uma ação sugerida.
- Atalho para pausar só a **extração de IA** (economiza recurso) mantendo a transcrição.

---

## 7. Funcionalidades complementares (roadmap que faz sentido)

Itens que conversam com o resto do app e potencializam o assistente de reunião:

- **Ponte ações → tarefas** (~1–2 hd) — já incluída na Fase 3; vale como feature
  independente mesmo sem tempo real.
- **Digest proativo do assistente** (~3 hd) — resumo automático (manhã/fim do dia)
  com prioridades, vencidas e itens parados; mostrar no Dashboard. Reusa a lógica da
  skill `maestro-daily-report`.
- **Busca global de verdade** (~2 hd) — hoje o Ctrl+K só acha tarefas; expandir para
  notas, **transcrições** e comentários via SQLite FTS.
- **Agenda/calendário por prazo** (~2 hd) — visão de calendário das tarefas por
  `due_date` (hoje só lista de vencidas).
- **Tarefas recorrentes / templates de subtarefas** (~2 hd).
- **Pomodoro ligado à tarefa** (~1 hd) — registrar tempo gasto por tarefa e alimentar
  o cycle time real das Métricas.
- **Web em tempo real** (~2 hd) — WebSocket para board/dashboard atualizarem quando um
  agente mexe via API (hoje precisa recarregar).
- **Diarização "quem falou"** (~4 hd, mais pesado) — `pyannote` + modelo; melhora muito
  a ata de reunião, porém é o item mais custoso e o único que puxa dependência grande.

---

## 8. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Latência do Whisper em CPU | Modelo menor no ao vivo; janela configurável; indicador de estado. |
| Latência/custo do provedor de IA | Debounce + contexto limitado; extração incremental (não reprocessa tudo). |
| Reunião longa estoura contexto | Resumir o miolo; enviar só janela recente + resumo. |
| IA erra ações/decisões | Painel editável + descartar antes de virar tarefa. |
| GUI travar | Todo processamento em QThread; comunicação por signals. |

## 9. Critérios de aceite

- Transcrição aparece ao vivo com atraso aceitável (poucos segundos).
- Ações/decisões/perguntas se atualizam durante a reunião sem travar a GUI.
- "Perguntar à reunião" responde com base no que já foi dito.
- Ao parar, "Criar tarefas das ações" gera tarefas corretas no board.
- Sem provedor de IA, a transcrição ao vivo continua funcionando.
