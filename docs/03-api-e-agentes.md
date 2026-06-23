# 03 — API e agentes

> Estado: **implementado**. Este documento reflete a API real (NestJS + Swagger).
> Swagger UI: `http://<host>:<porta>/api/docs`. Todas as rotas ficam sob o prefixo
> global **`/api`**.

A API é REST. Dois mecanismos de autenticação:

- **Humanos** → JWT (`Authorization: Bearer <accessToken>`) **+ header `X-Company-Id`**
  para escolher a empresa ativa (multi-tenant).
- **Agentes** → **API key** no header **`x-api-key: adm_…`**. O tenant é resolvido
  automaticamente a partir da *Membership* da chave — o agente **não** envia
  `X-Company-Id`.

A API key é vinculada a uma **Membership** (usuário + empresa). O agente herda as
permissões daquele papel. A chave também guarda uma lista de `scopes` (ver abaixo).

## Princípios para uma API amigável a agente

1. **Bulk em tudo que importa** — o passo *decompose* cria muitas tarefas de uma vez.
   `POST /api/tasks/bulk` aceita `{ projectId, items[] }` (com subtarefas aninhadas e
   dependências) e cria tudo em uma transação.
2. **Idempotência** — header `Idempotency-Key` em criações em massa; se o agente
   reenviar após timeout, não duplica tarefas. *(Sem a chave, reenvios criam lotes
   duplicados — sempre envie uma.)*
3. **Códigos legíveis** — endpoints de tarefa aceitam tanto `id` numérico quanto o
   código (`MAESTRO-4`).
4. **Erros descritivos** — mensagens em `messages[]` que um agente consegue
   interpretar (campo faltando, projeto inexistente, ciclo de dependência, etc.).
5. **Fluxo embutido** — o `dependsOn` do decompose já cria as arestas do grafo da
   tarefa; `GET /api/tasks/:code/flow` devolve nós/arestas + progresso.
6. **Auditoria automática** — toda escrita via API key é gravada no `ActivityLog`.

## Autenticação

### Humano (JWT + tenant)

```bash
TOKEN=$(curl -s -X POST http://localhost:5099/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@template.com","password":"Admin@123"}' | jq -r .accessToken)

curl http://localhost:5099/api/projects \
  -H "Authorization: Bearer $TOKEN" -H "X-Company-Id: 2"
```

### Criar uma API key (gerência → faz pelo dono/manager, autenticado por JWT)

```bash
curl -X POST http://localhost:5099/api/companies/2/api-keys \
  -H "Authorization: Bearer $TOKEN" -H "X-Company-Id: 2" \
  -H 'Content-Type: application/json' \
  -d '{"label":"agente claude-code","scopes":["tasks:write","tasks:move","docs:write"]}'
# → retorna o segredo (adm_…) UMA vez. Guarde; só o hash fica no banco.
```

### Agente (API key)

```bash
KEY="adm_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
curl http://localhost:5099/api/projects -H "x-api-key: $KEY"   # sem X-Company-Id
```

## Endpoints implementados

```
# Auth (humanos)
POST   /api/auth/login | /refresh | /logout
POST   /api/auth/forgot-password | /reset-password | /change-password

# Empresas e membros
GET    /api/companies                         # empresas do usuário/chave
POST   /api/companies
GET    /api/companies/:companyId/members
POST   /api/companies/:companyId/members       # convidar/vincular (envia e-mail)
PATCH  /api/companies/:companyId/members/:membershipId   # mudar papel
DELETE /api/companies/:companyId/members/:membershipId

# API keys (OWNER/MANAGER)
GET    /api/companies/:companyId/api-keys
POST   /api/companies/:companyId/api-keys      # cria → segredo (adm_…) UMA vez
DELETE /api/companies/:companyId/api-keys/:id  # revoga

# Projetos e quadro
GET    /api/projects                           # projetos da empresa ativa
POST   /api/projects                           # cria projeto (+ board "Principal" com 5 colunas)
GET    /api/projects/:id/board                 # board completo: colunas + tarefas

# Tarefas
GET    /api/tasks?projectId=&columnId=&assigneeId=&parentId=
POST   /api/tasks                              # { projectId, title, objective?, acceptance?, columnId?, priority?, estimateMd?, parentId? }
POST   /api/tasks/bulk                         # decompose: { projectId, items[] }  (Idempotency-Key)
GET    /api/tasks/:idOrCode                    # aceita "MAESTRO-4"
GET    /api/tasks/:idOrCode/flow               # { task, progress, nodes, edges }; ?format=mermaid → { mermaid }
POST   /api/tasks/:idOrCode/move               # { columnId } → muda status/coluna
POST   /api/tasks/:idOrCode/dependencies       # { blockerCode } (valida DAG; rejeita ciclo)
DELETE /api/tasks/:idOrCode/dependencies/:depId

# Documentos markdown (em projeto ou tarefa)
GET    /api/documents?projectId=&taskId=
POST   /api/documents                          # { title, body, type?, projectId?, taskId? }
GET    /api/documents/:id  |  PUT /api/documents/:id  |  DELETE /api/documents/:id
GET    /api/documents/:id/export               # markdown puro

# Comentários, labels, atividade, webhooks
GET    /api/comments?taskId=     POST /api/comments        # { taskId, body }
GET    /api/labels   POST /api/labels   DELETE /api/labels/:id
POST   /api/labels/:id/tasks/:taskId   DELETE /api/labels/:id/tasks/:taskId
GET    /api/activity?entityType=&entityId=&limit=
GET/POST/PATCH/DELETE /api/webhooks            # (OWNER/MANAGER)
```

> Não existe `PATCH /tasks` (edição de campos avulsa), `POST /tasks/:id/subtasks`
> nem CRUD de colunas — subtarefas saem do `bulk` (campo `subtasks`) e as colunas
> vêm do board padrão criado junto com o projeto.

## Escopos de API key

A chave armazena `scopes` (ex.: `tasks:write`, `tasks:move`, `docs:write`), expostos
no contexto da requisição. **Hoje a autorização efetiva é pelo papel da Membership**
(OWNER/MANAGER/...); o enforcement granular por `scope` é um refinamento planejado.
Vocabulário sugerido:

```
companies:read   projects:read   projects:write
tasks:read   tasks:write   tasks:move   tasks:delete
docs:read    docs:write
members:read members:write   apikeys:manage
```

## Fluxos de agente (o Maestro Loop via API)

### A. Briefing → spec + árvore de tarefas (decompose)

```bash
# 1) (opcional) registra a spec refinada como documento
curl -X POST http://localhost:5099/api/documents -H "x-api-key: $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"projectId":2,"type":"SPEC","title":"Spec navbar","body":"# ...markdown..."}'

# 2) decompõe em tarefas + subtarefas + dependências, em uma transação
curl -X POST http://localhost:5099/api/tasks/bulk -H "x-api-key: $KEY" \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: brief-2026-06-22-navbar' \
  -d '{
    "projectId": 2,
    "items": [{
      "ref": "nav",
      "title": "Adicionar aba '\''Projetos'\'' à navbar",
      "objective": "Acessar a lista de projetos direto pela navbar.",
      "acceptance": "Item visível em desktop e mobile, rota /projects, estado ativo ok.",
      "priority": "HIGH", "estimateMd": 1.5,
      "subtasks": [
        { "ref": "design",  "title": "Definir posição, rótulo e ícone", "estimateMd": 0.25 },
        { "ref": "desktop", "title": "Link na navbar desktop", "dependsOn": ["design"], "estimateMd": 0.5 },
        { "ref": "mobile",  "title": "Adicionar ao menu mobile", "dependsOn": ["design"], "estimateMd": 0.5 },
        { "ref": "active",  "title": "routerLinkActive em /projects", "dependsOn": ["desktop","mobile"] },
        { "ref": "qa",      "title": "Testar navegação e responsividade", "dependsOn": ["active"] }
      ]
    }]
  }'
```

> `ref` é um apelido local do payload; o `dependsOn` referencia outros `ref` do
> mesmo lote. A API resolve os `ref` para IDs reais e cria as `TaskDependency` na
> mesma transação — o **fluxo nasce pronto** já no decompose (ver [doc 08](08-fluxo-de-tarefas.md)).

### B. Ver o fluxo (objetivo → passos → aceite)

```bash
curl "http://localhost:5099/api/tasks/MAESTRO-4/flow" -H "x-api-key: $KEY"
```

Resposta (resumida):

```json
{
  "task": { "code": "MAESTRO-4", "title": "Adicionar aba 'Projetos' à navbar",
            "objective": "...", "acceptance": "..." },
  "progress": { "done": 1, "total": 5 },
  "nodes": [
    { "id": "objetivo", "kind": "entry", "label": "..." },
    { "id": "t12", "code": "MAESTRO-5", "title": "Definir posição...", "state": "done" },
    { "id": "t13", "code": "MAESTRO-6", "title": "Link desktop",       "state": "todo" },
    { "id": "t14", "code": "MAESTRO-7", "title": "Menu mobile",        "state": "todo" },
    { "id": "t15", "code": "MAESTRO-8", "title": "routerLinkActive",   "state": "blocked" },
    { "id": "t16", "code": "MAESTRO-9", "title": "Testar",             "state": "blocked" },
    { "id": "aceite", "kind": "exit", "label": "..." }
  ],
  "edges": [ { "from": "objetivo", "to": "t12" }, { "from": "t12", "to": "t13" }, "..." ]
}
```

O `state` de cada subtarefa (`todo` / `blocked` / `done`) é **calculado** a partir das
dependências e da coluna atual. Use `?format=mermaid` para receber `{ "mermaid": "graph TD ..." }`.

### C. Execução → mover no quadro

```bash
# colunas vêm do board: GET /api/projects/:id/board → columns[].id
curl -X POST http://localhost:5099/api/tasks/MAESTRO-5/move -H "x-api-key: $KEY" \
  -H 'Content-Type: application/json' -d '{"columnId":10}'   # → Concluído
```

Ao concluir `MAESTRO-5`, seus dependentes (`MAESTRO-6`, `MAESTRO-7`) saem de
`blocked` para `todo` automaticamente no próximo `flow`.

## Servidor MCP (envólucro da API)

O pacote `mcp/` expõe a API como **servidor MCP** (stdio), para que agentes como o
Claude Code conversem nativamente, sem escrever REST na mão. A chave
(`MAESTRO_API_KEY`) vai na config do servidor MCP; o tenant vem da própria chave.
Ferramentas expostas (ex.): criar projeto, escrever doc, decompor em tarefas, listar
tarefas, mover no quadro, comentar.

## Segurança

- API key: armazenada **só como hash** (SHA-256); segredo exibido uma vez; `prefix`
  visível na UI para identificar a chave.
- `expiresAt` opcional + revogação imediata (`revokedAt`).
- Toda ação via chave entra no `ActivityLog` como "via agente".
- *Refinamentos planejados:* rate limit por chave, `lastUsedAt` para detectar chaves
  ociosas e enforcement por `scope`.
