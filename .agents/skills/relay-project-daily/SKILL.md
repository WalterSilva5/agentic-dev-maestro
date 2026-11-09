---
name: relay-project-daily
description: Lê, filtra, cria e edita o Daily do projeto no Relay Local (registro diário de trabalho por dia, no board do projeto). Use quando o usuário pedir "o que foi feito no projeto ontem", "daily do projeto", "registra no daily", "resume a semana do projeto", "histórico de trabalho do projeto", "o que o time fez no dia X", ou quando um agente precisar reconstruir andamento do projeto por data.
---

# Relay — Daily do projeto (registro de trabalho por dia)

O **Daily do projeto** é um diário de trabalho: cada registro é um comentário
com **dia**, **tipo**, **texto**, autor e (opcional) minutos e card. Serve de
documento de daily e de fonte para agentes reconstruírem o andamento.

Diferente de:
- **`Comment`** → comentário de um card específico.
- **`DailyNote`** (`/api/daily/{date}`) → nota global do dia (Meu Dia), não por projeto.

## Onde aparece

- **Desktop**: Board do projeto → aba **📝 Daily**.
- **Web**: Board do projeto → aba **📝 Daily** (`/board/{id}`).
- **API**: `/api/projects/{id}/daily` (ver abaixo).

## API (base `http://127.0.0.1:9777`)

### Listar / filtrar
```bash
GET /api/projects/{projectId}/daily
    ?date=YYYY-MM-DD          # dia exato
    &dateFrom=YYYY-MM-DD      # intervalo (início)
    &dateTo=YYYY-MM-DD        # intervalo (fim)
    &kind=WORK|BLOCKER|DECISION|NOTE
    &author=nome              # busca parcial, case-insensitive
    &q=texto                  # busca no corpo
    &limit=200
```
Retorna lista ordenada do **mais recente** para o mais antigo.

```bash
# o que foi feito ontem
curl -s "http://127.0.0.1:9777/api/projects/2/daily?date=$(date -d yesterday +%F)" | jq

# semana atual, só bloqueios
curl -s "http://127.0.0.1:9777/api/projects/2/daily?dateFrom=$(date -d 'monday -7 days' +%F)&kind=BLOCKER" | jq

# busca livre
curl -s "http://127.0.0.1:9777/api/projects/2/daily?q=cashier" | jq '.[].body'
```

### Criar
```bash
curl -s -X POST "http://127.0.0.1:9777/api/projects/2/daily" \
  -H 'Content-Type: application/json' \
  -d '{
    "body": "Implementei a abertura de caixa e validei em loja 208",
    "date": "2026-11-08",
    "kind": "WORK",
    "author": "walter",
    "minutes": 90,
    "taskCode": "MIG-13973"
  }' | jq
```
- `date` ausente → **hoje**.
- `kind` ausente → `WORK`. Tipo inválido → `400`.
- `body` vazio/só espaços → `400`.

### Editar
```bash
curl -s -X PATCH "http://127.0.0.1:9777/api/project-daily/12" \
  -H 'Content-Type: application/json' \
  -d '{"body": "texto revisado", "kind": "DECISION", "minutes": 45}' | jq
```
Aceita `body`, `date`, `kind`, `author`, `minutes`, `taskCode` (todos opcionais).

### Excluir
```bash
curl -s -X DELETE "http://127.0.0.1:9777/api/project-daily/12"
```

### Resumo (para painéis e relatórios)
```bash
curl -s "http://127.0.0.1:9777/api/projects/2/daily/summary?dateFrom=2026-11-01&dateTo=2026-11-30" | jq
# { total, totalMinutes, byKind: {WORK, BLOCKER, DECISION, NOTE}, byAuthor: {...},
#   days: [{date, entries, minutes, authors}, ...] }
```

## Formato do doc de daily (vault)

O time mantém um arquivo por dia em
`vault-docs-projetos/tarefas/VERZEL/GAV/daily/YYYY-MM/DD-MM-YYYY - Daily - <tema>.md`:

```markdown
# Daily - 04/11/2026 — tema do dia

<contexto do dia>

## Itens trabalhados

### `13972` — modo de conexão do banco
- o que foi feito
- testes / commit / estado do card

## Estado da sprint

<números do board e progresso>

## Pendências

- item aberto
```

O Relay guarda o mesmo conteúdo em registros por **seção**:
`INTRO` · `ITEMS` (um por `###`) · `SPRINT` · `PENDING` (um por bullet) · `OTHER`.

### Exportar o dia no formato do vault
```bash
curl -s "http://127.0.0.1:9777/api/projects/2/daily/export?date=2026-11-04" \
  | jq -r '.markdown' > "/tmp/04-11-2026 - Daily - tema.md"
# também devolve .filename e .monthDir prontos para salvar no vault
```

Na UI: aba **Daily** → **⬇ Exportar .md** (web baixa o arquivo; desktop abre o
salvar como).

### Importar um doc existente
```bash
# por conteúdo
curl -s -X POST "http://127.0.0.1:9777/api/projects/2/daily/import" \
  -H 'Content-Type: application/json' \
  -d "{\"content\": $(jq -Rs . < doc.md), \"replace\": true}" | jq

# por caminho (servidor local)
curl -s -X POST "http://127.0.0.1:9777/api/projects/2/daily/import" \
  -H 'Content-Type: application/json' \
  -d '{"path":"/home/wsi/.../04-11-2026 - Daily - tema.md","replace":true}' | jq
```

`replace=true` (padrão) substitui os registros daquele dia — o import é idempotente.

### Importar o histórico inteiro do vault
```bash
python3 local-client/scripts/import_daily_vault.py \
  --dir /home/wsi/repositorios/github/vault-docs-projetos/tarefas/VERZEL/GAV/daily \
  --project-key MIG --dry-run     # confere
# depois sem --dry-run (ou --month 2026-11 para um mês)
```

## Fluxo recomendado para o agente

1. Descobrir o projeto: `GET /api/projects` (ou usar o projeto ativo do workspace).
2. Ler o período pedido com `dateFrom`/`dateTo` (ou `date` para um dia só).
3. Se for **escrever** (criar/editar/excluir): mostrar antes o que será gravado
   (**registro + campo + valor**) e pedir confirmação — a regra de escrita do
   Relay vale também para o daily.
4. Usar `kind` com critério: `WORK` (feito), `BLOCKER` (impedimento),
   `DECISION` (decisão tomada), `NOTE` (observação).
5. Amarrar ao card quando fizer sentido: `taskCode` = `MIG-13973` etc.

## Escrevendo um resumo do período

Para relatório, combine o daily com os cards:

```bash
# 1) registros do período
curl -s "http://127.0.0.1:9777/api/projects/2/daily?dateFrom=2026-11-01&dateTo=2026-11-07" > /tmp/daily.json
# 2) estado atual do board (progresso, por pessoa, por coluna)
curl -s "http://127.0.0.1:9777/api/projects/2/board" > /tmp/board.json
# 3) resumo agregado
curl -s "http://127.0.0.1:9777/api/projects/2/daily/summary?dateFrom=2026-11-01&dateTo=2026-11-07"
```

Monte o texto por dia, separando `WORK` (entregue) de `BLOCKER` (atenção) e
`DECISION` (mudanças de rumo).

## Limites / cuidados

- **Não** confundir com o Azure DevOps nem escrever em plataforma externa: o
  daily é **local**.
- `PATCH`/`DELETE` usam `/api/project-daily/{id}` (não `/api/daily/{id}`, que é
  a nota global do Meu Dia).
- Datas sempre `YYYY-MM-DD`; formato inválido → `400`.
- Sem `project_id` válido → `404`.
