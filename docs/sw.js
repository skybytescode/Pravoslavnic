// Pravoslavnic service worker
// 1) Caches site assets so the player works offline after the first load.
// 2) Handles clicks on notifications scheduled via Notification Triggers
//    (TimestampTrigger) by focusing the player or opening it.
//
// Bump CACHE_VERSION whenever asset URLs change so old caches are evicted.

const CACHE_VERSION = "v5b2470e9a1";
const CACHE = "pravoslavnic-" + CACHE_VERSION;

const ASSETS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./css/styles.css",
  "./css/chi-rho.png",
  "./js/schedule.js",
  "./js/player.js",
  "./content/01-miezonoptica.html",
  "./content/02-utrenia.html",
  "./content/03-ceasul-1.html",
  "./content/04-mijloceasul-1.html",
  "./content/05-ceasul-3.html",
  "./content/06-mijloceasul-3.html",
  "./content/07-ceasul-6.html",
  "./content/08-mijloceasul-6.html",
  "./content/09-ceasul-9.html",
  "./content/10-mijloceasul-9.html",
  "./content/11-vecernia.html",
  "./content/12-pavecernita.html",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => k.startsWith("pravoslavnic-") && k !== CACHE).map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Cross-origin (fonts.googleapis, fonts.gstatic) — let the browser handle it.
  if (url.origin !== self.location.origin) return;
  event.respondWith(
    caches.match(req).then((cached) => cached || fetch(req).then((res) => {
      // Opportunistically warm the cache for new pages we hadn't pre-listed.
      const copy = res.clone();
      caches.open(CACHE).then((cache) => cache.put(req, copy)).catch(() => {});
      return res;
    }).catch(() => cached))
  );
});

// When the user clicks a scheduled notification, focus an existing player
// window or open a new one rooted at the site's start URL.
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    (async () => {
      const all = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      const ours = all.find((c) => c.url.includes(self.location.origin));
      if (ours) {
        await ours.focus();
      } else {
        await self.clients.openWindow("./");
      }
    })()
  );
});
