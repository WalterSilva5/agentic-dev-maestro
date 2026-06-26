// Service Worker do PWA
// IMPORTANTE: Incrementar versão a cada deploy para forçar atualização
const CACHE_VERSION = '2';
const CACHE_NAME = `app-cache-v${CACHE_VERSION}`;
const OFFLINE_URL = '/';

// Arquivos essenciais para cache
const STATIC_CACHE_URLS = [
  '/',
  '/index.html',
  '/favicon.ico',
  '/manifest.json'
];

// Instalação do Service Worker - FORÇA ATUALIZAÇÃO IMEDIATA
self.addEventListener('install', (event) => {
  console.log(`[SW v${CACHE_VERSION}] Instalando...`);
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Cache aberto');
        return cache.addAll(STATIC_CACHE_URLS.map(url => new Request(url, { cache: 'reload' })));
      })
      .then(() => {
        console.log('[SW] skipWaiting - forçando ativação imediata');
        return self.skipWaiting();
      })
  );
});

// Ativação do Service Worker - LIMPA TODOS OS CACHES ANTIGOS
self.addEventListener('activate', (event) => {
  console.log(`[SW v${CACHE_VERSION}] Ativando...`);
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Remove QUALQUER cache que não seja o atual
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Removendo cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Assumindo controle de todos os clientes');
      return self.clients.claim();
    }).then(() => {
      // Notifica todos os clientes sobre a atualização
      return self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({
            type: 'SW_UPDATED',
            version: CACHE_VERSION
          });
        });
      });
    })
  );
});

// Estratégia de cache: Network First (sempre busca da rede primeiro)
self.addEventListener('fetch', (event) => {
  // Ignorar requisições que não sejam GET
  if (event.request.method !== 'GET') return;

  // Ignorar requisições externas (APIs, etc)
  if (!event.request.url.startsWith(self.location.origin)) return;

  // Ignorar requisições de API
  if (event.request.url.includes('/api/')) return;

  // Nunca cachear a config de runtime (porta/URL da API por ambiente)
  if (event.request.url.includes('/config.json')) return;

  event.respondWith(
    fetch(event.request, { cache: 'no-store' })
      .then((response) => {
        // Se a resposta for válida, clonar e adicionar ao cache
        if (response && response.status === 200) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // Se falhar, tentar buscar do cache
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Se não houver cache, retornar página offline para navegação
          if (event.request.mode === 'navigate') {
            return caches.match(OFFLINE_URL);
          }
        });
      })
  );
});

// Mensagens do cliente
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  // Força limpeza completa do cache
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => caches.delete(cacheName))
      );
    }).then(() => {
      event.source.postMessage({ type: 'CACHE_CLEARED' });
    });
  }
});
