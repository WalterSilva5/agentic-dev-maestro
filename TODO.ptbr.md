> 🇬🇧 [English version](TODO.md)

# Próximos passos — Agentic Dev Maestro

Backlog vivo das próximas tarefas. Itens no topo têm prioridade. Esforço em
homem-dia (hd) é estimativa; staffing/cronograma fica a critério da liderança.

---

## 🔴 Prioridade

### 1. Melhorar o módulo de TODOs (agendamento + lembretes na interface) — PRINCIPAL

Hoje o TODO é mínimo (texto + concluído). Torná-lo mais explícito e adicionar
**agendamento** com **notificações periódicas dentro da aplicação**.

**Modelo de dados**
- [ ] Adicionar ao `Todo`: `due_at` (data/hora agendada), e opcionalmente
  `priority`, `notes`, `remind` (liga/desliga o lembrete). Migração leve
  (`ALTER TABLE todos ADD COLUMN ...`), no padrão já usado em `init_db`.

**API**
- [ ] Criar/editar TODO com `dueAt` (e demais campos).
- [ ] Endpoint para listar TODOs **pendentes/vencidos** (`due_at <= agora` e
  `done = false`), usado pelo mecanismo de notificação.

**UI (desktop + web)**
- [ ] Seletor de data/hora por TODO; exibir o horário agendado.
- [ ] Estados visuais: agendado, **vencido/pendente**, concluído.
- [ ] Ordenar/filtrar por horário e por pendência.

**Notificações na interface (somente in-app — sem notificações do SO)**
- [ ] Quando o horário de um TODO é atingido, a aplicação passa a exibir um
  **lembrete periódico** (ex.: um toast/banner a cada N minutos) indicando que
  há tarefas pendentes, com **contador** dos vencidos.
- [ ] Ações no lembrete: **concluir**, **adiar (snooze)** por X min, e
  **dispensar** até o próximo ciclo.
- [ ] Desktop: `QTimer` verificando os pendentes periodicamente + um widget de
  toast/banner (reaproveitar o padrão de notificação já existente na janela).
- [ ] Web: intervalo de polling no endpoint de pendentes + toast na UI.
- [ ] Badge/contador de pendentes visível na navegação (ex.: no item TODOs).

**Critérios de aceite**
- Um TODO agendado para um horário passa a **lembrar periodicamente** na
  interface depois desse horário, até ser concluído ou adiado.
- O contador de pendentes/vencidos fica visível.
- Nada dispara notificação do sistema operacional — tudo é dentro do app.

---

## 🟡 Backlog — novos módulos (ajudar o dia a dia do dev)

Ideias que encaixam na arquitetura (reusam provedor de IA, board/API, SQLite por
workspace, DevLog/comentários, MCP).

- [ ] **Cockpit de Git/PR** (~4–6 hd) — branch atual, mudanças não commitadas,
  commits e PRs (`git`/`gh`); liga branch/commit → tarefa (DevLog já tem
  `COMMIT_REF`/`DEPLOY_LOG`); IA sugere mensagem de commit/descrição de PR.
- [ ] **Time tracking + Pomodoro por tarefa** (~2–3 hd) — timer sobre a tarefa →
  registra tempo → alimenta cycle time real das Métricas + timesheet semanal.
- [ ] **Biblioteca de snippets & prompts** (~2 hd) — snippets de código e prompts
  de IA reutilizáveis (com variáveis), buscáveis por label (SQLite + FTS).
- [ ] **Base de conhecimento (2º cérebro)** (~4 hd) — notas/wiki por projeto com
  backlinks e Q&A da IA sobre as notas (RAG no workspace); reusa `Document`.
- [ ] **Intake/triagem de bugs** (~2 hd) — captura rápida (colar stacktrace) →
  IA classifica severidade/tipo → vira tarefa (skill `bug-triage`).
- [ ] **Retrospectiva de sprint** (~2 hd) — ao concluir a sprint, "o que foi
  bem/mal/ações" com a IA; ações viram tarefas.
- [ ] **Testador de API (mini-Postman)** (~3 hd) — salva requests por projeto,
  executa e guarda histórico.
- [ ] **Digest proativo (standup automático)** (~3 hd) — "feito/fazendo/
  bloqueios" a partir da atividade do board + commits + Meu Dia; resumo semanal.
- [ ] **Importar TODO/FIXME do código** (~1–2 hd) — varre o repo por comentários
  `TODO/FIXME` e importa como tarefas ligadas ao arquivo.
- [ ] **Assistente de code review** (~3 hd) — aponta um diff/branch → review da
  IA → posta como comentário `CODE_REVIEW` na tarefa.
- [ ] **Runbooks/comandos do projeto** (~2 hd) — cartões de setup/deploy/comandos
  com copiar-em-1-clique; IA gera do README.

---

## 📝 Convenções
- Documentação em inglês (`*.md`) com versão PT em `*.ptbr.md`.
- Migrações de schema são aditivas e idempotentes (ver `_run_light_migrations`).
- Novos módulos devem, quando fizer sentido, ser expostos também na API/MCP.
