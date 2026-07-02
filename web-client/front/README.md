> 🇧🇷 [Versão em português](README.ptbr.md)

# Frontend — Angular 20

Web application (SPA + PWA) of the fullstack template. Consumes the NestJS API in `../back`.

## Stack

- Angular 20 (standalone components)
- Tailwind CSS + Bootstrap 5
- NgRx (state management)
- SweetAlert2
- Capacitor (PWA / mobile)

## Development

```bash
npm install --legacy-peer-deps
cp public/config.example.json public/config.json   # adjust apiUrl if needed
npm start                                           # http://localhost:4200
```

> `--legacy-peer-deps` is required due to peer-dependency conflicts in the Angular 20 toolchain.

## Build

```bash
npm run build      # output in dist/fullstack-template-front/browser
```

## Configuration

The application loads `public/config.json` at runtime (no rebuild). See [`CONFIG.md`](CONFIG.md) for details.

## Documentation for agents

See [`CLAUDE.md`](CLAUDE.md) and the `CLAUDE.md` at the monorepo root.

## License

MIT
