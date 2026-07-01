# Maestro Platform — Skill para Agentes

## Visão Geral
O **Maestro** é uma plataforma de gestão de projetos que usa um board kanban. Agentes de IA podem interagir com ela via ferramentas customizadas do opencode para criar, mover, revisar e documentar tarefas.

Disponível como app desktop (PySide6) e como **web app instalável (PWA)**, ambos servidos pela mesma API local (`http://127.0.0.1:9777`).

## Recursos do board
- **Sprints** (por projeto): nome, meta, status (PLANEJADA/ATIVA/CONCLUIDA), datas e **capacidade** (homem-dia). O board filtra por sprint e cada tarefa tem `sprintId` (nulo = backlog). Endpoints em `/api/projects/{id}/sprints` e `/api/sprints/{id}` — ver a skill **api-agent**.
- **Arquivamento**: cards concluídos podem ser arquivados (somem do board, vão para um board à parte) e cards concluídos **há mais de 3 dias são arquivados automaticamente**. Endpoints `/api/tasks/{code}/archive` · `/unarchive` · `/api/projects/{id}/archived`.
- **Assistentes de IA** (na GUI): assistente de **reunião ao vivo** (Transcrições) e assistente de **estudo sob demanda** (Estudos), além do chat interno — todos usam o provedor de IA configurado.

## Ferramentas Disponíveis
Todas as ferramentas estão no namespace `maestro_*`:

### Consulta
- `maestro_listProjects` — lista projetos
- `maestro_board` — consulta o board (colunas + tarefas)
- `maestro_getTask` — detalhes de uma tarefa
- `maestro_listTasks` — lista tarefas com filtros
- `maestro_getFlow` — fluxo da tarefa em mermaid

### Escrita
- `maestro_createTask` — cria tarefa
- `maestro_updateTask` — edita tarefa
- `maestro_moveTask` — move entre colunas
- `maestro_deleteTask` — exclui tarefa
- `maestro_addSubtask` — adiciona subtarefa (só título)
- `maestro_addComment` — posta comentário (code review, commits)
- `maestro_createDocument` — cria documento (spec, ADR, plano)

## Fluxo de Trabalho Esperado

### Ao receber uma solicitação do usuário:
1. **Antes de codificar**: crie uma tarefa no board (Backlog ou A fazer) com `maestro_createTask`
2. **Enquanto trabalha**: mova a tarefa para "Fazendo" com `maestro_moveTask`
3. **Code Review**: ao terminar, poste um comentário com `maestro_addComment` contendo:
   - Resumo do que foi implementado
   - Decisões técnicas importantes
   - Mensagem de commit sugerida
4. **Finalização**: mova a tarefa para "Revisão" ou "Concluído"

### Subtarefas:
- Subtarefas têm **apenas título** (sem descrição, sem comentários)
- Toda a documentação e discussão fica na tarefa principal
- Use `maestro_addSubtask` para decompor tarefas grandes

### Documentação:
- Use `maestro_createDocument` para criar specs (SPEC), plans (PLAN), ADRs ou notas
- Associe documentos a tarefas ou projetos conforme o contexto

## API Key
As ferramentas usam a variável de ambiente `MAESTRO_API_KEY` e `MAESTRO_API_URL`.
