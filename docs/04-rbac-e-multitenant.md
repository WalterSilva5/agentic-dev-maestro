# 04 — RBAC e multi-tenant

## Multi-tenancy

- **Tenant = Company.** Um usuário pode pertencer a várias empresas (uma
  `Membership` por empresa), com papel possivelmente diferente em cada uma.
- **Isolamento row-level:** toda entidade de domínio carrega `companyId`. Um guard
  global resolve a empresa do contexto (do JWT/Membership ou da API key) e **toda
  query é filtrada por `companyId`**. Sem exceção — é a defesa contra vazamento
  entre tenants.
- O `companyId` **nunca** vem do corpo da requisição confiável: vem do token/chave.

### Resolução de contexto por requisição

```
Humano (JWT)   → token identifica o User → escolhe a empresa ativa
                 (header X-Company-Id ou rota /companies/:id/...) →
                 carrega a Membership → papel + permissões
Agente (key)   → x-api-key → ApiKey → Membership → companyId + papel
                 (papel define a permissão; scopes da chave: refinamento planejado)
```

## Papéis e matriz de permissões

| Ação | OWNER | MANAGER | TECH_LEAD | DEV | VIEWER |
|---|:--:|:--:|:--:|:--:|:--:|
| Ver projetos/quadros/tarefas | ✅ | ✅ | ✅ | ✅ | ✅ |
| Criar/editar tarefas | ✅ | ✅ | ✅ | ✅ | ❌ |
| Mover tarefas no quadro | ✅ | ✅ | ✅ | ✅ | ❌ |
| Excluir tarefas | ✅ | ✅ | ✅ | ⚠️ próprias | ❌ |
| Escrever docs | ✅ | ✅ | ✅ | ✅ | ❌ |
| Criar/configurar projetos e quadros | ✅ | ✅ | ✅ | ❌ | ❌ |
| Gerenciar membros (convidar / mudar papel) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Gerenciar API keys | ✅ | ✅ | ⚠️ próprias | ⚠️ próprias | ❌ |
| Configurar/excluir a empresa, transferir posse | ✅ | ❌ | ❌ | ❌ | ❌ |

⚠️ = restrito a recursos próprios.

### Notas

- **OWNER** é o responsável pela empresa (quem a criou ou recebeu a posse). Pode
  rebaixar/remover qualquer um, exceto outro OWNER (transferência de posse explícita).
- **MANAGER** gerencia o dia a dia: membros, projetos, quadros, tarefas — mas não
  destrói a empresa nem mexe em OWNERs.
- **TECH_LEAD** manda no técnico (projetos, quadros, tarefas, docs, revisão), mas não
  gerencia pessoas.
- **DEV** é o executor: cria/edita/move tarefas e escreve docs.
- **VIEWER** é só leitura — ideal para stakeholders/gerentes que apenas consomem a
  visão (gera os mesmos relatórios markdown de hoje, sem poder editar).

## Agentes e permissões

> **Estado atual:** a autorização efetiva de uma API key é dada pelo **papel da
> Membership** (`@RequireRole` no guard). Os `scopes` já são **armazenados** na chave
> e expostos no contexto, mas o enforcement granular por escopo é um **refinamento
> planejado**. A descrição abaixo é o design-alvo (papel ∩ scopes).

A permissão efetiva de uma API key é **a interseção** do papel da Membership com os
`scopes` da chave. Exemplos:

- Chave num membro **DEV** com escopo `tasks:write tasks:move docs:write` → pode
  executar o loop, mas nunca gerenciar membros (o papel já barra).
- Chave num membro **MANAGER** mas com escopo só `tasks:read` → apesar do papel
  alto, a chave só lê (princípio do menor privilégio para agentes).

Recomendação: **agentes executores** usam uma Membership dedicada de papel `DEV`
(ou um papel `AGENT` futuro) com escopos mínimos, para deixar a auditoria limpa
(toda ação do agente fica atribuída àquela identidade).

## Auditoria

Toda escrita grava em `ActivityLog`: `actorUserId` + `viaApiKeyId` (se agente) +
`action` + `changes` (diff). Isso responde "quem mudou o status / criou a tarefa /
editou a doc — humano ou agente, e qual chave".
