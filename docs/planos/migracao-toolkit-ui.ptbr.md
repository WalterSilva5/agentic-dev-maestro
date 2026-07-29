# 11 — Decisão de toolkit de UI: Flutter vs Java vs rota web

> Objetivo: decidir para qual tecnologia migrar a interface do `local-client`,
> hoje em **PySide6/Qt6**, com a meta de um visual **moderno** e a saída do Qt.
> Este documento levanta a restrição que domina a decisão, compara as opções
> (Flutter, Java, rota web) e detalha o trabalho por tarefas, com esforço em
> **homem-dia (HD)**. Alocação e cronograma são decisão de liderança.
>
> Complementa o [Plano 10 — front-end responsivo](migracao-frontend-responsivo.ptbr.md),
> que já recomendou a rota web; aqui a comparação é reaberta a pedido para
> incluir **Flutter** e **Java** explicitamente, com plano de execução para o
> caminho que for escolhido.

## 1. A restrição que domina a decisão

A tela de **Reuniões** depende de dois recursos que **só existem num processo
nativo/local**:

1. **Captura de áudio do sistema** — `parec`/PulseAudio (no futuro, portal
   PipeWire no Wayland). O navegador não captura o áudio de outros aplicativos.
2. **Transcrição offline** — faster-whisper/ctranslate2, rodando no processo
   local.

Consequência central: **nenhuma escolha de toolkit remove essa parte.** Em
Flutter, Java ou web, o áudio e o Whisper continuam num helper nativo — hoje o
próprio processo Python. Portanto a decisão de UI **não** é sobre "quem resolve
o áudio", e sim sobre **custo de reescrita** e **teto de qualidade visual**,
mantendo o núcleo de captura/IA onde já funciona (Python).

## 2. O ponto de partida real (o que já existe)

- **Desktop atual**: `local-client` em PySide6/Qt6 + **FastAPI** embarcado (9777).
- **Web UI**: **React 18 + Vite** (`local-client/webui/`) com **16 telas
  funcionando**, servida pela própria API. É um front moderno **já pronto**.
- **Shell de desktop**: `maestro_local/desktop_shell.py` (**pywebview**) já
  abre a web UI numa janela nativa (E1 do Plano 10, concluído).
- **Camadas agnósticas de UI** extraídas recentemente e reutilizáveis por
  qualquer front via API: `transcricoes/repository.py` (persistência),
  `transcricoes/agent_service.py` (orquestração de IA), `transcricoes/session.py`
  (`MeetingSession`). Ou seja, a lógica de daemon **já está isolada da UI Qt**.
- **Lacuna**: **Reuniões** é a única tela grande ainda só-Qt (por causa da
  restrição da seção 1). Praticar Inglês e o cofre KeePass são desktop-only por
  natureza.

## 3. Opções

### Opção F — Flutter (desktop + mobile)
- **Como**: reescrever as ~16 telas em Flutter Desktop; o áudio/Whisper seguem
  num **sidecar Python** acessado por API/WebSocket local (ou plugins nativos/FFI
  para PulseAudio e ctranslate2 — mais caro e frágil). A camada de IA (Python)
  permanece como serviço.
- **Prós**: toolkit moderno e responsivo; **um código para desktop e mobile**;
  animações e componentes ricos.
- **Contras**: **reescrita completa** da UI; **descarta** o investimento em React
  + FastAPI (as 16 telas já feitas); nova linguagem (Dart) e toolchain; a ponte
  de áudio/estado ao vivo precisa ser reconstruída para Dart↔Python. É a opção
  **mais cara**.
- **Ganho sobre a web**: mobile nativo real e componentes nativos; para
  **desktop**, o ganho visual sobre uma web UI bem estilizada é pequeno.

### Opção J — Java (Swing/JavaFX)
- **Como**: reescrever a UI em Swing ou JavaFX; áudio/Whisper seguem num sidecar
  Python (Java não tem PulseAudio/ctranslate2 nativos práticos).
- **Prós**: JVM robusta; se a equipe já domina Java, curva menor.
- **Contras**: **Swing é datado** (estética anos 2000) e **JavaFX é pesado e
  também datado** frente a web/Flutter. **Não atende à meta de "moderno"** — é
  provável regressão visual em relação à web UI atual. Também é reescrita
  completa e descarta o investimento em React/FastAPI.
- **Veredito**: **não recomendada** para o objetivo declarado (interface
  moderna). Documentada aqui apenas para registro da comparação.

### Opção W — Rota web (React já existente) + shell nativo
- **Como**: consolidar na web UI React que **já existe**; o app Python vira
  **daemon local** (captura + Whisper + IA) expondo **API + WebSocket**;
  encapsular num shell nativo (**pywebview** já feito; **Tauri** como evolução
  para binário menor/tray/atalho global).
- **Prós**: **reaproveita tudo** (React + FastAPI + camadas agnósticas já
  extraídas); responsividade real (CSS/flex/grid); a lógica pesada fica onde já
  funciona; migração **incremental** (uma tela por vez, já quase toda pronta).
- **Contras**: para Reuniões ao vivo, precisa de **streaming por WebSocket**; o
  observador de tela/captura seguem nativos no daemon; "cara de app" depende do
  shell (pywebview/Tauri).
- **Custo**: **o menor** — a maior parte é ligar telas React a endpoints/WS.

## 4. Comparação (resumo)

| Critério | F — Flutter | J — Java (Swing/JavaFX) | W — Rota web |
|---|---|---|---|
| Modernidade visual (desktop) | Alta | Baixa/Média | Alta |
| Mobile nativo | Sim | Não (prático) | PWA/responsivo |
| Reaproveita React + FastAPI | Não | Não | **Sim** |
| Reaproveita camadas agnósticas (repo/agent/session) | Via API | Via API | **Direto/Via API** |
| Resolve áudio/Whisper sem Python | Não | Não | Não |
| Custo de reescrita | **Muito alto** | Alto | **Baixo/Médio** |
| Nova linguagem/toolchain | Dart | — | — |

## 5. Recomendação

1. **Rota web (W)** continua sendo a recomendação técnica: mesmo teto visual de
   Flutter no desktop, custo muito menor, e reaproveita o que já existe. A "cara
   de app" vem do shell (pywebview hoje; Tauri como próximo passo).
2. **Flutter (F)** só se o requisito for **app mobile nativo** como produto de
   primeira classe — aí o ganho justifica a reescrita. Para desktop puro, não
   compensa.
3. **Java (J)**: descartada para a meta de interface moderna.

## 6. Plano de execução — Rota web (W), recomendada

Fases por tarefas e objetivos; esforço em HD.

- **W0 — Shell nativo como padrão** (~1 HD): tornar o pywebview o modo
  recomendado de abrir o app (documentar em README/install); Reuniões abre a
  janela Qt legada enquanto W2/W3 não concluem.
- **W1 — Streaming ao vivo na API** (~3–5 HD): expor por **WebSocket** a
  transcrição e o estado ao vivo (itens/plano/perguntas), consumindo
  `agent_service`/`session` já existentes.
- **W2 — Reuniões na web** (~5–8 HD): recriar a tela em React consumindo o WS +
  endpoints (preparação, contexto, workspace/projeto, Q&A, resultado). Paridade
  com a tela Qt.
- **W3 — Daemon headless de captura/Whisper** (~2–3 HD): rodar captura + Whisper
  sem a GUI Qt, como serviço do processo da API.
- **W4 — Paridade e aposentadoria do Qt** (~3–5 HD + conforme escopo): migrar as
  telas restantes e desativar a GUI Qt quando houver paridade; decidir Tauro vs
  pywebview para empacotamento final.

**Total estimado (W): ~14–21 HD**, sem contar polimento incremental de telas.

## 7. Plano de execução — Flutter (F), caso escolhido

Só se o produto exigir mobile nativo. Esforço em HD.

- **F0 — Prova de conceito** (~2–3 HD): app Flutter Desktop mínimo consumindo a
  API FastAPI atual (uma tela: Dashboard) para validar a ponte HTTP/WS.
- **F1 — Sidecar de áudio/IA** (~3–5 HD): definir o contrato Dart↔Python
  (API/WebSocket) para captura, Whisper e estado ao vivo; manter o núcleo em
  Python (FFI para PulseAudio/ctranslate2 fica como pesquisa, não como base).
- **F2 — Design system Flutter** (~3–5 HD): tema, componentes base (cards,
  navegação, formulários) equivalentes ao que já existe na web.
- **F3 — Reescrita das telas** (~1–2 HD por tela × 16 ≈ 16–32 HD): portar cada
  tela consumindo a API; Reuniões consome o WS do F1.
- **F4 — Empacotamento** (~3–5 HD): build desktop (Linux/Windows) e, se for o
  caso, mobile; distribuição.

**Total estimado (F): ~27–50 HD**, além de re-resolver a ponte de áudio fora do
ecossistema Python. É o caminho **mais caro**.

## 8. Riscos e pontos de decisão

- **Áudio nativo**: em qualquer opção a captura fica no daemon Python
  (parec/PulseAudio; PipeWire no futuro). Não há como o navegador nem um front
  Flutter/Java capturar áudio de sistema sem helper nativo.
- **Custo de manter dois fronts** durante a transição: mitigado migrando **uma
  tela por vez** e mantendo a API como fonte única de verdade.
- **Empacotamento** (rota web): pywebview (já feito, Python puro) vs Tauri
  (binário menor, tray/atalho global) — decisão para W4.
- **Dart/Flutter** (rota F): nova toolchain e linguagem; peso da reescrita das 16
  telas já prontas em React.

## 9. Decisão

- [ ] **W — Rota web** (recomendada): consolidar na web UI React + daemon Python
  (WS) + shell nativo (pywebview → Tauri).
- [ ] **F — Flutter**: reescrita para desktop + mobile nativo (justificada só se
  mobile for requisito de produto).
- [x] **J — Java**: descartada (não atende à meta de interface moderna).

> Marcar a opção escolhida ao bater o martelo; a execução segue a seção
> correspondente (6 ou 7).
