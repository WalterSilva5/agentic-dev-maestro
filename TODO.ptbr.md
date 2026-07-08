> 🇬🇧 [English version](TODO.md)

# Próximos passos — Agentic Dev Maestro

Backlog vivo das próximas tarefas. Itens no topo têm prioridade. Esforço em
homem-dia (hd) é estimativa; staffing/cronograma fica a critério da liderança.

---

## ✅ Concluído

### 1. Melhorar o módulo de TODOs (agendamento + lembretes na interface) — PRINCIPAL ✅

TODOs agora são agendáveis com lembretes periódicos na interface (desktop + web).

- [x] `Todo`: adicionados `due_at`, `priority`, `notes`, `snoozed_until`
  (migração leve aditiva em `_run_light_migrations`).
- [x] API: criar/editar com `dueAt`/`priority`/`notes`; `GET /api/todos/pending`
  (vencidos e não adiados); `POST /api/todos/{id}/snooze`. Agendamento em hora local.
- [x] UI (desktop + web): seletor de data/hora + prioridade por TODO; vencido
  destacado em vermelho.
- [x] Notificações na interface (só in-app): lembrete periódico (a cada 1 min)
  com **contador** e ações **Ver / Adiar 10min / Dispensar**. Desktop via
  `QTimer` + banner inferior; web via toast com polling no shell do app.
- [x] Adiar silencia por 10 min; dispensar esconde até o próximo ciclo.
- [x] Badge de pendentes (⏰N) no menu (desktop: item Dashboard; web: item TODOs).
- [x] Edição inline de prioridade, recorrência e prazo em cada linha
  (incluindo definir/remover agendamento).
- [x] TODOs recorrentes (diária/semanal/mensal): concluir um recorrente
  reagenda para a próxima ocorrência futura em vez de marcar como concluído.

---

## 🟡 Backlog — novos módulos (ajudar o dia a dia do dev)

Ideias que encaixam na arquitetura (reusam provedor de IA, board/API, SQLite por
workspace, DevLog/comentários, MCP).

- [x] **Gerenciador de senhas (compatível com KeePass)** (~4–5 hd) — cofre de
  credenciais/segredos **global** (um único para o app, **não por workspace**;
  fica fora dos bancos de workspace, ex.: um `.kdbx` no diretório de config).
  Lê e grava o formato **`.kdbx`** (KeePass 2.x, via `pykeepass`), destravado por
  **senha-mestra** e/ou key file. Interopera com vaults KeePass existentes;
  busca, organização por grupos e **copiar para a área de transferência com
  auto-limpeza**. Sempre **local e criptografado**; a senha-mestra nunca é
  persistida (cofre trava por inatividade). Cuidado extra de segurança por lidar
  com credenciais.
- [ ] **Cockpit de Git/PR** (~4–6 hd) — branch atual, mudanças não commitadas,
  commits e PRs (`git`/`gh`); liga branch/commit → tarefa (DevLog já tem
  `COMMIT_REF`/`DEPLOY_LOG`); IA sugere mensagem de commit/descrição de PR.
- [ ] **Time tracking + Pomodoro por tarefa** (~2–3 hd) — timer sobre a tarefa →
  registra tempo → alimenta cycle time real das Métricas + timesheet semanal.
- [x] **Biblioteca de snippets & prompts** (~2 hd) — snippets de código e prompts
  de IA reutilizáveis, buscáveis por texto/tags/linguagem. View desktop
  **Biblioteca** + web `/biblioteca`; API `/api/snippets`. Tipo SNIPPET|PROMPT,
  copiar para área de transferência, contador de uso.
- [ ] **Base de conhecimento (2º cérebro)** (~4 hd) — notas/wiki por projeto com
  backlinks e Q&A da IA sobre as notas (RAG no workspace); reusa `Document`.
- [x] **Intake/triagem de bugs** (~2 hd) — captura rápida (colar stacktrace) →
  IA classifica severidade/tipo/título (+ causa provável e passos) → vira tarefa
  BUG. API `/api/bugs/triage`; aba "Triagem de bugs" na Biblioteca (desktop + web).
- [ ] **Retrospectiva de sprint** (~2 hd) — ao concluir a sprint, "o que foi
  bem/mal/ações" com a IA; ações viram tarefas.
- [x] **Testador de API (mini-Postman)** (~3 hd) — monta/executa/salva requisições
  HTTP e guarda histórico de execução. API `/api/http-requests` (+ `/run`,
  `/history`); tela dedicada no desktop e web (`/api-tester`).
- [ ] **Digest proativo (standup automático)** (~3 hd) — "feito/fazendo/
  bloqueios" a partir da atividade do board + commits + Meu Dia; resumo semanal.
- [x] **Importar TODO/FIXME do código** (~1–2 hd) — varre uma pasta por
  `TODO/FIXME/HACK/XXX` e importa os selecionados como tarefas ligadas ao arquivo.
  API `/api/code/scan-todos` + `/api/code/import-todos`; aba "Importar do código"
  na Biblioteca (desktop + web).
- [ ] **Assistente de code review** (~3 hd) — aponta um diff/branch → review da
  IA → posta como comentário `CODE_REVIEW` na tarefa.
- [x] **Runbooks/comandos do projeto** (~2 hd) — cartões de setup/deploy/comandos
  com copiar-em-1-clique. Aba "Runbooks" na Biblioteca (desktop) + web
  `/biblioteca`; API `/api/runbooks` (categoria, contador de uso).

---

## 📝 Convenções
- Documentação em inglês (`*.md`) com versão PT em `*.ptbr.md`.
- Migrações de schema são aditivas e idempotentes (ver `_run_light_migrations`).
- Novos módulos devem, quando fizer sentido, ser expostos também na API/MCP.
