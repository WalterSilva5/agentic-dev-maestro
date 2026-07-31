# 13 — Plano de implementação do front-end Flutter

> Objetivo: reescrever a interface do `local-client` em **Flutter**, mantendo o
> **backend Python** como daemon local (API + WebSocket). Tudo que o Flutter não
> suporta bem (captura de áudio do sistema, Whisper offline, KeePass, atalhos
> globais, camada de IA) **permanece em Python** e é exposto por API.
>
> Este documento é o plano de execução: tarefas, subtarefas e roadmap. Esforço em
> **homem-dia (HD)**; alocação e cronograma são decisão de liderança.
>
> Decisão de partida: [Plano 11 — toolkit de UI](migracao-toolkit-ui.ptbr.md)
> recomendava a rota web; a escolha por **Flutter** foi tomada e este plano
> detalha a execução dessa opção (a seção 8 registra o que muda em relação ao 11).

## 1. Situação medida (base do plano)

Levantado no código, não estimado:

| Item | Medida |
|---|---|
| Toolchain Flutter | **3.44.6 stable**, Dart 3.12.2, Linux desktop **já habilitado** |
| Projeto Flutter existente | **Nenhum** (greenfield) |
| Endpoints da API | **127** (47 GET, 45 POST, 17 DELETE, 11 PATCH, 7 PUT) |
| Contrato OpenAPI | **3.1.0**, 91 paths, 54 schemas — **cliente Dart pode ser gerado** |
| Autenticação | **Nenhuma**; workspace é **estado global do servidor** (`POST /api/workspaces/active`) |
| Telas Qt | 21 views, **13.286 LOC** |
| Web UI React (referência pronta) | 16 telas, **3.249 LOC** |
| **Sem cobertura de API** | **Reuniões** (só settings do Whisper) e **Vault** (KeePass) |

Dois fatos moldam o plano:

1. **O OpenAPI cobre quase tudo.** 91 paths tipados permitem **gerar** o cliente
   Dart + modelos, em vez de escrever à mão. Reduz muito o custo e o risco de
   divergência de contrato.
2. **Reuniões não tem API nenhuma.** É a única funcionalidade grande 100% presa
   ao Qt (captura de áudio + Whisper + estado ao vivo). É o maior bloco de
   trabalho **de backend** do plano — e precisa existir antes da tela Flutter.

## 2. Arquitetura alvo

```
┌────────────────────────────────────────┐
│  Flutter (UI)                          │   Linux desktop (mobile: futuro)
│  · telas, navegação, estado            │
│  · cliente gerado do OpenAPI           │
└──────────────┬─────────────────────────┘
               │  HTTP + WebSocket (127.0.0.1:9777)
┌──────────────▼─────────────────────────┐
│  Daemon Python (FastAPI + uvicorn)     │   fonte única de verdade
│  · 127 endpoints + WS ao vivo          │
│  · SQLite por workspace                │
│  · captura de áudio (parec/PulseAudio) │ ← nativo, fica em Python
│  · Whisper offline (ctranslate2)       │ ← nativo, fica em Python
│  · LangChain/LangGraph (IA)            │ ← fica em Python
│  · KeePass, atalhos globais, captura   │ ← nativo, fica em Python
└────────────────────────────────────────┘
```

**Regra de corte:** o Flutter só desenha e navega. Qualquer coisa que toque
áudio, modelo local, sistema de arquivos do usuário ou provedor de IA fica no
daemon e vira endpoint.

## 3. O que permanece em Python (e por quê)

| Recurso | Por que não vai para o Flutter |
|---|---|
| **Captura de áudio do sistema** | `parec`/PulseAudio captura o áudio de *outros apps*. Pacotes Dart de áudio cobrem microfone, não loopback/monitor no Linux. |
| **Transcrição Whisper** | faster-whisper/ctranslate2 é C++ com binding Python. Portar para FFI em Dart é caro e frágil. |
| **Camada de IA** | LangChain/LangGraph + `ai/llm.py` (structured output, fallback, caches) já resolvidos em Python. |
| **Cofre KeePass** | `pykeepass`. Reimplementar manuseio de cripto em Dart é risco desnecessário. |
| **Atalhos globais** | `pynput`. Suporte a atalho global no Linux/Wayland pelo Flutter é limitado. |
| **Captura de monitor** | Observador de tela usa API de tela do Qt. Flutter desktop não expõe equivalente. |
| **Sync Obsidian / instalação de skills** | Escrita no sistema de arquivos do usuário, já implementada. |
| **Banco (SQLite/SQLAlchemy)** | Fonte de verdade; o Flutter nunca fala com o banco direto. |

## 4. Fases, tarefas e subtarefas

Cada item é uma tarefa; os `·` são subtarefas.

### F0 — Fundação (~5–7 HD)

- [ ] **F0.1 — Criar o projeto Flutter** (~0,5 HD)
  - · `flutter create` com plataforma Linux desktop; estrutura de pastas
    (`lib/{core,data,features,ui}`)
  - · Definir Dart SDK mínimo e fixar a versão do Flutter (evita drift)
  - · Lint (`flutter_lints`) e formatação no CI local
- [ ] **F0.2 — Gerar o cliente Dart do OpenAPI** (~1,5 HD)
  - · Escolher gerador (`openapi-generator` ou `swagger_dart_code_generator`)
  - · Script `tools/gen_api_client.sh` que baixa `/openapi.json` do daemon e
    regenera — o contrato nunca é escrito à mão
  - · Fixar o cliente gerado no repositório (build reprodutível) e documentar
    quando regenerar
  - · Camada fina por cima (base URL, timeouts, tratamento de erro uniforme)
- [ ] **F0.3 — Estado e navegação** (~1 HD)
  - · Gerência de estado (recomendado: **Riverpod**) e convenções de provider
  - · Roteamento (**go_router**), rotas espelhando as telas atuais
  - · Estado global: workspace ativo, projeto ativo, tema
- [ ] **F0.4 — Design system** (~1,5 HD)
  - · Portar o tema atual: accent índigo `#4F46E5`, raio 12, sombras suaves,
    tipografia Inter, claro **e** escuro
  - · Componentes base: card, botão (primário/ghost), input, badge, empty state,
    `SectionCard` numerado, agrupamento de ações
  - · Responsividade real (o motivo original da migração): breakpoints e layout
    adaptativo desde o começo
- [ ] **F0.5 — Shell da aplicação** (~1 HD)
  - · Sidebar com navegação, seletor de workspace e de projeto
  - · Troca de workspace chamando `POST /workspaces/active` **com confirmação**
    (é estado global do daemon — troca o banco ativo)
  - · Toggle de tema; barra de status (saúde da API)
- [ ] **F0.6 — Smoke ponta a ponta** (~0,5 HD)
  - · Dashboard consumindo a API real; erro visível se o daemon estiver fora
  - · Checagem de saúde no boot (`/api/health`) com mensagem clara

### F1 — Telas CRUD sobre a API existente (~20–26 HD)

Todas consomem endpoints que **já existem**. A web UI React serve de referência
funcional (3.249 LOC para 16 telas mostram que a UI orientada a API é enxuta).

Simples (~0,5–1 HD cada):
- [ ] **F1.1 — Labels** · CRUD, cor, uso por tarefa
- [ ] **F1.2 — Tradutor** · origem/destino, histórico
- [ ] **F1.3 — Testador de API** · requisição, resposta, histórico salvo
- [ ] **F1.4 — Instruções/Guia** · conteúdo estático + navegação
- [ ] **F1.5 — Ferramentas (hub)** · grade de atalhos para as telas extras

Médias (~1–1,5 HD cada):
- [ ] **F1.6 — Dashboard** · resumo, digest (IA), atividade recente, projetos
- [ ] **F1.7 — Projetos** · lista, criação, exclusão, abrir board
- [ ] **F1.8 — TODOs** · agendamento, recorrência, snooze, badge de pendentes
- [ ] **F1.9 — Métricas** · velocity, lead/cycle time (gráficos: `fl_chart`)
- [ ] **F1.10 — Estudos** · planos, tópicos, criação a partir de arquivo
- [ ] **F1.11 — Assistente (chat)** · streaming da resposta, histórico
- [ ] **F1.12 — Biblioteca** · snippets e runbooks
- [ ] **F1.13 — Base de conhecimento + memória** · busca semântica, ingestão
- [ ] **F1.14 — Configurações** · idioma, provedores de IA, Whisper, notificações
- [ ] **F1.15 — Sprints e planejamento** · alocação, retrospectiva

Complexas (~2–3 HD cada):
- [ ] **F1.16 — Board (kanban)** · colunas, **drag & drop** entre colunas,
  filtro por sprint, cards com tipo/prioridade/labels/assignee
  - · Drag & drop com feedback visual e reordenação otimista
  - · Estado de erro/rollback se o `POST /tasks/{code}/move` falhar
- [ ] **F1.17 — Detalhe da tarefa** · descrição, checklist (DoD), comentários
  tipados, dependências, labels, sprint, time tracking
- [ ] **F1.18 — Meu Dia** · notas com preview markdown, template, relatório do
  dia (IA), atividade, sync Obsidian, backup

### F2 — Backend: expor o que falta (Python) (~11–13 HD)

Pré-requisito de F3. **Nada disso é trabalho de Flutter** — é completar o daemon.

- [ ] **F2.1 — API de Reuniões (CRUD)** (~2 HD)
  - · Endpoints sobre o `transcricoes/repository.py` **que já existe**
    (listar, obter, salvar, excluir, arquivar, ordenar)
  - · Schemas Pydantic espelhando o dict do repositório
  - · Testes de API (o repositório já tem 9 testes de unidade)
- [ ] **F2.2 — Desacoplar os workers do Qt** (~3–4 HD) ⚠ **maior risco técnico**
  - · Reescrever `agent_service`, `live_assistant`, `transcriber` de `QThread`
    para `threading`/`asyncio` puro
  - · Motivo medido: spike registrado no
    [Plano 12](eficiencia-recursos.ptbr.md#3-a-fazer-por-esforço) mostrou que
    rodar o loop Qt numa thread dedicada (arranjo que o daemon exigiria)
    **causou segfault** — violação de afinidade de thread do Qt. Tirar o Qt do
    caminho do áudio é a solução limpa, não contorná-lo.
  - · Manter a GUI Qt funcionando durante a transição (adaptador de sinais)
- [ ] **F2.3 — WebSocket ao vivo** (~3 HD)
  - · Canal de transcrição parcial + estado do assistente (plano/ações/decisões/
    perguntas) em tempo real
  - · Protocolo versionado (tipos de mensagem documentados)
  - · Reconexão e recuperação de estado ao reconectar
- [ ] **F2.4 — API do Vault (KeePass)** (~2 HD) ⚠ **decisão de segurança**
  - · Expor cofre por HTTP local exige cuidado: sessão destravada, timeout de
    bloqueio, **nunca** logar segredo, e avaliar se o endpoint deve existir
  - · Alternativa a considerar: manter o Vault só no app Qt/Python e **não**
    portar para Flutter (menor superfície de risco)
- [ ] **F2.5 — API do observador de tela** (~1 HD)
  - · Listar monitores, capturar frame sob demanda, ligar/desligar
- [ ] **F2.6 — Atalhos globais** (~0,5 HD)
  - · Permanecem no daemon (`pynput`); expor comando "alternar gravação" por API
    para o Flutter refletir o estado

### F3 — Reuniões no Flutter (~5–7 HD) — depende de F2

- [ ] **F3.1 — Tela de reunião** (~3 HD)
  - · Fluxo em 4 etapas já consolidado no Qt: 1 Preparar → 2 Gravar →
    3 Assistente ao vivo → 4 Resultado (ver
    [plano de melhorias](melhorias-reunioes.ptbr.md))
  - · Indicador de progresso do fluxo (equivalente ao `FlowIndicator`)
  - · Campo único de transcrição (travado durante a gravação)
- [ ] **F3.2 — Consumo do WebSocket** (~1,5 HD)
  - · Transcrição parcial em tempo real; abas de plano/dicas/ações/decisões/
    perguntas; perguntar à reunião
  - · Respostas manuais nas perguntas preservadas na reanálise
- [ ] **F3.3 — Histórico e reabertura** (~1 HD)
  - · Lista, busca, arquivar/excluir, reordenar
  - · Reabrir mostra os itens salvos (incl. derivação do `summary_json` para
    gravações antigas)
- [ ] **F3.4 — Contexto e anexos** (~1 HD)
  - · Upload de arquivo/imagem para contexto; captura de tela via F2.5

### F4 — Paridade, empacotamento e migração (~4–6 HD)

- [ ] **F4.1 — Checklist de paridade** (~1 HD)
  - · Tela a tela, comparando com a GUI Qt; lista do que ficou de fora
    conscientemente
- [ ] **F4.2 — Empacotamento Linux** (~2 HD)
  - · Build release; empacotar (AppImage/Flatpak) com o daemon Python junto
  - · Script de inicialização: subir o daemon e a UI, checagem de saúde
  - · Autostart (hoje existe para o app Qt)
- [ ] **F4.3 — Convivência durante a transição** (~1 HD)
  - · Qt e Flutter lado a lado, mesmo daemon e mesmo banco
  - · Documentar qual usar para quê enquanto a paridade não fecha
- [ ] **F4.4 — Aposentar o Qt** (~1–2 HD)
  - · Só quando F4.1 fechar; remover views e dependência PySide6
  - · Decidir o destino da **web UI React** (ver seção 7)

### F5 — Mobile (opcional, fora do escopo inicial)

- [ ] **F5.1 — Viabilidade** · o daemon hoje escuta em `127.0.0.1`; usar do
  celular exige expor na rede → **decisão de segurança** (autenticação,
  TLS, pareamento). Não fazer sem esse desenho.
- [ ] **F5.2 — Adaptação de layout** · as telas já nascem responsivas em F0.4

## 5. Roadmap

```
F0 Fundação ──► F1 Telas CRUD ──────────────────────► F4 Paridade ──► aposentar Qt
   (5–7 HD)      (20–26 HD)                              (4–6 HD)
                                                          ▲
F2 Backend (Python) ──► F3 Reuniões no Flutter ──────────┘
   (11–13 HD)             (5–7 HD)
```

- **F0 é bloqueante** para todo o resto.
- **F1 e F2 correm em paralelo** — são bases de código diferentes (Dart × Python)
  e não se bloqueiam.
- **F3 depende de F2** (sem API/WS de reuniões não há o que consumir).
- **F4 fecha** quando F1 e F3 estiverem completas.

**Total estimado: ~45–59 HD.**

Marcos sugeridos:
1. **M1 — "Anda"**: F0 completo; Dashboard e Projetos reais no Flutter.
2. **M2 — "Serve para o dia a dia"**: F1 simples + médias + Board e Task detail.
3. **M3 — "Reuniões funcionam"**: F2 + F3.
4. **M4 — "Substitui o Qt"**: F4 fechado.

## 6. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| **Afinidade de thread do Qt** (F2.2) | Alto — segfault já observado em spike | Remover o Qt do caminho do áudio (threading puro), não contorná-lo |
| **Drag & drop do board** em Flutter | Médio | Prototipar cedo em F1.16; rollback otimista se a API falhar |
| **Divergência de contrato** API↔UI | Médio | Cliente **gerado** do OpenAPI + regeneração versionada (F0.2) |
| **Vault por HTTP** (F2.4) | Alto (segurança) | Avaliar não portar; se portar, sessão com timeout e sem log de segredo |
| **Três front-ends ao mesmo tempo** (Qt + React + Flutter) | Médio (custo de manutenção) | Decidir o destino do React em F4.4; migrar uma tela por vez |
| **Estimativa acima do Plano 11** | Baixo | Ver seção 8 — a diferença é o backend de Reuniões, antes subestimado |

## 7. Pontos de decisão

- **Destino da web UI React**: manter como acesso por navegador/remoto, ou
  aposentar junto com o Qt? Manter três fronts é caro; manter dois (Flutter
  desktop + React remoto) só se o acesso por navegador tiver valor real.
- **Vault no Flutter**: portar (exige API de cofre) ou deixar fora do escopo?
  Recomendação: **deixar fora** no primeiro ciclo — menor superfície de risco.
- **Mobile**: só depois de resolver autenticação/exposição do daemon (F5.1).

## 8. Relação com o Plano 11

O [Plano 11](migracao-toolkit-ui.ptbr.md) estimou a rota Flutter em **~27–50 HD**
e recomendou a rota web. A decisão foi por Flutter; este plano detalha a execução
e chega a **~45–59 HD**. A diferença não é reestimativa da UI — é que o Plano 11
tratava o *sidecar* de áudio como um item só (~3–5 HD), enquanto aqui o backend
de Reuniões (F2) está aberto em 6 tarefas (~11–13 HD), incluindo o
**desacoplamento do Qt** cuja dificuldade real só ficou clara no spike registrado
no [Plano 12](eficiencia-recursos.ptbr.md).

Segue valendo do Plano 11: **a captura de áudio e o Whisper permanecem em Python
em qualquer cenário** — trocar o toolkit de UI não remove essa parte.
