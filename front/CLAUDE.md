# Frontend (Angular) — Guia para Agentes de IA

## Visão Geral

Frontend Angular 20 do template fullstack. Trabalha em conjunto com o backend NestJS em `../back`.

**Leia também o `CLAUDE.md` na raiz do monorepo** para a arquitetura completa e as convenções compartilhadas.

---

## Regra Fundamental

**Toda alteração no frontend que envolve dados DEVE estar sincronizada com o backend, e vice-versa.**

Ao alterar um campo, verifique:
1. O model/interface em `src/app/models/` está atualizado?
2. O DTO correspondente no backend aceita/retorna o campo?
3. O service/provider faz a chamada HTTP correta?
4. O template exibe ou permite editar o campo?

---

## Stack

- Angular 20 (standalone components, OnPush change detection)
- Tailwind CSS + Bootstrap 5
- NgRx (state management: auth)
- SweetAlert2 (`Swal.fire()` direto)
- Capacitor (empacotamento PWA / mobile)

## Estrutura

```
src/app/
├── pages/        # auth, home, user, credit, settings, not-found
├── components/   # Componentes reutilizáveis (navbar, mobile-bottom-nav, etc.)
├── services/     # HTTP services
├── models/       # Interfaces TypeScript
├── state/        # NgRx store (auth, roles)
├── routes/       # app.routes.ts
└── modules/      # data-service (base + auth headers) + interceptors (JWT)
```

## Configuração em Runtime

A config é carregada de `public/config.json` antes do bootstrap (não em build). Veja [`CONFIG.md`](CONFIG.md). `apiUrl` default: `http://localhost:5000/api`.

## Convenções

- Standalone components com `ChangeDetectionStrategy.OnPush`
- Tailwind inline no template para estilos utilitários; SCSS apenas para animações/media queries
- UI em português brasileiro
- Sem emojis salvo se pedido
- Primary (verde): `#1DB954`

## Comandos

```bash
npm install --legacy-peer-deps
npm start          # ng serve — http://localhost:4200
npm run build      # ng build
npx tsc --noEmit   # checar tipos
```
