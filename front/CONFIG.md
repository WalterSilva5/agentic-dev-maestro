# Configuração de Ambiente

Este projeto utiliza um sistema de configuração baseado em arquivo JSON carregado em runtime, ao invés de arquivos de environment TypeScript. Esta abordagem permite atualizar configurações sem precisar fazer rebuild da aplicação.

## Estrutura

- **`public/config.json`**: Arquivo de configuração que será carregado pela aplicação
- **`public/config.example.json`**: Exemplo de configuração (versionado no Git)
- **`src/app/services/config.service.ts`**: Serviço que carrega e gerencia as configurações
- **`src/app/config/config.initializer.ts`**: Inicializador que carrega as configurações antes do bootstrap
- **`src/app/models/app-config.interface.ts`**: Interface TypeScript para as configurações

## Como Funciona

1. Antes da aplicação iniciar, o `ConfigService` carrega o arquivo `/config.json`
2. As configurações ficam disponíveis em toda a aplicação via injeção de dependência
3. No deploy, basta substituir o arquivo `config.json` com os valores do ambiente correto

## Configuração Local

1. Copie o arquivo de exemplo:
```bash
cp public/config.example.json public/config.json
```

2. Edite `public/config.json` com as configurações locais:
```json
{
  "apiUrl": "http://localhost:5000/api",
  "production": false
}
```

## Deploy

### Desenvolvimento
```json
{
  "apiUrl": "http://192.168.1.6:5000/api",
  "production": false
}
```

### Produção
```json
{
  "apiUrl": "https://api.wsisys.com.br/api",
  "production": true
}
```

### Como Aplicar no Deploy

**Opção 1: Substituir arquivo após build**
```bash
# Build da aplicação
npm run build

# Substituir config.json na pasta dist
cp config.production.json dist/fullstack-template-front/browser/config.json
```

**Opção 2: Volume no Docker**
```dockerfile
# No docker-compose.yml
volumes:
  - ./config.production.json:/app/config.json
```

**Opção 3: Script de deploy**
```bash
#!/bin/bash
npm run build
cd dist/fullstack-template-front/browser
cat > config.json << EOF
{
  "apiUrl": "$API_URL",
  "production": true
}
EOF
```

## Usando as Configurações no Código

### Injetar o serviço:
```typescript
import { ConfigService } from './services/config.service';

constructor(private configService: ConfigService) {
  const apiUrl = this.configService.apiUrl;
  const isProduction = this.configService.isProduction;
}
```

### Obter configuração completa:
```typescript
const config = this.configService.getConfig();
console.log(config.apiUrl);
```

## Migrando Código Antigo

### Antes (usando environment):
```typescript
import { environment } from '../environments/environment';

apiUrl = environment.apiUrl;
```

### Depois (usando ConfigService):
```typescript
import { ConfigService } from './services/config.service';

constructor(private configService: ConfigService) {
  this.apiUrl = this.configService.apiUrl;
}
```

## Vantagens

✅ **Sem rebuild**: Altere configurações sem recompilar  
✅ **Simplicidade**: Apenas um arquivo JSON para editar  
✅ **Flexibilidade**: Fácil integração com CI/CD  
✅ **Segurança**: Arquivo não é versionado (adicionado ao .gitignore)  
✅ **Runtime**: Configurações carregadas dinamicamente  

## Arquivos Antigos (Deprecados)

Os seguintes arquivos podem ser removidos após a migração completa:
- `src/environments/environment.ts`
- `src/environments/environment.dev.ts`
- `src/environments/environment.local.ts`
- `src/environments/environment.prod.ts`
- `src/environments/environment.hml.ts` (se existir)

Também pode remover as seções `fileReplacements` do `angular.json`.
