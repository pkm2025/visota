/* PMKetoan Service Worker — offline caching + background sync.
 *
 * Strategies:
 *  - Static assets (CSS/JS/images): cache-first with network fallback
 *  - HTML pages: network-first with cache fallback (offline reads last version)
 *  - API/POST: network-only (never cache writes)
 */

const CACHE_VERSION = "pmketoan-v4";
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGE_CACHE = `${CACHE_VERSION}-pages`;
const OFFLINE_URL = "/offline/";

const STATIC_ASSETS = [
  "/static/icons/logo.svg",
  "/static/icons/icon-192.svg",
  "/static/icons/icon-512.svg",
  "/static/vendor/js/dexie.min.js",
  "/static/modern/js/pkm-cache.js",
  "/offline/",
];

// Install: pre-cache critical assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => !k.startsWith(CACHE_VERSION))
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch: route by request type
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Skip non-GET (POST/PUT/DELETE — never cache)
  if (request.method !== "GET") return;

  // Skip cross-origin
  const url = new URL(request.url);
  if (url.origin !== location.origin) return;

  // Skip Django admin + debug
  if (url.pathname.startsWith("/admin/") || url.pathname.startsWith("/__debug__/")) {
    return;
  }

  // Static assets (CSS/JS/images): cache-first
  if (
    url.pathname.startsWith("/static/") ||
    url.pathname.match(/\.(css|js|svg|png|jpg|jpeg|gif|woff2?)$/i)
  ) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // HTML pages: network-first with cache fallback
  if (request.headers.get("accept")?.includes("text/html")) {
    event.respondWith(networkFirst(request));
    return;
  }

  // XHR/fetch JSON: try network, fallback to cache if exists
  if (request.headers.get("accept")?.includes("application/json")) {
    event.respondWith(networkFirst(request));
    return;
  }
});

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    // Refresh in background
    fetch(request).then((resp) => cache.put(request, resp.clone())).catch(() => {});
    return cached;
  }
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    return cached || new Response("Offline", { status: 503 });
  }
}

async function networkFirst(request) {
  const cache = await caches.open(PAGE_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok && response.headers.get("content-type")?.includes("text/html")) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    // Fall back to offline page
    const offline = await cache.match(OFFLINE_URL);
    return offline || new Response("Offline — please reconnect", { status: 503 });
  }
}

// Listen for messages from client (skipWaiting etc)
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

// Push notifications (planned for v2)
self.addEventListener("push", (event) => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title || "PMKetoan", {
      body: data.body || "",
      icon: "/static/icons/icon-192.svg",
      badge: "/static/icons/icon-192.svg",
      data: { url: data.url || "/modern/" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/modern/";
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((clientList) => {
      const existing = clientList.find((c) => c.url.includes(url));
      if (existing) return existing.focus();
      return clients.openWindow(url);
    })
  );
});
