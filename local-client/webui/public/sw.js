// Service worker do Maestro web (PWA). Cacheia o app shell; nunca a API.
const CACHE = 'maestro-v1'
const SHELL = ['/', '/index.html', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png']

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}))
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  // A API sempre pela rede (dados dinâmicos, mesmo servidor local).
  if (url.pathname.startsWith('/api')) return
  if (e.request.method !== 'GET') return

  // Network-first com fallback ao cache (funciona offline para o shell).
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone()
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {})
        return res
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match('/'))),
  )
})
