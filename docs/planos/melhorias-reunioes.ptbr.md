# Plano — Melhorias de componentes e do fluxo de Reuniões

> Objetivo: reduzir o acoplamento da tela de Reuniões (hoje um "god object"),
> agrupar os componentes em unidades coesas e otimizar o fluxo de uso e de
> recursos. Esforço em **homem-dia (HD)**; alocação/cronograma é decisão de
> liderança.

## 1. Diagnóstico (medido no código, não impressão)

| Indicador | Valor atual | Comentário |
| --- | --- | --- |
| `gui/views/transcricoes_view.py` | **2221 linhas** | ~65% de todo o módulo de reuniões (3386 linhas) |
| Métodos na view | **103** | UI, orquestração de IA, persistência e áudio no mesmo lugar |
| Atributos de estado (`self._*`) | **129** | Estado espalhado, sem modelo coeso |
| Widgets (`self.x`) | **56** | Muitos widgets manipulados por índice/visibilidade |
| Workers de QThread orquestrados pela view | **6 tipos** | Transcriber, LiveTranscriber, LiveExtract, LiveAsk, Analyze, Vision |
| Referências aos 2 campos de transcrição | **31** | `transcript_edit` (estático) x `live_transcript_edit` (ao vivo) |
| Chaves duplicadas no `i18n_catalog.py` | **17** | Ex.: "Excluir", "Gravar", "Histórico", "Copiar" |

Sintomas que o usuário sente: fluxo com dois campos de transcrição que se
alternam por visibilidade, painel "Ao vivo" fora da numeração das etapas
(1 Preparar → 2 Gravar → **?** → 3 Resultado) e reprocessamentos de contexto
a cada extração.

## 2. Eixos de melhoria

### A. Agrupamento de componentes (o maior ganho estrutural)

- **A1 — Extrair widgets compostos da view.** Mover os blocos já bem
  delimitados para `gui/meetings/` como widgets próprios, com sinais claros:
  `DestinationBar` (workspace+projeto), `PreparationCard` (tipo, pauta,
  contexto), `RecordingCard` (áudio recolhível, gravar, ao vivo),
  `LiveAssistantPanel` (transcrição ao vivo + abas + perguntar),
  `ResultCard` (transcrição, resumo, ações), `HistoryPanel` (busca, lista,
  menu de contexto, estado vazio). A view vira composição + orquestração.
  **~5 HD.**
- **A2 — Modelo de estado da reunião.** Trocar os ~129 atributos soltos por um
  `MeetingSession` (dataclass) com `transcript`, `prep`, `context_items`,
  `live_state`, `rec_id`, `md_source`. Um único ponto para salvar/restaurar
  (hoje o autosave depende de vários campos). **~2 HD.**
- **A3 — Serviço de persistência.** Tirar as queries SQLAlchemy da view para
  `transcricoes/repository.py` (`save_session`, `load_session`, `list_history`,
  `archive`, `delete`, `reorder`). **~1,5 HD.**
- **A4 — Orquestrador de IA.** Concentrar os 6 workers num
  `MeetingAgentService` que expõe `transcribe()`, `extract()`, `ask()`,
  `analyze()`, `see_screen()` e emite sinais; a view só reage. **~2 HD.**

### B. Fluxo de reuniões (UX)

- **B1 — Unificar a transcrição.** Um único campo, com um indicador de "ao
  vivo" quando estiver gravando, no lugar de dois campos alternados por
  visibilidade (31 referências hoje). Remove a classe inteira de bugs de
  "campo errado visível". **~1,5 HD.**
- **B2 — Encaixar o assistente no fluxo.** O painel "Ao vivo" vira a etapa
  numerada **3. Assistente** (Resultado passa a 4), ou é embutido na etapa
  2 durante a gravação — hoje ele aparece solto entre as etapas. **~1 HD.**
- **B3 — Barra de progresso do fluxo.** Um indicador no topo mostrando em que
  passo a reunião está (preparada → gravando → transcrevendo → analisada),
  com o estado atual destacado. **~1 HD.**
- **B4 — Ações contextuais.** Habilitar/ocultar ações conforme o estado (ex.:
  "Criar tarefas" só quando há ações extraídas; "Exportar" só com conteúdo),
  em vez de botões sempre visíveis e às vezes inertes. **~0,5 HD.**

### C. Otimização de recursos

- **C1 — Gravar áudio em disco (streaming).** Hoje o buffer inteiro fica em
  RAM (`_chunks.append`), ~230 MB/hora por stream, porque o WAV final precisa
  dele. Escrever incrementalmente no arquivo e manter só a janela do ao vivo.
  **~2 HD.** *(A cópia repetida por janela já foi corrigida.)*
- **C2 — Cache do contexto da reunião.** `_meeting_context()` é chamado em 5
  pontos, refazendo queries a cada extração; cachear e invalidar por evento
  (troca de projeto, novo anexo, edição da preparação). **~0,5 HD.**
- **C3 — Extração incremental de verdade.** Enviar só o delta da transcrição
  com um resumo do estado, em vez do estado inteiro a cada ciclo — reduz
  tokens e latência do ao vivo. **~1 HD.**

### D. Higiene

- **D1 — Deduplicar o catálogo i18n.** 17 chaves repetidas (a última vence,
  então há traduções mortas); consolidar e adicionar um teste que falha se
  houver duplicata. **~0,5 HD.**
- **D2 — Testes de regressão do fluxo.** Cobrir o que já quebrou antes:
  abrir do histórico troca de reunião, respostas manuais preservadas na
  reanálise, autosave/restauração do `live_state_json`, reset de "Nova
  reunião". **~1,5 HD.**

## 3. Ordem sugerida

Cada fase entrega valor sozinha e reduz o risco da seguinte:

1. **Fase 1 — Segurança para refatorar** (D2, D1) — **~2 HD.**
   Testes antes de mexer na estrutura.
2. **Fase 2 — Componentização** (A1, A2) — **~7 HD.**
   O grosso do ganho de manutenção; a view deixa de ser god object.
3. **Fase 3 — Camadas** (A3, A4) — **~3,5 HD.**
   Persistência e IA fora da UI.
4. **Fase 4 — Fluxo** (B1, B2, B3, B4) — **~4 HD.**
   Fica bem mais simples depois da componentização.
5. **Fase 5 — Recursos** (C1, C2, C3) — **~3,5 HD.**

**Total estimado: ~20 HD.**

## 4. Riscos e mitigação

- **Refatorar sem rede** — mitigado pela Fase 1 (testes primeiro) e por
  manter os nomes de widgets/handlers públicos durante a extração.
- **Regressão visual** — validar cada fase com render offscreen das telas
  (mesmo método já usado nos prints da documentação).
- **Escopo crescer** — as fases são independentes; dá para parar depois de
  qualquer uma sem deixar o código pela metade.

## 5. Decisão pendente

- [ ] Aprovar o plano e a ordem das fases.
- [ ] Definir até onde ir agora (sugestão: Fases 1–2, ~9 HD, que já resolvem
      o god object e deixam a base pronta para o resto).
