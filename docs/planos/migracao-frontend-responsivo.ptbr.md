# 10 — Plano de front-end responsivo (Reuniões e além)

> Objetivo: deixar a interface (em especial **Reuniões**) genuinamente responsiva
> e decidir se vale migrar de PySide6/Qt para outra tecnologia (Flutter, web…).
> Este documento levanta o problema, avalia as opções e recomenda um caminho.
> Esforço estimado em **homem-dia (HD)**; alocação/cronograma é decisão de liderança.

## 1. Contexto atual

- **Desktop**: `local-client` em **PySide6/Qt6** (GUI) + **FastAPI** embarcado (porta 9777).
- **Web**: já existe uma **web UI em React 18 + Vite** (`local-client/webui/`), servida
  pela própria API — ou seja, **já há um front responsivo no projeto**.
- **Camada de IA**: LangChain/LangGraph sobre endpoints OpenAI-compat (`ai/llm.py`).
- **Reuniões** é **desktop-only** por dois motivos técnicos:
  1. Captura de **áudio do sistema** via `parec`/PulseAudio (o navegador não acessa
     o áudio de outros apps);
  2. **Transcrição offline** com faster-whisper (roda no processo local).

## 2. Problema

O Qt não tem um modelo de layout responsivo declarativo (não há media queries/CSS).
Tudo é manual: `QSplitter`, políticas de tamanho, larguras mínimas. Conforme a tela
de Reuniões cresceu (preparação, contexto, observador de tela, seletores de
workspace/projeto), os componentes passaram a **quebrar em larguras menores**
(itens sobrepostos, botões cortados, sem rolagem).

## 3. Ganhos já aplicados (curto prazo, Opção A)

Sem trocar de stack, a tela de Reuniões recebeu:

- **Rolagem vertical** da coluna de conteúdo (`QScrollArea`) — nada mais se sobrepõe.
- **`FlowLayout`** nas barras de ações (botões/combos quebram para a linha seguinte).
- **Breakpoint**: abaixo de ~820px o **histórico colapsa** e some, com botão
  "☰ Histórico" para reexibir; o conteúdo passa a ocupar a largura toda.
- **Larguras mínimas relaxadas** (coluna direita, combos) e altura mínima do painel
  ao vivo, evitando corte do splitter interno.

Isso resolve os sintomas imediatos. O `FlowLayout` e o padrão de breakpoint são
**reaproveitáveis** nas demais telas do desktop.

## 4. Opções de médio/longo prazo

### Opção A — Continuar em Qt, tornando-o responsivo
- **Como**: aplicar `FlowLayout` + breakpoints (colapsar painéis) + `QScrollArea`
  nas demais telas; extrair um utilitário de "responsividade" comum.
- **Prós**: zero stack novo; mantém captura de áudio e Whisper nativos; incremental.
- **Contras**: responsividade em Qt é sempre manual/verbosa; teto de qualidade
  visual menor que web/Flutter.
- **Esforço**: ~1 HD por tela para adequar (o grosso da infra já existe).

### Opção B — Migrar o desktop para **Flutter**
- **Como**: reescrever a UI em Flutter Desktop; a captura de áudio e o Whisper
  precisariam de **plugins nativos/FFI** (PulseAudio/PipeWire, ctranslate2) ou
  continuar em um processo Python acessado via API local; a camada de IA (Python)
  permaneceria como serviço.
- **Prós**: toolkit moderno e responsivo; um código para desktop + mobile.
- **Contras**: **reescrita completa** da UI; **re-resolver** áudio nativo e Whisper
  fora do ecossistema Python; descarta o investimento em React/FastAPI; curva de
  aprendizado (Dart). É a opção **mais cara**.
- **Esforço**: **muito alto** (dezenas de HD só para paridade de Reuniões).

### Opção C — Consolidar na **web UI React já existente** + daemon local (recomendada)
- **Ideia**: a UI responsiva **já existe** em React. O único bloqueio é
  áudio/Whisper no navegador. Solução: manter o app Python como **daemon local**
  (captura + Whisper + camada de IA) expondo **API + WebSocket**; o React consome e
  renderiza a UI responsiva (inclusive Reuniões, com transcrição ao vivo via WS).
- **Prós**: reaproveita **todo** o investimento em React + FastAPI + camada de IA;
  responsividade real (CSS/flex/grid, media queries); a lógica pesada (áudio, IA)
  fica onde já funciona (Python).
- **Contras**: precisa de **streaming** (WebSocket) da transcrição/estado ao vivo;
  o observador de tela e a captura seguem nativos (no daemon); empacotar como app
  de desktop (ver Opção D) para janela nativa + atalho global + tray.
- **Esforço**: **médio** (a maior parte é ligar telas React a endpoints/WS já
  existentes ou fáceis de expor).

### Opção D — Encapsular a web UI num shell de desktop leve
- **Como**: **pywebview** (Python puro, casa com o backend atual), **Tauri**
  (Rust, binário pequeno) ou **Electron** (mais pesado) para dar janela nativa,
  atalho global e bandeja à web UI da Opção C.
- **Prós**: experiência "app de verdade" reusando a UI web; migração gradual
  (uma tela por vez migra do Qt para a web).
- **Contras**: mais uma dependência de empacotamento; IPC daemon↔shell.
- **Esforço**: **baixo-médio** para o esqueleto (pywebview é o mais rápido dado o
  stack Python).

## 5. Recomendação

1. **Agora (feito/continuar)** — Opção **A**: finalizar a responsividade das telas
   Qt reusando `FlowLayout` + breakpoints. Entrega valor imediato sem risco.
2. **Direção estratégica** — Opção **C + D**, **não** Flutter: mover a UI para a
   **web UI React que já existe**, com o app Python como **daemon local** de captura
   + Whisper + IA, e encapsular num shell leve (**pywebview** como primeira escolha).
   Racional: Flutter obrigaria a **reescrever a UI e re-resolver o áudio nativo**
   fora do Python; a rota web **reaproveita** React + FastAPI + camada de IA e dá
   responsividade real de graça. A restrição de áudio nativo permanece em Python
   nos dois caminhos — então o caminho web é estritamente menos custoso.

## 6. Roadmap sugerido (por fases, esforço em HD)

- **Fase 0 — Responsividade Qt (curto prazo)**: aplicar `FlowLayout`/breakpoints nas
  telas restantes. ~1 HD/tela.
- **Fase 1 — Streaming ao vivo na API**: expor WebSocket de transcrição/estado ao
  vivo (hoje só desktop). ~3–5 HD.
- **Fase 2 — Reuniões na web UI**: recriar a tela de Reuniões em React consumindo o
  WS + endpoints (preparação, contexto, workspace/projeto, Q&A). ~5–8 HD.
- **Fase 3 — Shell de desktop (pywebview)**: janela nativa + atalho global + tray;
  daemon headless de captura/Whisper. ~3–5 HD.
- **Fase 4 — Paridade e migração gradual**: migrar as demais telas do Qt para a web,
  aposentando a GUI Qt quando houver paridade. Esforço conforme escopo.

## 7. Riscos e pontos de decisão

- **Áudio nativo**: em qualquer opção a captura fica no daemon Python (parec/PulseAudio;
  no futuro, portal PipeWire para Wayland). Não há como o navegador capturar áudio de
  sistema sem um helper nativo.
- **Empacotamento**: escolher entre pywebview (Python, mais simples) e Tauri (binário
  menor, mais robusto) — decisão para o início da Fase 3.
- **Custo de manter dois fronts** durante a transição (Qt + web): mitigado migrando
  **uma tela por vez** e mantendo a API como fonte única de verdade.

## 8. Decisão pendente (liderança)

- [ ] Aprovar a direção **web (C+D)** vs **Flutter (B)** vs **só melhorar Qt (A)**.
- [ ] Se web: escolher o shell (**pywebview** recomendado) para a Fase 3.
