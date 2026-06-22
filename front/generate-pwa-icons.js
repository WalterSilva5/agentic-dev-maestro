// Este é um script para gerar ícones PWA de diferentes tamanhos
// Execute com: node generate-pwa-icons.js

const fs = require('fs');
const path = require('path');

console.log(`
📱 GUIA PARA CRIAR ÍCONES PWA
=============================

Para criar os ícones do PWA, você tem duas opções:

OPÇÃO 1 - Usar ferramenta online (Recomendado):
1. Acesse: https://www.pwabuilder.com/imageGenerator
2. Faça upload de um logo/ícone quadrado (mínimo 512x512px)
3. Baixe o pacote de ícones gerado
4. Copie os ícones para: public/icons/

OPÇÃO 2 - Criar manualmente:
Crie imagens PNG nos seguintes tamanhos:
- icon-72x72.png
- icon-96x96.png
- icon-128x128.png
- icon-144x144.png
- icon-152x152.png
- icon-192x192.png
- icon-384x384.png
- icon-512x512.png

DICAS:
- Use fundo sólido (#1DB954 - verde do tema)
- Logo/ícone centralizado e legível
- Formato PNG com transparência ou fundo sólido
- Para "maskable" icons, deixe 10% de margem de segurança

ÍCONE RECOMENDADO:
- Um haltere ou símbolo de fitness
- Cores: Verde (#1DB954) e/ou Roxo (#6A0DAD)
- Estilo: Minimalista, moderno
`);

// Criar diretório se não existir
const iconsDir = path.join(__dirname, '../public/icons');
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
  console.log('✅ Diretório public/icons/ criado!');
} else {
  console.log('ℹ️  Diretório public/icons/ já existe');
}

console.log('\n📦 Após criar os ícones, seu PWA estará pronto para instalação!');
