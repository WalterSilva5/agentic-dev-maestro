# 09 — Modulo de Estudos

## Contexto

O Maestro hoje resolve tracking de tarefas de desenvolvimento. A ideia é expandir para que tambem funcione como ferramenta de acompanhamento de estudos pessoais — permitindo definir um roadmap de aprendizado, quebrar em topicos/etapas, acompanhar progresso percentual e manter notas de estudo integradas ao fluxo existente.

O objetivo nao é criar um app separado, mas integrar estudos como um modulo dentro do Maestro, reaproveitando o maximo da infraestrutura existente (projetos, tarefas, kanban, notas diarias, Obsidian).

---

## Conceitos principais

### Plano de Estudo (StudyPlan)

Um plano de estudo é um container que representa um percurso completo — ex: "Aprender Rust", "Certificacao AWS SAA", "Algoritmos e Estruturas de Dados".

Cada plano tem:
- **Titulo** e **descricao**
- **Categoria** (linguagem, framework, certificacao, conceito, curso, livro)
- **Status** (planejado, em andamento, pausado, concluido, abandonado)
- **Data inicio / data alvo** (opcional, para prazos pessoais)
- **Progresso geral** (calculado automaticamente a partir dos topicos)
- **Recursos** (links, livros, cursos — lista livre)
- **Projeto vinculado** (opcional — pode vincular a um projeto existente do Maestro para usar o kanban)

### Topico de Estudo (StudyTopic)

Cada plano é dividido em topicos ordenados que formam o roadmap. Um topico pode ter sub-topicos (hierarquia de 1 nivel).

Cada topico tem:
- **Titulo**
- **Descricao** (o que cobrir, por que importa)
- **Ordem** no roadmap
- **Status** (pendente, estudando, revisao, concluido, pulado)
- **Peso** (default 1 — permite dar mais importancia a topicos maiores)
- **Estimativa de horas** (opcional)
- **Horas registradas** (tracking de tempo)
- **Notas** (markdown livre — anotacoes do estudo)
- **Recursos** (links especificos do topico)
- **Parent** (para sub-topicos)

### Sessao de Estudo (StudySession)

Registro de quando o usuario sentou pra estudar. Pode ser manual ou com timer.

- **Topico vinculado**
- **Data/hora inicio e fim**
- **Duracao** (minutos)
- **Notas da sessao** (o que aprendeu, duvidas, insights)
- **Nivel de confianca** (1-5: quao bem entendeu o topico)

---

## Calculo de progresso

O progresso percentual do plano é calculado com base nos topicos:

```
progresso = soma(peso dos topicos concluidos) / soma(peso de todos os topicos) * 100
```

Topicos com status "pulado" nao contam no denominador (foram removidos do escopo).

Sub-topicos contribuem proporcionalmente ao peso do topico pai:
- Se um topico pai tem peso 3 e 2 de 4 sub-topicos estao concluidos, ele contribui com 1.5 (3 * 0.5).

---

## Modelo de dados

```
StudyPlan
  id            INTEGER PK
  title         VARCHAR(200) NOT NULL
  description   TEXT
  category      VARCHAR(40)   -- linguagem, framework, certificacao, conceito, curso, livro
  status        VARCHAR(20)   -- planejado, em_andamento, pausado, concluido, abandonado
  start_date    DATE
  target_date   DATE
  resources     TEXT          -- JSON array de {title, url, type}
  project_id    INTEGER FK    -- opcional, vinculo com Project existente
  created_at    DATETIME
  updated_at    DATETIME

StudyTopic
  id            INTEGER PK
  plan_id       INTEGER FK -> StudyPlan
  parent_id     INTEGER FK -> StudyTopic (nullable, para sub-topicos)
  title         VARCHAR(200) NOT NULL
  description   TEXT
  sort_order    INTEGER
  status        VARCHAR(20)   -- pendente, estudando, revisao, concluido, pulado
  weight        FLOAT DEFAULT 1.0
  estimate_hours FLOAT
  logged_hours  FLOAT DEFAULT 0
  notes         TEXT          -- markdown
  resources     TEXT          -- JSON array
  created_at    DATETIME
  updated_at    DATETIME

StudySession
  id            INTEGER PK
  topic_id      INTEGER FK -> StudyTopic
  plan_id       INTEGER FK -> StudyPlan
  started_at    DATETIME
  ended_at      DATETIME
  duration_min  INTEGER
  notes         TEXT
  confidence    INTEGER       -- 1 a 5
  created_at    DATETIME
```

---

## Interface (GUI)

### Nova pagina: "Estudos" no sidebar

Posicao no menu: entre "Diario" e "Board" (Alt+2).

### Tela principal: lista de planos

- Cards com titulo, categoria, status, barra de progresso percentual
- Filtros por status e categoria
- Botao "Novo Plano"
- Ordenacao por ultimo acesso, progresso, data alvo

### Tela de plano: roadmap visual

- Header com titulo, descricao, progresso geral (barra + percentual)
- Estatisticas: topicos concluidos/total, horas estimadas vs registradas
- Lista de topicos como timeline/roadmap vertical:
  - Cada topico mostra: titulo, status (badge colorido), barra de progresso (sub-topicos), horas
  - Topico expandivel para ver sub-topicos e notas
  - Drag-and-drop para reordenar
- Painel lateral ou dialog para editar topico:
  - Titulo, descricao, notas (markdown), recursos
  - Status (dropdown)
  - Registro de sessao de estudo (botao "Registrar sessao")
- Botao "Iniciar sessao" (timer simples)

### Tela de sessao de estudo

- Timer (opcional — pode registrar manualmente)
- Campo de notas (markdown)
- Slider de confianca (1-5)
- Ao finalizar: salva sessao e atualiza horas do topico

### Integracao com Diario

- Na pagina "Diario de Trabalho", mostrar sessoes de estudo do dia
- No relatorio gerado, incluir secao "Estudos" com:
  - Sessoes realizadas
  - Horas de estudo
  - Topicos avancados

### Integracao com Obsidian

Na sincronizacao do vault, exportar:
```
Vault/
  Estudos/
    NomePlano/
      README.md          -- overview, progresso, recursos
      Roadmap.md         -- lista de topicos com status
      Topicos/
        01-TopicA.md     -- notas do topico
        02-TopicB.md
      Sessoes/
        2026-06-25.md    -- sessoes do dia
```

### Integracao com projeto (opcional)

Se o plano estiver vinculado a um projeto:
- Cada topico pode gerar uma tarefa no kanban (acao manual "Criar tarefa")
- A tarefa mantem referencia ao topico
- Concluir a tarefa marca o topico como concluido

---

## API endpoints

```
GET    /api/study/plans                    -- listar planos
POST   /api/study/plans                    -- criar plano
GET    /api/study/plans/:id                -- detalhe do plano (com topicos)
PATCH  /api/study/plans/:id                -- atualizar plano
DELETE /api/study/plans/:id                -- remover plano

GET    /api/study/plans/:id/topics         -- listar topicos do plano
POST   /api/study/plans/:id/topics         -- criar topico
PATCH  /api/study/topics/:id               -- atualizar topico
DELETE /api/study/topics/:id               -- remover topico
PATCH  /api/study/plans/:id/topics/reorder -- reordenar topicos

POST   /api/study/sessions                 -- registrar sessao
GET    /api/study/sessions?date=YYYY-MM-DD -- sessoes por data
GET    /api/study/plans/:id/sessions       -- sessoes do plano

GET    /api/study/stats                    -- estatisticas gerais (horas, planos ativos, streak)
```

---

## Fases de implementacao

### Fase 1 — Fundacao (MVP)
- Modelos SQLAlchemy: StudyPlan, StudyTopic, StudySession
- Migracao do banco
- Endpoints CRUD basicos
- Pagina "Estudos" no sidebar com lista de planos
- Tela de criacao/edicao de plano
- Lista de topicos com status e reordenacao
- Calculo de progresso

### Fase 2 — Sessoes e tracking
- Registro de sessoes de estudo (manual)
- Timer simples (opcional)
- Horas registradas por topico
- Slider de confianca
- Integracao com Diario (mostrar sessoes do dia no relatorio)

### Fase 3 — Visualizacao e polish
- Roadmap visual (timeline vertical)
- Graficos de progresso ao longo do tempo
- Streak de estudo (dias consecutivos)
- Estatisticas na pagina de Metricas
- Integracao com Obsidian (export de planos e notas)

### Fase 4 — Integracao com projetos
- Vincular plano a projeto
- Gerar tarefas a partir de topicos
- Sincronizar status topico <-> tarefa

---

## Decisoes em aberto

1. **Timer**: implementar timer real (com notificacao) ou apenas registro manual de horas?
2. **Gamificacao**: adicionar streak, badges, XP? Pode motivar mas tambem adiciona complexidade.
3. **Importacao de roadmaps**: permitir colar um roadmap em markdown e parsear automaticamente em topicos?
4. **Flashcards/revisao espaçada**: faz sentido integrar revisao espaçada (tipo Anki) aos topicos? Pode ser um modulo futuro.
5. **Compartilhamento**: exportar plano como template para reusar? Ex: "Roadmap Rust" que qualquer um pode importar.
