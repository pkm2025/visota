/* PMKetoan Service Worker — offline caching + background sync.
 *
 * Strategies:
 *  - Static assets (CSS/JS/images): cache-first with network fallback
 *  - PKM pages (/modern/knowledge/*): stale-while-revalidate (offline reads)
 *  - Other HTML pages: network-first with cache fallback
 *  - API/POST: network-only (POST to notes queued via Background Sync)
 *  - Background Sync: drafts queued offline are replayed when online
 */

const CACHE_VERSION = "pmketoan-v5";
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGE_CACHE = `${CACHE_VERSION}-pages`;
const PKM_PAGE_CACHE = `${CACHE_VERSION}-pkm-pages`;
const OFFLINE_URL = "/offline/";

/* Routes considered PKM pages (stale-while-revalidate, offline-friendly). */
const PKM_ROUTE_PREFIX = "/modern/knowledge/";

const STATIC_ASSETS = [
  "/static/icons/logo.svg",
  "/static/icons/icon-192.svg",
  "/static/icons/icon-512.svg",
  "/static/vendor/js/dexie.min.js",
  "/static/modern/js/pkm-cache.js",
  "/offline/",
];

/* PKM pages to pre-cache on install so they work immediately offline.
   These are the key navigation routes; detail pages are cached on
   first visit via the stale-while-revalidate strategy. */
const PKM_PRECACHE_PAGES = [
  "/modern/knowledge/",
  "/modern/knowledge/notes/",
  "/modern/knowledge/qa/",
  "/modern/knowledge/settings/",
];

// Install: pre-cache critical assets (ignore individual failures so one
// missing route doesn't prevent the SW from installing).
self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const staticCache = await caches.open(STATIC_CACHE);
      await Promise.all(
        STATIC_ASSETS.map((url) =>
          staticCache.add(new Request(url, { cache: "reload" })).catch(() => {})
        )
      );
      const pageCache = await caches.open(PKM_PAGE_CACHE);
      await Promise.all(
        PKM_PRECACHE_PAGES.map((url) =>
          pageCache.add(new Request(url, { cache: "reload" })).catch(() => {})
        )
      );
    })()
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
  const url = new URL(request.url);

  // Skip cross-origin
  if (url.origin !== location.origin) return;

  // Skip Django admin + debug
  if (url.pathname.startsWith("/admin/") || url.pathname.startsWith("/__debug__/")) {
    return;
  }

  // POST/PUT/DELETE to PKM notes API: queue for background sync if offline
  if (request.method !== "GET") {
    if (
      url.pathname.startsWith("/api/v1/pkm/notes") &&
      (request.method === "POST" || request.method === "PUT")
    ) {
      event.respondWith(queueDraftRequest(request));
    }
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

  // PKM pages: stale-while-revalidate (fast offline reads, background refresh)
  if (
    url.pathname.startsWith(PKM_ROUTE_PREFIX) &&
    request.headers.get("accept")?.includes("text/html")
  ) {
    event.respondWith(staleWhileRevalidate(event, request, PKM_PAGE_CACHE));
    return;
  }

  // Other HTML pages: network-first with cache fallback
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

/**
 * Stale-while-revalidate: return cached immediately (if available), then
 * fetch a fresh copy in the background to update the cache. On network
 * failure the cached version is returned. If nothing is cached and the
 * network fails, fall back to the offline page.
 */
async function staleWhileRevalidate(event, request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((response) => {
      if (
        response.ok &&
        response.headers.get("content-type")?.includes("text/html")
      ) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);

  // Return cached version immediately if available
  if (cached) {
    // Ensure background revalidation runs (kept alive by event.waitUntil)
    event.waitUntil(fetchPromise);
    return cached;
  }

  // No cache — wait for network
  const networkResponse = await fetchPromise;
  if (networkResponse) return networkResponse;

  // Network failed and nothing cached: offline fallback
  const offline = await cache.match(OFFLINE_URL);
  return (
    offline ||
    (await caches.match(OFFLINE_URL)) ||
    new Response("Offline — please reconnect", { status: 503 })
  );
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

// --- Background Sync: queue offline draft POSTs and replay when online -------

const SYNC_TAG = "pkm-draft-sync";
const QUEUE_DB = "pkm_sync_queue";
const QUEUE_STORE = "outbox";

/** Open (or create) the IndexedDB outbox for queued requests. */
function openSyncQueue() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(QUEUE_DB, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        db.createObjectStore(QUEUE_STORE, {
          keyPath: "id",
          autoIncrement: true,
        });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/** Store a failed (offline) request in the outbox and register for sync. */
async function queueDraftRequest(request) {
  try {
    const body = await request.clone().text();
    const headers = {};
    request.headers.forEach((value, key) => {
      headers[key] = value;
    });
    const db = await openSyncQueue();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(QUEUE_STORE, "readwrite");
      tx.objectStore(QUEUE_STORE).add({
        url: request.url,
        method: request.method,
        headers: headers,
        body: body,
        timestamp: Date.now(),
      });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();

    // Register for background sync if supported
    if ("sync" in self.registration) {
      await self.registration.sync.register(SYNC_TAG);
    }

    // Notify the client that the request was queued
    broadcast({ type: "pkm:sync-queued", url: request.url });

    return new Response(
      JSON.stringify({ queued: true, message: "Saved offline; will sync when online." }),
      {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ queued: false, error: String(err) }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

/** Replay all queued requests (called on 'sync' event). */
async function replayQueue() {
  const db = await openSyncQueue();
  const allReq = await new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, "readonly");
    const req = tx.objectStore(QUEUE_STORE).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });

  for (const item of allReq) {
    try {
      const headers = new Headers();
      Object.entries(item.headers || {}).forEach(([k, v]) => headers.set(k, v));
      const resp = await fetch(item.url, {
        method: item.method,
        headers: headers,
        body: item.body,
        credentials: "include",
      });
      if (resp.ok) {
        // Remove successfully replayed request
        await new Promise((resolve, reject) => {
          const tx = db.transaction(QUEUE_STORE, "readwrite");
          tx.objectStore(QUEUE_STORE).delete(item.id);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        });
        broadcast({ type: "pkm:sync-replayed", url: item.url });
      } else {
        // Non-2xx: keep in queue for next sync attempt
        broadcast({ type: "pkm:sync-failed", url: item.url, status: resp.status });
      }
    } catch (err) {
      // Network still down or error — keep in queue
      broadcast({ type: "pkm:sync-error", url: item.url, error: String(err) });
    }
  }
  db.close();
}

/** Send a message to all controlled clients. */
function broadcast(message) {
  self.clients.matchAll({ includeUncontrolled: true }).then((clientList) => {
    clientList.forEach((client) => client.postMessage(message));
  });
}

// Background Sync event: replay queued draft POSTs when connectivity returns
self.addEventListener("sync", (event) => {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(replayQueue());
  }
});

// Listen for messages from client (skipWaiting, manual sync trigger, etc)
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
  if (event.data === "PKM_SYNC_NOW") {
    event.waitUntil(replayQueue());
  }
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
