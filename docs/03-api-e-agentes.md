# 03 — API e agentes

A API é REST (NestJS + Swagger, do template). Dois mecanismos de autenticação:

- **Humanos** → JWT + refresh (já existe no template).
- **Agentes** → **API key** no header `x-api-key: mst_live_xxx`.

A API key é vinculada a uma **Membership** (usuário + empresa). O agente herda as
permissões daquele papel, podendo ser **ainda mais restrito** pelos `scopes` da chave.

## Princípios para uma API amigável a agente

1. **Bulk em tudo que importa** — o passo *decompose* cria muitas tarefas de uma vez.
   `POST /tasks/bulk` aceita um array (com subtarefas aninhadas) e cria em uma
   transação. Sem isso, o agente faz N chamadas e a UX desanda.
2. **Idempotência** — header `Idempotency-Key` em criações; se o agente reenviar
   após timeout, não duplica tarefas/docs.
3. **Códigos legíveis** — endpoints aceitam tanto `id` quanto código (`GAV-42`).
4. **Erros descritivos** — mensagens que um agente consegue interpretar e corrigir
   (campo faltando, escopo insuficiente, coluna inexistente).
5. **Respostas enxutas + `?expand=`** — por padrão devolve o essencial; expande sob
   demanda (`?expand=subtasks,documents`) para não estourar contexto do agente.
6. **Auditoria automática** — toda escrita via API key grava `viaApiKeyId` no
   `ActivityLog`.

## Esboço de endpoints

```
# Empresas e membros
GET    /companies                      # empresas do usuário/chave
POST   /companies
GET    /companies/:id/members
POST   /companies/:id/members          # convidar/vincular usuário (papel)
PATCH  /companies/:id/members/:mid     # mudar papel
DELETE /companies/:id/members/:mid

# API keys (gestão pelo dono da conta / manager)
GET    /companies/:id/api-keys
POST   /companies/:id/api-keys         # cria → retorna o segredo UMA vez
DELETE /companies/:id/api-keys/:keyId  # revoga

# Projetos e docs
GET    /projects?companyId=
POST   /projects
GET    /projects/:id
GET    /projects/:id/documents
POST   /projects/:id/documents         # cria doc markdown (ex.: a spec refinada)

# Quadro
GET    /boards/:id                      # colunas + tarefas (kanban completo)
POST   /boards/:id/columns
PATCH  /columns/:id                     # renomear, reordenar, WIP

# Tarefas
GET    /tasks?projectId=&status=&assignee=&label=
POST   /tasks
POST   /tasks/bulk                      # criação em massa (decompose)
GET    /tasks/:idOrCode                 # aceita "GAV-42"
PATCH  /tasks/:idOrCode                 # editar campos
POST   /tasks/:idOrCode/move            # { columnId, rank } → muda status/posição
POST   /tasks/:idOrCode/subtasks
GET    /tasks/:idOrCode/comments
POST   /tasks/:idOrCode/comments
POST   /tasks/:idOrCode/documents       # anexa/gera doc na tarefa

# Fluxo da tarefa (objetivo → subtarefas → aceite) — ver doc 08
GET    /tasks/:idOrCode/flow            # { nodes, edges }; ?format=mermaid → texto
POST   /tasks/:idOrCode/dependencies    # { blockerCode, blockedCode } (valida DAG)
DELETE /tasks/:idOrCode/dependencies/:depId
```

## Escopos de API key (sugestão)

```
companies:read           projects:read   projects:write
tasks:read   tasks:write   tasks:move     tasks:delete
docs:read    docs:write
members:read members:write   apikeys:manage
```

Uma chave de agente "executor" típica teria:
`tasks:read tasks:write tasks:move docs:read docs:write` — cria/atualiza tarefas e
docs, move no quadro, **mas não** gerencia membros nem outras chaves.

## Fluxos de agente (o Maestro Loop via API)

### A. Briefing → spec + tarefas

```
1. POST /projects/:id/documents
   { type:"SPEC", title:"...", body:"<markdown refinado>" }
2. POST /tasks/bulk
   [
     { ref:"T1", title:"Tarefa 1", objective:"...", acceptance:"...",
       estimateMd:1.5,
       subtasks:[
         { ref:"S1", title:"Modelar sessões", estimateMd:0.5 },
         { ref:"S2", title:"Endpoint de login", estimateMd:0.5 },
         { ref:"S3", title:"Endpoint de refresh", estimateMd:0.5,
           dependsOn:["S1","S2"] },           // ← cria as arestas do fluxo
         { ref:"S4", title:"Testes e2e", dependsOn:["S3"] }
       ] },
     ...
   ]
   Header: Idempotency-Key: brief-2026-06-21-projX
```

> `ref` é um apelido local do payload; o `dependsOn` referencia outros `ref` do
> mesmo lote. A API resolve os `ref` para IDs reais e cria as `TaskDependency` na
> mesma transação — o **fluxo nasce pronto** já no decompose (ver [doc 08](08-fluxo-de-tarefas.md)).

### B. Execução → mover no quadro

```
1. GET /tasks?projectId=&status=A fazer&assignee=me
2. POST /tasks/GAV-42/move { columnId:"<Fazendo>" }
3. POST /tasks/GAV-42/comments { body:"PR aberto: <link>" }
4. POST /tasks/GAV-42/move { columnId:"<Revisão>" }
```

## Servidor MCP (envólucro da API)

Um pacote separado expõe a API como **servidor MCP**, para que agentes como o
Claude Code conversem nativamente, sem você escrever chamadas REST na mão.
Ferramentas MCP sugeridas:

| Tool MCP | Faz |
|---|---|
| `maestro_create_project` | cria projeto |
| `maestro_write_doc` | cria/atualiza doc markdown |
| `maestro_decompose` | cria tarefas + subtarefas em massa |
| `maestro_list_tasks` | lista/filtra tarefas |
| `maestro_move_task` | muda status no quadro |
| `maestro_comment` | comenta numa tarefa |

A chave (`MAESTRO_API_KEY`) e a `companyId` vão na config do servidor MCP. Assim o
mesmo agente que hoje gera os `.md` passa a registrar tudo direto no quadro.

## Segurança

- API key: armazenar **só hash**; segredo exibido uma vez; prefixo visível na UI.
- `expiresAt` opcional + revogação imediata (`revokedAt`).
- Rate limit por chave; `lastUsedAt` para detectar chaves ociosas.
- Toda ação via chave entra no `ActivityLog` como "via agente".
