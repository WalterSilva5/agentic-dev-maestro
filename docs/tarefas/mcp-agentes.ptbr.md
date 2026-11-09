> 🇬🇧 [English version](mcp-agentes.md)

# Tarefas — MCP / Agentes

Pacote separado que expõe a API do Relay como **servidor MCP**, para agentes
(Claude Code, etc.) operarem os quadros nativamente. Detalhes de design no
[doc 03](../03-api-e-agentes.md#servidor-mcp-envólucro-da-api). Esforço em homem-dia (hd).

---

## M1 — Scaffold do servidor MCP · 1.5 hd
- [ ] Pacote `relay-mcp` (Node/TypeScript) usando o SDK MCP
- [ ] Config por env: `RELAY_API_URL`, `RELAY_API_KEY`, `RELAY_COMPANY_ID`
- [ ] Cliente HTTP tipado (reusar tipos gerados do Swagger)
- [ ] Mapear erros da API → erros MCP legíveis para o agente

## M2 — Tools de leitura · 1 hd
- [ ] `relay_list_projects`
- [ ] `relay_list_tasks` (filtros: status, assignee, label)
- [ ] `relay_get_task` (por código `GAV-42`)

## M3 — Tools de escrita · 2 hd
- [ ] `relay_write_doc` (cria/atualiza doc markdown em projeto/tarefa)
- [ ] `relay_decompose` (bulk: tarefas + subtarefas, com `Idempotency-Key`)
- [ ] `relay_move_task` (muda status no quadro)
- [ ] `relay_comment` (comenta numa tarefa)

## M4 — Empacotamento e uso · 1.5 hd
- [ ] Publicar/rodar via `npx` ou binário
- [ ] Exemplo de config no cliente MCP (ex.: `claude` / `mcpServers`)
- [ ] Guia: "como dar uma API key a um agente e ligar o MCP"
- [ ] Princípio do menor privilégio: recomendar chave com escopos mínimos

## M5 — Validação ponta a ponta · 1 hd
- [ ] Rodar o **Relay Loop** completo via MCP num agente real
      (briefing → doc → decompose → mover status)
- [ ] Conferir que toda ação aparece no `ActivityLog` como "via agente"

---

## Checklist de qualidade (MCP)

- [ ] Tools com descrições claras e schemas de entrada validados
- [ ] Erros da API chegam ao agente de forma acionável (campo faltando, escopo)
- [ ] Idempotência respeitada no `decompose` (sem tarefas duplicadas)
- [ ] Auditoria correta (ações atribuídas à identidade do agente)
- [ ] Guia de configuração testado por alguém que não escreveu o código
