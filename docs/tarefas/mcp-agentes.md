# Tarefas — MCP / Agentes

Pacote separado que expõe a API do Maestro como **servidor MCP**, para agentes
(Claude Code, etc.) operarem os quadros nativamente. Detalhes de design no
[doc 03](../03-api-e-agentes.md#servidor-mcp-envólucro-da-api). Esforço em homem-dia (hd).

---

## M1 — Scaffold do servidor MCP · 1.5 hd
- [ ] Pacote `maestro-mcp` (Node/TypeScript) usando o SDK MCP
- [ ] Config por env: `MAESTRO_API_URL`, `MAESTRO_API_KEY`, `MAESTRO_COMPANY_ID`
- [ ] Cliente HTTP tipado (reusar tipos gerados do Swagger)
- [ ] Mapear erros da API → erros MCP legíveis para o agente

## M2 — Tools de leitura · 1 hd
- [ ] `maestro_list_projects`
- [ ] `maestro_list_tasks` (filtros: status, assignee, label)
- [ ] `maestro_get_task` (por código `GAV-42`)

## M3 — Tools de escrita · 2 hd
- [ ] `maestro_write_doc` (cria/atualiza doc markdown em projeto/tarefa)
- [ ] `maestro_decompose` (bulk: tarefas + subtarefas, com `Idempotency-Key`)
- [ ] `maestro_move_task` (muda status no quadro)
- [ ] `maestro_comment` (comenta numa tarefa)

## M4 — Empacotamento e uso · 1.5 hd
- [ ] Publicar/rodar via `npx` ou binário
- [ ] Exemplo de config no cliente MCP (ex.: `claude` / `mcpServers`)
- [ ] Guia: "como dar uma API key a um agente e ligar o MCP"
- [ ] Princípio do menor privilégio: recomendar chave com escopos mínimos

## M5 — Validação ponta a ponta · 1 hd
- [ ] Rodar o **Maestro Loop** completo via MCP num agente real
      (briefing → doc → decompose → mover status)
- [ ] Conferir que toda ação aparece no `ActivityLog` como "via agente"

---

## Checklist de qualidade (MCP)

- [ ] Tools com descrições claras e schemas de entrada validados
- [ ] Erros da API chegam ao agente de forma acionável (campo faltando, escopo)
- [ ] Idempotência respeitada no `decompose` (sem tarefas duplicadas)
- [ ] Auditoria correta (ações atribuídas à identidade do agente)
- [ ] Guia de configuração testado por alguém que não escreveu o código
