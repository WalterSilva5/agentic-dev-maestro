# Agentic Dev Maestro — Guia de Uso da Plataforma

> **Versão:** 1.0  
> **Propósito:** Skill de referência rápida para usuários e agentes de IA que interagem com a plataforma.

---

## 1. O que é o Agentic Dev Maestro

O **Agentic Dev Maestro** (ou apenas **Maestro**) é uma plataforma que transforma briefings brutos
em documentação estruturada, decomposição em tarefas, e um quadro kanban com execução por
**agentes de IA**.

### O "Maestro Loop"

```
1. BRIEFING   → alguém joga uma descrição crua de tarefa/projeto
2. REFINO     → um agente transforma em doc estruturada
3. DECOMPOSE  → o agente quebra em tarefas → subtarefas
4. QUADRO     → tudo cai num kanban com colunas configuráveis
5. EXECUÇÃO   → agentes executam e mantêm status sincronizado
6. VISÃO      → gerentes e tech leads veem ao vivo
```

---

## 2. Primeiros Passos

### 2.1 Acessar a Plataforma

- **Frontend:** `http://localhost:4200`
- **API:** `http://localhost:5000/api`
- **Swagger:** `http://localhost:5000/api/docs`

### 2.2 Login

Use as credenciais padrão do seed:

| Papel | Email | Senha |
|-------|-------|-------|
| Admin | admin@template.com | Admin@123 |
| User | user@template.com | User@123 |

### 2.3 Selecionar Empresa

Após o login, selecione uma empresa (tenant). O `X-Company-Id` é enviado automaticamente
em todas as requisições para isolar dados entre empresas.

### 2.4 Criar um Projeto

1. Vá para **Projetos** na navbar
2. Clique em **Novo Projeto**
3. Preencha: nome, key (sigla, ex: `PROJ`) e descrição
4. Um quadro kanban com 5 colunas padrão é criado automaticamente

---

## 3. Gerenciamento de Tarefas

### 3.1 Criar Tarefa

No quadro kanban, clique no input "Adicionar tarefa" da coluna desejada.

### 3.2 Mover Tarefa (Drag & Drop)

Arraste o card da tarefa entre as colunas do kanban. A mudança é persistida via API.

### 3.3 Fluxo da Tarefa

Cada tarefa pode ter:

- **Objetivo** — o que deve ser alcançado (entrada do fluxo)
- **Subtarefas** — passos concretos para cumprir o objetivo
- **Critérios de Aceite** — condição para considerar a tarefa concluída
- **Dependências** — arestas orientadas formando um DAG (Directed Acyclic Graph)

Acesse **Fluxo** no detalhe da tarefa para ver o grafo visual.

### 3.4 Prioridades

| Prioridade | Cor |
|------------|-----|
| URGENT | Vermelho |
| HIGH | Amarelo |
| MEDIUM | Azul |
| LOW | Cinza |

---

## 4. Quadro Kanban

### 4.1 Colunas Padrão

| Coluna | Descrição |
|--------|-----------|
| Backlog | Ideias e tarefas não priorizadas |
| A fazer | Priorizadas e prontas para execução |
| Fazendo | Em execução |
| Revisão | Aguardando review |
| Concluído | Finalizadas |

### 4.2 Limites de WIP

Não implementado por padrão, mas o modelo de dados suporta `wipLimit` por coluna.

---

## 5. Membros e Papéis (RBAC)

### 5.1 Papéis

| Papel | Permissões |
|-------|------------|
| `OWNER` | Acesso total, pode gerenciar membros e API keys |
| `ADMIN` | Acesso total exceto remoção de OWNER |
| `MANAGER` | Gerenciar tarefas e membros |
| `MEMBER` | Visualizar e criar tarefas |
| `VIEWER` | Apenas leitura |

### 5.2 Convidar Membros

1. Vá em **Membros** na sidebar
2. Clique em **Adicionar Membro**
3. Informe o email e o papel

---

## 6. API Keys (Agentes)

### 6.1 Criar uma API Key

```bash
# Pelo frontend: vá em API Keys > Nova API Key
# Pela API (requer token de admin):
curl -X POST http://localhost:5000/api/companies/1/api-keys \
  -H "Authorization: Bearer <seu_token>" \
  -H "Content-Type: application/json" \
  -d '{"label":"Meu Agente","scopes":["tasks:write"]}'
```

### 6.2 Usar a API Key

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "x-api-key: sua_api_key_aqui" \
  -H "Content-Type: application/json" \
  -d '{"projectId":1,"title":"Minha tarefa"}'
```

### 6.3 Mover Tarefa via API

```bash
curl -X POST http://localhost:5000/api/tasks/PROJ-1/move \
  -H "x-api-key: sua_api_key_aqui" \
  -H "Content-Type: application/json" \
  -d '{"columnId":3}'
```

---

## 7. Servidor MCP

O Maestro expõe um servidor **MCP (Model Context Protocol)** para integração com
agentes de IA (Claude, Cursor, etc.).

### Tools Disponíveis

| Tool | Descrição |
|------|-----------|
| `create_task` | Cria tarefa no projeto |
| `move_task` | Move tarefa entre colunas |
| `get_board` | Obtém quadro completo |
| `list_projects` | Lista projetos |
| `get_task_flow` | Obtém grafo de dependências |
| `bulk_create` | Cria tarefas em lote |

### Configurar no Cliente MCP

```json
{
  "mcpServers": {
    "maestro": {
      "command": "node",
      "args": ["caminho/para/mcp/index.js"],
      "env": {
        "MAESTRO_API_URL": "http://localhost:5000/api",
        "MAESTRO_API_KEY": "sua_api_key_aqui"
      }
    }
  }
}
```

---

## 8. Webhooks

Webhooks permitem notificar sistemas externos quando eventos ocorrem.

### Eventos Disponíveis

| Evento | Disparado quando |
|--------|------------------|
| `task.created` | Tarefa criada |
| `task.moved` | Tarefa movida de coluna |
| `task.updated` | Tarefa atualizada |

### Configurar Webhook

```bash
curl -X POST http://localhost:5000/api/webhooks \
  -H "x-api-key: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://meu-sistema.com/webhook",
    "events": ["task.created", "task.moved"],
    "secret": "meu-secret"
  }'
```

---

## 9. Documentos

Cada tarefa pode ter documentos anexados (especificações, planos, ADRs).

### Tipos de Documento

| Tipo | Uso |
|------|-----|
| `SPEC` | Especificação técnica |
| `PLAN` | Plano de implementação |
| `NOTES` | Notas e observações |
| `ADR` | Architecture Decision Record |
| `OTHER` | Outros |

### Download de Documentos

Use o botão **Exportar** no detalhe da tarefa para baixar o documento em formato Markdown.

---

## 10. Idempotência (Bulk Operations)

Operações em massa (`/tasks/bulk`) suportam o header `Idempotency-Key`:

```bash
curl -X POST http://localhost:5000/api/tasks/bulk \
  -H "x-api-key: sua_api_key" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: meu-idempotente-123" \
  -d '{
    "projectId": 1,
    "items": [
      {"title": "Tarefa 1"},
      {"title": "Tarefa 2"}
    ]
  }'
```

Se a mesma `Idempotency-Key` for reenviada, a operação não é duplicada.

---

## 11. Boas Práticas

1. **Use o fluxo (objetivo → subtarefas → aceite)** para tarefas complexas
2. **Defina dependências** entre subtarefas para garantir a ordem correta
3. **Utilize etiquetas (labels)** para categorizar tarefas
4. **Mantenha a documentação** atualizada junto com as tarefas
5. **Use API keys com escopos limitados** para agentes específicos
6. **Habilite webhooks** para integrar com CI/CD e notificações

---

## 12. Troubleshooting

### Erro 401 (Unauthorized)

- Verifique se o token JWT não expirou (faça login novamente)
- Para API key, confirme se ela não foi revogada ou expirou

### Erro 404 (Not Found)

- Confirme o `X-Company-Id` correto
- Verifique se o recurso existe na empresa selecionada

### Erro 500 (Internal Server Error)

- Verifique os logs do container: `docker compose logs api`
- Confirme se o MySQL e Redis estão saudáveis

---

## 13. Comandos Úteis

```bash
# Subir a plataforma
docker compose up --build -d

# Ver logs da API
docker compose logs -f api

# Aplicar migrations (caso necessário)
npm --prefix back run prisma:migrate

# Seed (usuários iniciais)
npm --prefix back run prisma:seed

# Verificar saúde da API
curl http://localhost:5000/api/health
```

---

*Skill gerada automaticamente pelo Agentic Dev Maestro.*  
*Para atualizações, consulte a aba Downloads na plataforma.*
