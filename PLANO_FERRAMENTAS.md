> 🇧🇷 [Versão em português](PLANO_FERRAMENTAS.ptbr.md)

# Implementation Plan — OpenCode Tools for Maestro

## Goal
Create a set of custom opencode tools that let AI agents interact with the Maestro platform (tasks, board, comments, documents) without leaving the terminal.

---

## Checklist

### 1. Custom Tools (`.opencode/tools/maestro.ts`)
| # | Tool | Description | Status |
|---|-----------|-----------|--------|
| 1.1 | `maestro_listProjects` | Lists all projects | ✅ |
| 1.2 | `maestro_board` | Queries the board (columns + tasks) | ✅ |
| 1.3 | `maestro_getTask` | Details of a task | ✅ |
| 1.4 | `maestro_listTasks` | Lists tasks with filters | ✅ |
| 1.5 | `maestro_createTask` | Creates a task | ✅ |
| 1.6 | `maestro_updateTask` | Edits task fields | ✅ |
| 1.7 | `maestro_moveTask` | Moves a task between columns | ✅ |
| 1.8 | `maestro_deleteTask` | Deletes a task | ✅ |
| 1.9 | `maestro_addSubtask` | Adds a subtask (title only) | ✅ |
| 1.10 | `maestro_addComment` | Posts a comment (code review, commits) | ✅ |
| 1.11 | `maestro_getFlow` | Exports the task flow (mermaid) | ✅ |
| 1.12 | `maestro_createDocument` | Creates a document (spec, plan, ADR) | ✅ |

### 2. Custom Commands (`.opencode/commands/`)
| # | Command | Description | Status |
|---|---------|-----------|--------|
| 2.1 | `/review` | Opens a prompt to do a code review of a task | ✅ |
| 2.2 | `/decompose` | Opens a prompt to decompose a task into subtasks | ✅ |

### 3. Skill (`.opencode/skills/maestro-platform/`)
| # | Skill | Description | Status |
|---|-------|-----------|--------|
| 3.1 | SKILL.md | Instructs agents to use the platform automatically | ✅ |

### 4. Configuration
| # | Item | Description | Status |
|---|------|-----------|--------|
| 4.1 | Environment variables | `MAESTRO_API_URL` and `MAESTRO_API_KEY` | ✅ |
| 4.2 | opencode.json | Project configuration | ✅ |

---

## How to Use

### Environment Variables
Configure them in your `opencode.jsonc` or export them in the terminal:
```bash
export MAESTRO_API_URL=http://localhost:5000/api
export MAESTRO_API_KEY=adm_4752211dbdabb2214960a05d3991dc2961973a4270cd1243
```

### Usage Examples
```bash
# In the terminal with opencode:
"list the projects using maestro_listProjects"
"show the board for the MAESTRO project"
"create a task in the MAESTRO backlog called 'Implement X'"
"add a code review comment on MAESTRO-10"
"decompose MAESTRO-42 into subtasks using /decompose"
```

---

## File Structure

```
.opencode/
├── tools/
│   └── maestro.ts           # 12 custom tools
├── commands/
│   ├── review.md            # /review - code review
│   └── decompose.md         # /decompose - decompose tasks
└── skills/
    └── maestro-platform/
        └── SKILL.md         # Platform usage skill
```
