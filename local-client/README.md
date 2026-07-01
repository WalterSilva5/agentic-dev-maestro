# Maestro Local

Cliente desktop do Agentic Dev Maestro. Organiza tarefas, diário de trabalho e estudos, com API REST embutida para integração com agentes de IA.

## Instalação e execução

### Rápido (recomendado)

```bash
./install.sh    # cria venv, instala deps, valida
./run.sh        # executa
```

### Manual

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m maestro_local
```

### Opções

```bash
./run.sh --port 8888    # porta customizada (padrão: 9777)
```

### Entry point global

Após `pip install -e .`, o comando `maestro` fica disponível no PATH do venv:

```bash
maestro              # porta padrão
maestro --port 8888  # porta customizada
```

## O que a aplicação faz

Ao iniciar, o Maestro abre:
1. **GUI desktop** (PySide6/Qt 6) — interface gráfica com 10 telas no menu (+ Métricas, TODOs e Labels como abas do Dashboard)
2. **API REST** (FastAPI/uvicorn) — `http://127.0.0.1:9777/api` em thread daemon

A tela inicial é **Meu Dia**, que funciona como home da aplicação.

## Telas

### Meu Dia (Alt+2) — home

Tela principal do dia de trabalho:

- **Obsidian Vault**: selecionar vault por projeto/workspace, sincronizar notas e tarefas com o Obsidian. Sync automático a cada 5 minutos
- **Notas do dia**: editor markdown com template pre-configurado, preview renderizado, botão para inserir template padrão (Foco do Dia, Tarefas, Blockers, Notas Técnicas)
- **Gerar Relatório**: gera relatório automático com lista de tarefas trabalhadas, atividades do dia e resumo
- **Date picker**: calendário popup para navegar entre dias (substituiu o combo de datas)
- **Dica IA**: ao lado do relatório gerado, botão com prompt sugerido para pedir a um agente de IA que resuma o dia usando a skill `maestro-daily-report`
- **Atividade do dia**: timeline com todas as ações do dia (tasks criadas, movidas, comentadas)
- **Backup do Banco**: exportar cópia do banco SQLite

### TODOs (aba do Dashboard)

Lista rápida de pendências, separada do board:

- **Lista simples**: sem colunas, sem projeto, sem fluxo de status
- **Adicionar/concluir/remover**: campo de texto com Enter, checkbox por item (riscado quando concluído), botão de remover
- **Organização**: pendentes no topo, concluídos embaixo, com contador
- **Limpar concluídos**: botão para remover de uma vez todos os itens marcados
- **API**: gerenciável via `/api/todos`, então agentes também conseguem criar e fechar TODOs

### Dashboard (Alt+1)

Hub central do workspace, organizado em **abas**:

- **Visão geral**: Pomodoro em destaque, cards de resumo (tarefas ativas, concluídas, vencidas, em progresso), tarefas vencidas clicáveis, atividade recente e progresso por projeto
- **Métricas**, **TODOs** e **Labels** (antes eram páginas próprias)

### Estudos (Alt+3)

Módulo de aprendizado:

- **Planos de estudo**: criar planos com nome, categoria (Linguagem, Framework, Certificação, Conceito, Curso, Livro) e status (Não Iniciado, Em Progresso, Concluído, Pausado)
- **Tópicos**: adicionar tópicos com peso e estimativa de horas. Marcar como concluído
- **Roadmap visual**: barra de progresso calculada pelo peso dos tópicos concluídos
- **Sessões de estudo**: registrar tempo de estudo com notas e nível de confiança (1-5)
- **Estatísticas**: horas totais, sessões por semana, planos ativos

### Board Kanban (Alt+4)

Board de tarefas por projeto:

- **Colunas**: customizáveis por projeto (ex: Backlog, A Fazer, Fazendo, Revisão, Concluído)
- **Drag-and-drop**: arrastar cards entre colunas
- **Quick-move**: botão para avançar tarefa para próxima coluna sem arrastar
- **Filtros**: por tipo (Feature, Bug, Tech Debt, Improvement, Chore), prioridade (Low, Medium, High, Urgent), responsável e label
- **WIP limits**: limite de tarefas por coluna
- **Cards**: mostram tipo, prioridade, labels, due date, assignee, indicador de bloqueio e checklist progress
- **Task detail**: dialog completo com título, descrição, tipo, prioridade, assignee, due date, labels, checklist (Definition of Done), dependências, comentários com markdown
- **Tarefas de revisão**: agentes sempre criam tarefas com `requiresHuman: true` para o desenvolvedor validar alterações

### Assistente (Alt+5)

Assistente de IA interno que roda com seu próprio provedor:

- **Provedores compatíveis com OpenAI**: LM Studio local, opencode ou qualquer API no formato `/v1/chat/completions`
- **Ferramentas internas** (LangGraph): lê o board, lista tarefas, solicita revisão (cria tarefa requer-dev), comenta tarefas, cria TODOs e resume a atividade recente
- **Execução assíncrona**: roda em thread separada, sem travar a interface
- **Configuração**: provedor ativo definido em Configurações → Provedores de IA (Base URL, API Key e Modelo)

### Transcrições (Alt+6)

Gravação, transcrição e resumo de reuniões e estudos (migrado do projeto wsi-cronista):

- **Captura de áudio (Linux)**: microfone e/ou áudio do sistema via PipeWire/PulseAudio (`parec`); fontes `.monitor` para loopback
- **Transcrição local**: faster-whisper, modelo configurável (tiny → large-v3), roda offline em QThread
- **Assistente de reunião**: extrai título, pontos-chave, decisões, ações (com responsável) e perguntas em aberto
- **Assistente de estudo**: gera resumo, conceitos-chave, exercícios práticos, tópicos relacionados e recursos
- **IA reusada**: a análise usa o provedor configurado em Provedores de IA (LM Studio/opencode)
- **Histórico**: gravações salvas no banco do workspace, com busca por texto
- **Integração**: botão "Salvar no Meu Dia" anexa o resumo ao relatório do dia
- **Atalho global**: `Ctrl+Shift+R` inicia/para a gravação (best-effort; pode não funcionar em Wayland)
- **Acesso rápido**: widget na sidebar inicia a gravação em 1 clique e mostra o tempo decorrido

### Projetos (Alt+7)

- Criar projetos com nome, chave única (ex: DEMO, PROJ) e descrição
- Cada projeto gera automaticamente colunas padrão no board
- Visão de lista com link para o board

### Labels (aba do Dashboard)

- Criar labels com nome e cor (paleta de 12 cores)
- Aplicar labels em tarefas para categorizar e filtrar
- Labels compartilhadas entre projetos do mesmo workspace

### Métricas (aba do Dashboard)

Dashboard analítico:

- **Cards**: total de tarefas, concluídas (7 e 30 dias), lead time médio, cycle time
- **Throughput semanal**: gráfico de barras das últimas 8 semanas
- **Por tipo**: breakdown Feature/Bug/Tech Debt/Improvement/Chore com percentual
- **Por prioridade**: breakdown Low/Medium/High/Urgent com percentual
- **Por projeto**: progresso de cada projeto com barra

### Skills (Alt+8)

Biblioteca de skills para agentes de IA:

- **12 skills** com prefixo `maestro-` organizadas por categoria (Setup, Agente, Fluxo de Trabalho, Planejamento, Qualidade, Registro)
- **Instalar**: um clique instala o arquivo SKILL.md em `.claude/skills/` do projeto alvo
- **Instalar todas**: botão para instalar todas as skills de uma vez
- **Preview**: ver o conteúdo da skill antes de instalar
- **Diretório destino**: selecionar o projeto onde instalar as skills

### Instruções (Alt+9)

Guia de uso reestruturado com 12 seções, incluindo explicações de cada tela, fluxo de trabalho, o papel dos agentes e tarefas de revisão.

### Configurações (Alt+0)

Tela de configurações gerais:

- **Provedores de IA**: cadastrar e selecionar provedores compatíveis com OpenAI (LM Studio, Ollama, OpenAI, OpenRouter, Groq, DeepSeek, Mistral, Gemini, Together, opencode) usados pelo Assistente e pelas Transcrições. Campos de Base URL, API Key e Modelo, com botão de testar conexão e adicionar novos provedores
- **Transcrições**: modelo do Whisper (tiny → large-v3) e idioma usados na transcrição local
- **Pomodoro**: duração da sessão configurável (1-120 minutos), atualiza o timer da sidebar em tempo real
- **Notificações push**: notificações periódicas na área de trabalho com mensagem personalizada, intervalo configurável (1-480 min) e toggle de ativação. Desabilitado por padrão. Usa `QSystemTrayIcon` com fallback para `notify-send`

## Recursos gerais

| Recurso | Descrição |
|---|---|
| **Tema dark/light** | Toggle na sidebar, aplica em todas as telas |
| **Pomodoro** | Timer configurável no Dashboard com play/pause e reset |
| **Notificações push** | Lembretes periódicos na área de trabalho com mensagem e intervalo customizáveis |
| **Busca global** | `Ctrl+K` abre busca por título ou código de tarefa |
| **Workspaces** | Isolamento completo com banco separado, emoji, cor e descrição customizáveis |
| **Obsidian sync** | Auto-sync a cada 5 min, vault configurável por workspace/projeto |
| **Backup** | Exportar banco SQLite a qualquer momento |
| **Atalhos** | `Alt+1` a `Alt+9` + `Alt+0` para as 10 telas do menu, `Ctrl+K` busca, `Ctrl+Shift+R` gravação |

## Web UI (frontend web)

Além da GUI desktop, há um frontend **web** (React + Vite) servido pela própria API — sobe junto com ela. Com o app rodando, acesse **`http://127.0.0.1:9777/`** no navegador.

- **Código**: `webui/` (React + Vite + axios + react-router), consome a mesma API REST
- **Build**: o `install.sh` builda automaticamente (se houver `npm`); a FastAPI serve `webui/dist/` na raiz `/`, mantendo `/api/*`
- **Desenvolvimento** (hot-reload): `cd webui && npm run dev` (porta 3000, com proxy `/api → 9777`)
- **Telas**: Dashboard, Meu Dia, Estudos, Projetos, Board + detalhe de tarefa (descrição, checklist, comentários, tipo/prioridade, mover), Assistente (chat), Métricas, TODOs, Labels e Configurações (idioma, provedores de IA, Whisper). Seletor de workspace na sidebar e tema claro/escuro. **Transcrições** e **Skills** seguem exclusivas da GUI desktop (captura de áudio e instalação em diretório local)
- **Rodar só a web** (sem a GUI desktop): `./run-web.sh` (ou `python -m maestro_local.webmain`) — sobe API + web em `http://127.0.0.1:9777/`

```bash
cd webui
npm install
npm run build      # gera webui/dist servido pela API
# ou, em dev:
npm run dev        # http://localhost:3000 (proxy para a API em 9777)
```

## API REST

A API roda em `http://127.0.0.1:9777/api` sem autenticação. Todos os endpoints retornam JSON.

### Endpoints

| Recurso | Método | Endpoint | Descrição |
|---|---|---|---|
| Health | GET | `/api/health` | Status da API |
| Projetos | POST | `/api/projects` | Criar projeto |
| Projetos | GET | `/api/projects` | Listar projetos |
| Projetos | GET | `/api/projects/metrics` | Métricas por projeto |
| Projetos | GET | `/api/projects/{id}/board` | Board completo do projeto |
| Tarefas | POST | `/api/tasks` | Criar tarefa |
| Tarefas | GET | `/api/tasks` | Listar tarefas (filtros: project_id, column_id, type, priority) |
| Tarefas | GET | `/api/tasks/{code}` | Detalhe da tarefa por código (ex: DEMO-1) |
| Tarefas | PATCH | `/api/tasks/{code}` | Atualizar tarefa |
| Tarefas | DELETE | `/api/tasks/{code}` | Soft-delete da tarefa |
| Tarefas | POST | `/api/tasks/{code}/move` | Mover para coluna (body: {column_id}) |
| Checklist | POST | `/api/tasks/{code}/checklist` | Adicionar item de checklist |
| Checklist | PATCH | `/api/tasks/checklist/{id}/toggle` | Toggle checked |
| Checklist | DELETE | `/api/tasks/checklist/{id}` | Remover item |
| Dependências | POST | `/api/tasks/{code}/dependencies` | Adicionar dependência |
| Dependências | DELETE | `/api/tasks/{code}/dependencies/{id}` | Remover dependência |
| Context | GET | `/api/tasks/{code}/context` | Contexto completo da tarefa |
| Context | GET | `/api/tasks/{code}/flow` | Fluxo de trabalho da tarefa |
| Histórico | GET | `/api/tasks/{code}/history` | Timeline estruturada de desenvolvimento (transições, comentários, code reviews, checklist) |
| Changelog | GET | `/api/projects/{project_id}/changelog?days=7` | Changelog agregado do projeto (tarefas concluídas, em andamento, atividade por dia) |
| Labels | POST | `/api/labels` | Criar label |
| Labels | GET | `/api/labels` | Listar labels |
| Labels | DELETE | `/api/labels/{id}` | Remover label |
| Labels | POST | `/api/labels/{id}/tasks/{task_id}` | Aplicar label em tarefa |
| Labels | DELETE | `/api/labels/{id}/tasks/{task_id}` | Remover label de tarefa |
| Comentários | POST | `/api/comments` | Criar comentário |
| Comentários | GET | `/api/comments` | Listar comentários (filtro: task_id) |
| Comentários | PATCH | `/api/comments/{id}` | Editar comentário |
| Comentários | DELETE | `/api/comments/{id}` | Remover comentário |
| Documentos | POST | `/api/documents` | Criar documento |
| Documentos | GET | `/api/documents` | Listar documentos |
| Documentos | PUT | `/api/documents/{id}` | Atualizar documento |
| Documentos | DELETE | `/api/documents/{id}` | Remover documento |
| Atividade | GET | `/api/activity` | Log de atividades |
| Diario | GET | `/api/daily/{date}` | Nota do dia (YYYY-MM-DD) |
| Diario | POST | `/api/daily/{date}` | Criar/atualizar nota do dia |
| Diario | PATCH | `/api/daily/{date}/report` | Append ao relatório do dia |
| TODOs | GET | `/api/todos` | Listar TODOs (filtro: done) |
| TODOs | POST | `/api/todos` | Criar TODO |
| TODOs | PATCH | `/api/todos/{id}` | Atualizar texto ou marcar como concluído |
| TODOs | DELETE | `/api/todos/{id}` | Remover TODO |
| Estudos | POST | `/api/study/plans` | Criar plano de estudo |
| Estudos | GET | `/api/study/plans` | Listar planos |
| Estudos | GET | `/api/study/plans/{id}` | Detalhe do plano |
| Estudos | PATCH | `/api/study/plans/{id}` | Atualizar plano |
| Estudos | DELETE | `/api/study/plans/{id}` | Remover plano |
| Tópicos | POST | `/api/study/plans/{id}/topics` | Adicionar tópico |
| Tópicos | GET | `/api/study/plans/{id}/topics` | Listar tópicos |
| Tópicos | PATCH | `/api/study/topics/{id}` | Atualizar tópico |
| Tópicos | DELETE | `/api/study/topics/{id}` | Remover tópico |
| Sessões | POST | `/api/study/sessions` | Registrar sessão de estudo |
| Sessões | GET | `/api/study/sessions` | Listar sessões (filtro: date) |
| Stats | GET | `/api/study/stats` | Estatísticas de estudo |

### Exemplo: criar tarefa via curl

```bash
# Criar projeto
curl -X POST http://127.0.0.1:9777/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Meu Projeto", "key": "MP"}'

# Criar tarefa
curl -X POST http://127.0.0.1:9777/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Implementar login", "project_id": 1, "type": "FEATURE", "priority": "HIGH"}'

# Mover tarefa
curl -X POST http://127.0.0.1:9777/api/tasks/MP-1/move \
  -H "Content-Type: application/json" \
  -d '{"column_id": 2}'
```

## Skills para agentes de IA

| Skill | Categoria | O que faz |
|---|---|---|
| `maestro-run` | Setup | Iniciar a aplicação (GUI + API) |
| `maestro-api-agent` | Agente | Ensina o agente a interagir com a API REST |
| `maestro-task-workflow` | Fluxo | Fluxo completo: pegar task, implementar, mover, documentar |
| `maestro-project-setup` | Setup | Criar projeto com colunas e labels padrão |
| `maestro-sprint-planning` | Planejamento | Planejar sprint com estimativas e priorização |
| `maestro-code-review-log` | Qualidade | Registrar code reviews como comentários |
| `maestro-bug-triage` | Qualidade | Triagem de bugs com prioridade e reprodução |
| `maestro-daily-standup` | Registro | Gerar relatório de standup automático |
| `maestro-tech-debt-tracker` | Qualidade | Registrar e priorizar dívida técnica |
| `maestro-documentation-writer` | Registro | Gerar documentação a partir do código |
| `maestro-daily-report` | Registro | Relatório diário com notas, atividade e resumo em bullet list (suporta modo parcial) |
| `maestro-context-loader` | Agente | Carregar contexto completo do workspace para retomar trabalho de onde parou |

## Tipos de tarefa

| Tipo | Uso |
|---|---|
| `FEATURE` | Nova funcionalidade |
| `BUG` | Correção de bug |
| `TECH_DEBT` | Dívida técnica |
| `IMPROVEMENT` | Melhoria em funcionalidade existente |
| `CHORE` | Tarefa operacional |

## Prioridades

| Prioridade | Nível |
|---|---|
| `LOW` | Baixa |
| `MEDIUM` | Média |
| `HIGH` | Alta |
| `URGENT` | Urgente |

## Banco de dados

SQLite local com isolamento por workspace:

```
~/.maestro-local/
├── config.json                     # Workspaces, vaults, tema
└── workspaces/
    ├── default/maestro.db          # Workspace padrão
    └── {workspace-id}/maestro.db   # Workspaces adicionais
```

O banco é criado automaticamente na primeira execução. Cada workspace tem seu próprio arquivo, garantindo isolamento total dos dados.

## Estrutura do código

```
maestro_local/
├── __main__.py              # Entry point: init_db -> start_api -> QApplication
├── config.py                # Config JSON + workspace management
├── db/
│   └── models.py            # SQLAlchemy models + switch_db()
├── api/
│   ├── app.py               # FastAPI endpoints (todos os recursos)
│   └── server.py            # Uvicorn runner em thread daemon
├── gui/
│   ├── theme.py             # ThemeColors dataclass + dark/light + stylesheet
│   ├── main_window.py       # MainWindow + sidebar + pomodoro + workspace selector
│   ├── workspace_selector.py # Seletor de workspace com emoji/cor/descrição
│   └── views/
│       ├── daily_view.py        # Meu Dia + Obsidian sync + relatório
│       ├── todos_view.py        # Lista simples de TODOs
│       ├── chat_view.py         # Assistente (agente interno)
│       ├── transcricoes_view.py # Transcrições (gravação + transcrição)
│       ├── settings_view.py     # Configurações (IA, pomodoro, notificações)
│       ├── dashboard_view.py    # Dashboard com resumo e atividade
│       ├── study_view.py        # Planos de estudo + tópicos + sessões
│       ├── board_view.py        # Kanban board + TaskCard + filtros
│       ├── task_detail_dialog.py # Dialog completo de tarefa
│       ├── projects_view.py     # Lista/criação de projetos
│       ├── labels_view.py       # CRUD de labels com paleta
│       ├── metrics_view.py      # Dashboard de métricas
│       ├── skills_view.py       # Skills para agentes de IA
│       └── guide_view.py        # Instruções de uso
├── ai/
│   ├── providers.py         # Provedores OpenAI-compatíveis + teste de conexão
│   ├── tools.py             # Ferramentas internas do agente (board, revisão, TODOs)
│   └── agent.py             # Agente estratégico (LangGraph ReAct)
├── transcricoes/
│   ├── audio.py             # Captura de áudio Linux (parec/PipeWire)
│   ├── transcriber.py       # faster-whisper em QThread
│   ├── summarizer.py        # Sumarização via provedor do Maestro
│   ├── assistants.py        # Assistentes de reunião e estudo
│   ├── markdown_gen.py      # Geração de markdown dos resumos
│   └── hotkeys.py           # Atalhos globais (pynput)
└── skills/
    └── catalog.py           # Catálogo de 12 skills com conteúdo SKILL.md
```

## Requisitos

- Python 3.10+
- Qt 6 (instalado automaticamente com PySide6)
- `langgraph` + `langchain-openai` (instalados automaticamente; usados pelo Assistente)
- Para o Chat e a análise das Transcrições: um provedor de IA compatível com OpenAI (LM Studio local, opencode, etc.)
- Para as Transcrições (gravação no Linux): `pulseaudio-utils` (`parec`/`pactl`) e PipeWire/PulseAudio; `faster-whisper` para transcrição (instalado automaticamente)
- Linux, macOS ou Windows
