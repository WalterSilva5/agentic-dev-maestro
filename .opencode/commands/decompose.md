---
description: Decompõe uma tarefa em subtarefas e posta o plano
---

You are decomposing the task $1 into smaller subtasks.

1. Use `maestro_getTask` to get the full details of the task.
2. Use `maestro_board` with the task's projectId to understand the current board state and column structure.
3. Analyze the task objective and acceptance criteria, then propose a decomposition into 3-8 subtasks.
   Each subtask MUST have:
   - A clear, actionable title (short imperative phrase)
   - Subtasks have ONLY titles — no descriptions, no comments (all context stays on the main task)

4. For each subtask, use `maestro_addSubtask` with the task's code and the subtask title.
5. Post a comment on the main task using `maestro_addComment` summarizing the decomposition plan:

```markdown
## Plano de Decomposição

| # | Subtarefa |
|---|-----------|
| 1 | Título da subtarefa 1 |
| 2 | Título da subtarefa 2 |
...
```
