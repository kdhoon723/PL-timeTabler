const CACHE = 'pl-timetabler-v2'
const SHELL = ['/', '/manifest.webmanifest', '/icon.svg', '/data/catalog-2026-1.json', '/data/common-graduation-rules.json', '/data/department-sources-2026.json']

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE)
    await cache.addAll(SHELL)
    // Vite emits content-hashed bundles. Discover them from the built index so
    // a direct offline navigation can boot the SPA, not just return its HTML.
    const index = await fetch('/', { cache: 'no-cache' })
    if (index.ok) {
      const html = await index.clone().text()
      const assets = [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map((match) => match[1])
      await cache.put('/', index)
      await cache.addAll(assets)
    }
    await self.skipWaiting()
  })())
})
self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim()))
})
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  const url = new URL(event.request.url)
  if (url.origin !== self.location.origin) return
  // API responses are live state. In particular, optimization polling must never
  // be frozen at the first QUEUED/RUNNING response by the offline shell cache.
  if (url.pathname.startsWith('/api/')) return
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith((async () => {
      const cached = await caches.match(event.request)
      if (cached) return cached
      const response = await fetch(event.request)
      if (response.ok) await (await caches.open(CACHE)).put(event.request, response.clone())
      return response
    })())
    return
  }
  // Navigations and mutable catalog/requirements data are network-first. This
  // makes every deploy/data refresh visible even when sw.js itself is unchanged,
  // while the precache remains a genuine offline fallback.
  event.respondWith((async () => {
    try {
      const response = await fetch(event.request)
      if (response.ok) await (await caches.open(CACHE)).put(event.request, response.clone())
      return response
    } catch {
      return event.request.mode === 'navigate' ? caches.match('/') : caches.match(event.request)
    }
  })())
})
