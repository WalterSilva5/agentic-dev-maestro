> 🇬🇧 [English version](PLANO_FERRAMENTAS.md)

# Plano de Implementação — Ferramentas OpenCode para Relay

## Objetivo
Criar um conjunto de ferramentas customizadas do opencode que permitam aos agentes de IA interagir com a plataforma Relay (tasks, board, comentários, documentos) sem sair do terminal.

---

## Checklist

### 1. Custom Tools (`.opencode/tools/relay.ts`)
| # | Ferramenta | Descrição | Status |
|---|-----------|-----------|--------|
| 1.1 | `relay_listProjects` | Lista todos os projetos | ✅ |
| 1.2 | `relay_board` | Consulta o board (colunas + tarefas) | ✅ |
| 1.3 | `relay_getTask` | Detalhes de uma tarefa | ✅ |
| 1.4 | `relay_listTasks` | Lista tarefas com filtros | ✅ |
| 1.5 | `relay_createTask` | Cria tarefa | ✅ |
| 1.6 | `relay_updateTask` | Edita campos da tarefa | ✅ |
| 1.7 | `relay_moveTask` | Move tarefa entre colunas | ✅ |
| 1.8 | `relay_deleteTask` | Exclui tarefa | ✅ |
| 1.9 | `relay_addSubtask` | Adiciona subtarefa (só título) | ✅ |
| 1.10 | `relay_addComment` | Posta comentário (code review, commits) | ✅ |
| 1.11 | `relay_getFlow` | Exporta fluxo da tarefa (mermaid) | ✅ |
| 1.12 | `relay_createDocument` | Cria documento (spec, plan, ADR) | ✅ |

### 2. Custom Commands (`.opencode/commands/`)
| # | Comando | Descrição | Status |
|---|---------|-----------|--------|
| 2.1 | `/review` | Abre prompt para fazer code review de uma tarefa | ✅ |
| 2.2 | `/decompose` | Abre prompt para decompor tarefa em subtarefas | ✅ |

### 3. Skill (`.opencode/skills/relay-platform/`)
| # | Skill | Descrição | Status |
|---|-------|-----------|--------|
| 3.1 | SKILL.md | Instrui agentes a usarem a plataforma automaticamente | ✅ |

### 4. Configuração
| # | Item | Descrição | Status |
|---|------|-----------|--------|
| 4.1 | Variáveis de ambiente | `RELAY_API_URL` e `RELAY_API_KEY` | ✅ |
| 4.2 | opencode.json | Configuração do projeto | ✅ |

---

## Como Usar

### Variáveis de Ambiente
Configure no seu `opencode.jsonc` ou exporte no terminal:
```bash
export RELAY_API_URL=http://localhost:5000/api
export RELAY_API_KEY=adm_4752211dbdabb2214960a05d3991dc2961973a4270cd1243
```

### Exemplos de Uso
```bash
# No terminal com opencode:
"liste os projetos usando relay_listProjects"
"mostre o board do projeto RELAY"
"crie uma tarefa no backlog do RELAY chamada 'Implementar X'"
"adicione um comentário de code review na RELAY-10"
"decomponha a RELAY-42 em subtarefas usando /decompose"
```

---

## Estrutura de Arquivos

```
.opencode/
├── tools/
│   └── relay.ts           # 12 ferramentas customizadas
├── commands/
│   ├── review.md            # /review - code review
│   └── decompose.md         # /decompose - decompor tarefas
└── skills/
    └── relay-platform/
        └── SKILL.md         # Skill de uso da plataforma
```
