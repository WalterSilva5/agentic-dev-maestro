> 🇧🇷 [Versão em português](CONFIG.ptbr.md)

# Environment Configuration

This project uses a configuration system based on a JSON file loaded at runtime, instead of TypeScript environment files. This approach lets you update configuration without needing to rebuild the application.

## Structure

- **`public/config.json`**: Configuration file that will be loaded by the application
- **`public/config.example.json`**: Configuration example (versioned in Git)
- **`src/app/services/config.service.ts`**: Service that loads and manages the configuration
- **`src/app/config/config.initializer.ts`**: Initializer that loads the configuration before bootstrap
- **`src/app/models/app-config.interface.ts`**: TypeScript interface for the configuration

## How It Works

1. Before the application starts, the `ConfigService` loads the `/config.json` file
2. The configuration becomes available throughout the application via dependency injection
3. At deploy time, just replace the `config.json` file with the values for the correct environment

## Local Configuration

1. Copy the example file:
```bash
cp public/config.example.json public/config.json
```

2. Edit `public/config.json` with the local configuration:
```json
{
  "apiUrl": "http://localhost:5000/api",
  "production": false
}
```

## Deploy

### Development
```json
{
  "apiUrl": "http://192.168.1.6:5000/api",
  "production": false
}
```

### Production
```json
{
  "apiUrl": "https://api.wsisys.com.br/api",
  "production": true
}
```

### How to Apply on Deploy

**Option 1: Replace the file after build**
```bash
# Build the application
npm run build

# Replace config.json in the dist folder
cp config.production.json dist/fullstack-template-front/browser/config.json
```

**Option 2: Docker volume**
```dockerfile
# In docker-compose.yml
volumes:
  - ./config.production.json:/app/config.json
```

**Option 3: Deploy script**
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

## Using the Configuration in Code

### Inject the service:
```typescript
import { ConfigService } from './services/config.service';

constructor(private configService: ConfigService) {
  const apiUrl = this.configService.apiUrl;
  const isProduction = this.configService.isProduction;
}
```

### Get the complete configuration:
```typescript
const config = this.configService.getConfig();
console.log(config.apiUrl);
```

## Migrating Old Code

### Before (using environment):
```typescript
import { environment } from '../environments/environment';

apiUrl = environment.apiUrl;
```

### After (using ConfigService):
```typescript
import { ConfigService } from './services/config.service';

constructor(private configService: ConfigService) {
  this.apiUrl = this.configService.apiUrl;
}
```

## Advantages

✅ **No rebuild**: Change configuration without recompiling  
✅ **Simplicity**: Only one JSON file to edit  
✅ **Flexibility**: Easy integration with CI/CD  
✅ **Security**: The file is not versioned (added to .gitignore)  
✅ **Runtime**: Configuration loaded dynamically  

## Old Files (Deprecated)

The following files can be removed after the full migration:
- `src/environments/environment.ts`
- `src/environments/environment.dev.ts`
- `src/environments/environment.local.ts`
- `src/environments/environment.prod.ts`
- `src/environments/environment.hml.ts` (if it exists)

You can also remove the `fileReplacements` sections from `angular.json`.
