# Frontend — Angular 20

Aplicação web (SPA + PWA) do template fullstack. Consome a API NestJS em `../back`.

## Stack

- Angular 20 (standalone components)
- Tailwind CSS + Bootstrap 5
- NgRx (state management)
- SweetAlert2
- Capacitor (PWA / mobile)

## Desenvolvimento

```bash
npm install --legacy-peer-deps
cp public/config.example.json public/config.json   # ajuste apiUrl se necessário
npm start                                           # http://localhost:4200
```

> `--legacy-peer-deps` é necessário por conflitos de peer-deps no toolchain do Angular 20.

## Build

```bash
npm run build      # saída em dist/fullstack-template-front/browser
```

## Configuração

A aplicação carrega `public/config.json` em runtime (sem rebuild). Veja [`CONFIG.md`](CONFIG.md) para detalhes.

## Documentação para agentes

Veja [`CLAUDE.md`](CLAUDE.md) e o `CLAUDE.md` na raiz do monorepo.

## Licença

MIT
