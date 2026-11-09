---
name: gav-azure-sync
description: Sincroniza manualmente o board do Azure DevOps para o Relay local — somente leitura no Azure, escrita só local. Use quando o usuário pedir "sincronizar board", "importar do Azure", "trazer tasks do Azure para o Relay" ou "atualizar board local com o Azure".
---

# GAV — Sincronização Azure → Relay (somente leitura no Azure)

Sincroniza **manualmente** o board **"VAR 3.0 - Migração GX"** (org `GrupoAvenida`) para o Relay local. **Nunca escreve no Azure** — só lê via `az boards query/show` e escreve/atualiza no SQLite local (`Task`, `BoardColumn`, `Member`, `Label`, `Epic`).

> Escrita no Azure exige autorização explícita (card + ação + valor). Esta skill é **somente leitura no Azure**.

## Quando usar
- "sincronizar board" / "importar do Azure" / "trazer tasks do Azure"
- "atualizar o Relay com o Azure" / "espelhar o Azure localmente"

## Regras
1. **`--project` explícito** em todo `az` (default `VAR 3.0 - Migração GX`).
2. **`2>arquivo.err`** separado — o `WARNING` do auto-detect quebra o JSON se misturar.
3. **Idempotente**: `code = GAVAR-<id>`; re-rodar não duplica, só atualiza `column_id`, `assignee`, `tags`.
4. **Colunas**: mapeia `System.State` → coluna local de mesmo nome (cria se faltar, respeitando o modelo 12 raias).
5. **Nunca** `az boards work-item create/update/delete` nesta skill.

## Passo 1 — Ler do Azure (somente leitura)
```bash
ORG=https://dev.azure.com/GrupoAvenida; PROJ="VAR 3.0 - Migração GX"
az boards query --project "$PROJ" --organization $ORG \
  --wiql "SELECT [System.Id],[System.Title],[System.State],[System.AssignedTo],[System.Tags],[System.CreatedDate],[System.ChangedDate] FROM WorkItems WHERE [System.TeamProject]='$PROJ' ORDER BY [System.ChangedDate] DESC" \
  -o json > /tmp/azure.json 2>/tmp/azure.err
python3 -c "import json; d=json.load(open('/tmp/azure.json')); print(f'total {len(d)}'); print([(x['id'], x['fields'].get('System.State'), x['fields'].get('System.Title')[:50]) for x in d[:3]])"
```

## Passo 2 — Sincronizar para o Relay local
```bash
# helper local (cria/atualiza Task por GAVAR-<id>, mapeia estado→coluna, cria Member/Label/Epic se preciso)
python3 local-client/scripts/sync_azure_to_local.py \
  --project "VAR 3.0 - Migração GX" --local-project-key GAVAR \
  --input /tmp/azure.json --dry-run   # sem --dry-run aplica
```

## Passo 3 — Conferir
```bash
# no Relay local
python3 -c "from relay.db.models import Task, get_session; s=get_session(); print(s.query(Task).filter(Task.code.like('GAVAR-%')).count())"
```

## Observações
- Estados Azure: To do, Approved, Refinement, Ready for Dev, Doing, Dev Box, Dev Review, In Test, Rework, Verified, Accepted, Done (12 raias do template).
- `is_done` = apenas `Done`; `is_conclusion` no Azure = `Done`.
- `AssignedTo.displayName` → `Member` + `Task.assignee` (cria Member com cor livre).
- `System.Tags` (ex.: "cliente; sprint-1") → `Label`/`Epic` conforme sufixo.
