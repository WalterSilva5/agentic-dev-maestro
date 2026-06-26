# Plano de Implementação — Ferramentas OpenCode para Maestro

## Objetivo
Criar um conjunto de ferramentas customizadas do opencode que permitam aos agentes de IA interagir com a plataforma Maestro (tasks, board, comentários, documentos) sem sair do terminal.

---

## Checklist

### 1. Custom Tools (`.opencode/tools/maestro.ts`)
| # | Ferramenta | Descrição | Status |
|---|-----------|-----------|--------|
| 1.1 | `maestro_listProjects` | Lista todos os projetos | ✅ |
| 1.2 | `maestro_board` | Consulta o board (colunas + tarefas) | ✅ |
| 1.3 | `maestro_getTask` | Detalhes de uma tarefa | ✅ |
| 1.4 | `maestro_listTasks` | Lista tarefas com filtros | ✅ |
| 1.5 | `maestro_createTask` | Cria tarefa | ✅ |
| 1.6 | `maestro_updateTask` | Edita campos da tarefa | ✅ |
| 1.7 | `maestro_moveTask` | Move tarefa entre colunas | ✅ |
| 1.8 | `maestro_deleteTask` | Exclui tarefa | ✅ |
| 1.9 | `maestro_addSubtask` | Adiciona subtarefa (só título) | ✅ |
| 1.10 | `maestro_addComment` | Posta comentário (code review, commits) | ✅ |
| 1.11 | `maestro_getFlow` | Exporta fluxo da tarefa (mermaid) | ✅ |
| 1.12 | `maestro_createDocument` | Cria documento (spec, plan, ADR) | ✅ |

### 2. Custom Commands (`.opencode/commands/`)
| # | Comando | Descrição | Status |
|---|---------|-----------|--------|
| 2.1 | `/review` | Abre prompt para fazer code review de uma tarefa | ✅ |
| 2.2 | `/decompose` | Abre prompt para decompor tarefa em subtarefas | ✅ |

### 3. Skill (`.opencode/skills/maestro-platform/`)
| # | Skill | Descrição | Status |
|---|-------|-----------|--------|
| 3.1 | SKILL.md | Instrui agentes a usarem a plataforma automaticamente | ✅ |

### 4. Configuração
| # | Item | Descrição | Status |
|---|------|-----------|--------|
| 4.1 | Variáveis de ambiente | `MAESTRO_API_URL` e `MAESTRO_API_KEY` | ✅ |
| 4.2 | opencode.json | Configuração do projeto | ✅ |

---

## Como Usar

### Variáveis de Ambiente
Configure no seu `opencode.jsonc` ou exporte no terminal:
```bash
export MAESTRO_API_URL=http://localhost:5000/api
export MAESTRO_API_KEY=adm_4752211dbdabb2214960a05d3991dc2961973a4270cd1243
```

### Exemplos de Uso
```bash
# No terminal com opencode:
"liste os projetos usando maestro_listProjects"
"mostre o board do projeto MAESTRO"
"crie uma tarefa no backlog do MAESTRO chamada 'Implementar X'"
"adicione um comentário de code review na MAESTRO-10"
"decomponha a MAESTRO-42 em subtarefas usando /decompose"
```

---

## Estrutura de Arquivos

```
.opencode/
├── tools/
│   └── maestro.ts           # 12 ferramentas customizadas
├── commands/
│   ├── review.md            # /review - code review
│   └── decompose.md         # /decompose - decompor tarefas
└── skills/
    └── maestro-platform/
        └── SKILL.md         # Skill de uso da plataforma
```
