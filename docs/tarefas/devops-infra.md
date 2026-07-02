> 🇧🇷 [Versão em português](devops-infra.ptbr.md)

# Tasks — Infra / DevOps

Base: the template already ships a `docker-compose.yml` (MySQL, Redis, API, front ends),
a multi-stage `Dockerfile`, `docker-entrypoint.sh` (migrations + seed) and Nginx.
Here it is only about **adapting** it for Maestro. Effort in man-days (md).

---

## D1 — Lean compose for Maestro · 1 md
- [ ] Remove the `front-react` and `front-flutter` services from the compose file
- [ ] Keep: `mysql`, `redis`, `api`, `front` (Angular)
- [ ] Check ports and service names; healthchecks ok

## D2 — Environment variables · 0.5 md
- [ ] Review `back/.env.example`: `DATABASE_URL`, `JWT_*`, `REDIS_*`
- [ ] Add Maestro secrets: API key prefix, webhook secret (HMAC)
- [ ] Document each variable in `.env.example`

## D3 — Automatic migrations + seed · 0.5 md
- [ ] Validate `docker-entrypoint.sh` running `prisma migrate deploy` + seed
- [ ] Idempotent seed (does not duplicate the demo company/user on reruns)

## D4 — CI (lint, test, build) · 1.5 md
- [ ] Pipeline: install deps, `lint`, `test` (back and front), `build`
- [ ] Run multi-tenant isolation tests in CI
- [ ] Dependency caching to speed things up

## D5 — Image build and deploy · 1.5 md
- [ ] Multi-stage build of the API and the front end (Nginx serving the Angular app)
- [ ] Migration strategy on deploy (run before bringing up the new API)
- [ ] Variables/secrets in the target environment (do not commit `.env`)

## D6 — Basic observability · 1 md
- [ ] Health check exposed (already in the template) + DB/Redis readiness
- [ ] Structured logs; correlation by request id
- [ ] (Optional) Bull queue metrics

---

## Diagrams (maintenance)

- [ ] `docs/diagramas/gerar.sh` runs locally with Java + Graphviz
- [ ] (Optional) CI job that regenerates the SVGs and fails if there is a `.puml` without an updated `.svg`

## Quality checklist (infra)

- [ ] `docker compose up` brings everything up from scratch with migrations + seed
- [ ] `.env` never committed; `.env.example` complete
- [ ] Green CI (lint + test + build) required for merge
- [ ] Reproducible deploy with a planned migration rollback
