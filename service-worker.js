/* Tirumala Live Info offline cache + Firebase Cloud Messaging worker. */
importScripts('./app-config.js');

const CACHE = 'tirumala-live-info-v6';
const FILES = [
  './', './index.html', './manifest.webmanifest', './app-config.js',
  './data/live.json', './assets/app-icon.png', './assets/full-logo.png',
  './assets/icon-192.png', './assets/icon-512.png', './assets/apple-touch-icon.png',
  './assets/favicon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))));
  self.clients.claim();
});

// Avoid serving stale app config or live JSON from the cache.
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.endsWith('/app-config.js') || url.pathname.endsWith('/data/live.json')) {
    event.respondWith(fetch(event.request, { cache: 'no-store' }).catch(() => caches.match(event.request)));
    return;
  }
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    if (response && response.ok) {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(event.request, copy));
    }
    return response;
  }).catch(() => caches.match('./index.html'))));
});

// Firebase is loaded only after the app's public Firebase config has been filled in.
const cfg = self.TLI_CONFIG || {};
const firebaseReady = cfg.firebase && cfg.firebase.apiKey && cfg.firebase.projectId && cfg.firebase.messagingSenderId && cfg.firebase.appId;
if (firebaseReady) {
  try {
    importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
    importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');
    firebase.initializeApp(cfg.firebase);
    const messaging = firebase.messaging();
    messaging.onBackgroundMessage(payload => {
      const notification = payload.notification || {};
      self.registration.showNotification(notification.title || 'Tirumala Live Info', {
        body: notification.body || 'There is a new Tirumala update.',
        icon: './assets/icon-192.png',
        badge: './assets/icon-192.png',
        data: { url: (payload.fcmOptions && payload.fcmOptions.link) || './index.html' }
      });
    });
  } catch (error) {
    // Keep offline caching available even if the remote Firebase SDK is temporarily unavailable.
  }
}

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const raw = (event.notification.data && event.notification.data.url) || './index.html';
  const target = new URL(raw, self.location.origin).href;
  event.waitUntil((async () => {
    const open = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of open) {
      if ('focus' in client) {
        await client.focus();
        if ('navigate' in client) await client.navigate(target);
        return;
      }
    }
    if (self.clients.openWindow) await self.clients.openWindow(target);
  })());
});
