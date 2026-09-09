const CACHE = 'baranda-shell-v4';
const ASSETS = ['/static/offline.html', '/static/offline.js', '/static/app.css', '/static/theme.css', '/static/fonts/InterVariable.woff2',
  '/static/icons/icon.svg', '/static/icons/icon-192.png', '/static/icons/icon-512.png',
  '/static/icons/maskable-512.png', '/static/manifest.webmanifest'];
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key.startsWith('baranda-shell-') && key !== CACHE).map((key) => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('/static/offline.html')));
    return;
  }
  if (ASSETS.includes(url.pathname)) {
    event.respondWith(fetch(event.request).then((response) => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then((cache) => cache.put(event.request, copy)));
      }
      return response;
    }).catch(() => caches.match(event.request)));
  }
});
