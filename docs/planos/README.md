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

- [Decisão de toolkit de UI (Flutter vs Java vs web)](migracao-toolkit-ui.ptbr.md)
  ([EN](migracao-toolkit-ui.md)) — reabre a comparação a pedido incluindo
  **Flutter** e **Java** explicitamente. Mostra que a captura de áudio + Whisper
  fica em Python em qualquer opção; descarta **Java** (menos moderno), mantém a
  **rota web** como recomendação (~14–21 HD) e detalha o plano Flutter
  (~27–50 HD) caso mobile nativo seja requisito.

- [Eficiência de recursos](eficiencia-recursos.ptbr.md)
  ([EN](eficiencia-recursos.md)) — separa causa real de percepção ("Python
  pesa"): o custo está no modelo Whisper residente e no processo gordo (Qt + API
  + ML juntos), não na linguagem. Registra o que já foi aplicado (liberar Whisper
  ocioso, widget por evento) e o que falta (imports/telas tardios, daemon
  headless); a eficiência vem de arquitetura, não de trocar a UI.

- [Implementação do front-end Flutter](frontend-flutter.ptbr.md)
  ([EN](frontend-flutter.md)) — **plano de execução** da decisão por Flutter
  (backend Python permanece como daemon). Tarefas e subtarefas em 6 fases:
  fundação, 18 telas CRUD sobre os 127 endpoints existentes, backend de Reuniões
  (a única funcionalidade sem API), Reuniões no Flutter, paridade/empacotamento
  e mobile opcional (~45–59 HD). O contrato OpenAPI 3.1 permite **gerar** o
  cliente Dart.
