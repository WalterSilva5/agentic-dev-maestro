> 🇬🇧 [English version](devops-infra.md)

# Tarefas — Infra / DevOps

Base: o template já traz `docker-compose.yml` (MySQL, Redis, API, fronts),
`Dockerfile` multi-stage, `docker-entrypoint.sh` (migrations + seed) e Nginx.
Aqui é só **adaptar** para o Maestro. Esforço em homem-dia (hd).

---

## D1 — Compose enxuto para o Maestro · 1 hd
- [ ] Remover serviços `front-react` e `front-flutter` do compose
- [ ] Manter: `mysql`, `redis`, `api`, `front` (Angular)
- [ ] Conferir portas e nomes de serviço; healthchecks ok

## D2 — Variáveis de ambiente · 0.5 hd
- [ ] Revisar `back/.env.example`: `DATABASE_URL`, `JWT_*`, `REDIS_*`
- [ ] Adicionar segredos do Maestro: prefixo de API key, secret de webhook (HMAC)
- [ ] Documentar cada variável no `.env.example`

## D3 — Migrations + seed automáticos · 0.5 hd
- [ ] Validar `docker-entrypoint.sh` rodando `prisma migrate deploy` + seed
- [ ] Seed idempotente (não duplica empresa/usuário demo em reexecuções)

## D4 — CI (lint, test, build) · 1.5 hd
- [ ] Pipeline: instalar deps, `lint`, `test` (back e front), `build`
- [ ] Rodar testes de isolamento multi-tenant no CI
- [ ] Cache de dependências para acelerar

## D5 — Build de imagens e deploy · 1.5 hd
- [ ] Build multi-stage da API e do front (Nginx servindo o Angular)
- [ ] Estratégia de migrations no deploy (rodar antes de subir a nova API)
- [ ] Variáveis/segredos no ambiente de destino (não commitar `.env`)

## D6 — Observabilidade básica · 1 hd
- [ ] Health check exposto (já no template) + readiness do DB/Redis
- [ ] Logs estruturados; correlação por request id
- [ ] (Opcional) métricas de fila Bull

---

## Diagramas (manutenção)

- [ ] `docs/diagramas/gerar.sh` roda local com Java + Graphviz
- [ ] (Opcional) job de CI que regenera os SVGs e falha se houver `.puml` sem `.svg` atualizado

## Checklist de qualidade (infra)

- [ ] `docker compose up` sobe tudo do zero com migrations + seed
- [ ] `.env` nunca commitado; `.env.example` completo
- [ ] CI verde (lint + test + build) obrigatório para merge
- [ ] Deploy reprodutível e com rollback de migration pensado
