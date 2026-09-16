const CACHE_NAME = 'freqtrader-cache-v2';

const URLS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './icon-152.png',
  './icon-167.png',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png',
  'https://fonts.googleapis.com/css2?family=Geist:wght@300..700&family=Geist+Mono:wght@400;500;600&display=swap'
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return Promise.allSettled(URLS_TO_CACHE.map(url => {
          return fetch(url).then(response => {
            if (!response.ok) throw new TypeError('bad response status');
            return cache.put(url, response);
          });
        }));
      })
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Stale-while-revalidate for CDN scripts and local files
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  // Ignore API requests
  if (event.request.url.includes('/api/v1/')) return;
  // Ignore socket/websockets
  if (event.request.url.startsWith('ws')) return;
  
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      const fetchPromise = fetch(event.request).then(networkResponse => {
        // Cache successful responses for our domain or CDN
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(err => {
        return cachedResponse;
      });

      return cachedResponse || fetchPromise;
    })
  );
});
