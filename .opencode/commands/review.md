---
description: Faz code review de uma tarefa e posta como comentário
---

You are reviewing the task $1.

1. Use `maestro_getTask` to get the full details of the task.
2. Use `maestro_getFlow` with format=mermaid to see the task flow and subtasks.
3. Analyze the task, its context in the project, and propose a code review covering:
   - Architecture and design decisions
   - Potential issues or edge cases
   - Suggestions for improvement
   - Acceptance criteria validation

Post the review as a comment using `maestro_addComment` with the task ID and a well-formatted markdown review. Use code blocks with appropriate language tags for any code snippets.
