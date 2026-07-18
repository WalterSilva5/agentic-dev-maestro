# Planos

Diretório de planos técnicos e de migração do projeto. Cada plano avalia opções,
recomenda um caminho e estima esforço em **homem-dia (HD)**; alocação e cronograma
são decisão de liderança.

## Índice

- [Melhorias de componentes e do fluxo de Reuniões](melhorias-reunioes.ptbr.md)
  ([EN](melhorias-reunioes.md)) — diagnóstico medido no código (view de 2221
  linhas, 103 métodos, 129 atributos) e plano em 5 fases: componentização,
  camadas de persistência/IA, fluxo e otimização de recursos (~20 HD).

- [Migração de front-end responsivo (Flutter vs web vs Qt)](migracao-frontend-responsivo.ptbr.md)
  ([EN](migracao-frontend-responsivo.md)) — avalia migrar a UI de PySide6/Qt para
  Flutter ou para a web UI React já existente; recomenda a rota **web** (React +
  daemon Python de captura/Whisper/IA + shell pywebview) em vez de Flutter, com
  roadmap por fases.
