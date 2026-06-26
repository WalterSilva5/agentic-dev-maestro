# Agentic Dev Maestro

Plataforma fullstack de gestão de projetos e estudos, com suporte a agentes de IA.

## Visão Geral

O Maestro combina gestão de tarefas kanban com ferramentas para agentes de IA, permitindo que equipes e agentes trabalhem juntos no ciclo de desenvolvimento.

## Componentes

| Componente | Descrição | Stack |
|------------|-----------|-------|
| **Web Client** | Interface web completa com kanban, tarefas, estudos e métricas | NestJS 8 + Angular 20 + MySQL |
| **Local Client** | Aplicação desktop offline com API local para agentes | Python + PySide6 + FastAPI + SQLite |
| **OpenCode Tools** | Ferramentas customizadas para agentes de IA | TypeScript (opencode) |

## Início Rápido

### Web Client (Docker)

```bash
cd web-client
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:4200
- API: http://localhost:5000/api
- Swagger: http://localhost:5000/api/docs

### Local Client

```bash
cd local-client
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m maestro_local
```

- GUI: http://localhost:9777 (abre automaticamente)
- API: http://127.0.0.1:9777/api

## Funcionalidades

### Gestão de Projetos
- Board kanban com drag-and-drop
- Tasks com prioridade, tipo, labels, checklist e dependências
- Comentários com suporte a markdown e code reviews
- Documentos (specs, planos, ADRs)
- Dashboard e métricas

### Módulo de Estudos
- Planos de estudo com roadmap visual
- Tópicos com progresso percentual
- Sessões de estudo com tracking de horas
- Integração com o fluxo de tarefas

### OpenCode Tools
- 12 ferramentas customizadas para agentes
- Comandos `/review` e `/decompose`
- Skill de uso da plataforma

## Estrutura

```
agentic-dev-maestro/
├── web-client/          # Cliente web (NestJS + Angular)
├── local-client/        # Cliente desktop (Python)
├── .opencode/           # Ferramentas para agentes
├── mcp/                 # Servidores MCP
├── docs/                # Documentação
├── CLAUDE.md            # Guia para agentes de IA
└── README.md            # Este arquivo
```

## Documentação

- `CLAUDE.md` — Guia completo para agentes de IA
- `web-client/README.md` — Documentação do web client
- `local-client/README.md` — Documentação do local client
- `docs/` — Diagramas e documentação adicional

## Licença

MIT
