/**
 * RoadSoS Service Worker — Offline-first caching strategy.
 *
 * Caches:
 * - App shell (CACHE_NAME): all static assets
 * - API responses (API_CACHE): /api/v1/services/nearby — cache-first, 1hr TTL
 * - Protocol bundle (PROTOCOL_CACHE): /v1/protocols/offline-bundle — precached at install
 * - Incident dispatch responses: cache-first for resilience
 */

const CACHE_NAME = "roadsos-v2";
const PROTOCOL_CACHE = "roadsos-protocols-v2";
const API_CACHE = "roadsos-api-v2";

const ASSETS_TO_CACHE = [
  "/",
  "/manifest.json",
  "/icon-192.svg",
  "/app/ar/page",
  "/app/admin/page",
];

const API_CACHE_PATTERNS = [
  "/v1/services/nearby",
  "/v1/services/",
  "/v1/admin/heatmap",
  "/v1/admin/stats",
];

const PROTOCOL_PATTERNS = [
  "/v1/protocols/offline-bundle",
];

// ─── Install: Precache app shell + offline bundle ──────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      await cache.addAll(ASSETS_TO_CACHE);

      // Precache the offline protocol bundle (EN)
      try {
        const protoCache = await caches.open(PROTOCOL_CACHE);
        const bundleResp = await fetch("/v1/protocols/offline-bundle?lang=en");
        if (bundleResp.ok) {
          await protoCache.put("/v1/protocols/offline-bundle?lang=en", bundleResp.clone());
        }
      } catch (e) {
        // Bundle not available yet — will be cached on first fetch
      }

      await self.skipWaiting();
    })(),
  );
});

// ─── Activate: Cleanup old caches ──────────────────────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      const oldCaches = keys.filter(
        (k) => k !== CACHE_NAME && k !== PROTOCOL_CACHE && k !== API_CACHE,
      );
      await Promise.all(oldCaches.map((k) => caches.delete(k)));
      await self.clients.claim();
    })(),
  );
});

// ─── Fetch handler ─────────────────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET") return;

  // Protocol bundle → cache-first (critical for offline)
  if (PROTOCOL_PATTERNS.some((p) => url.pathname.startsWith(p))) {
    event.respondWith(cacheFirstWithNetworkRefresh(request, PROTOCOL_CACHE));
    return;
  }

  // API calls → network-first with cache fallback
  if (API_CACHE_PATTERNS.some((p) => url.pathname.startsWith(p))) {
    event.respondWith(networkFirstWithTimeout(request, API_CACHE, 1000));
    return;
  }

  // Dispatch/status calls → cache-first for resilience
  if (url.pathname.includes("/v1/incident/")) {
    event.respondWith(cacheFirstWithNetworkRefresh(request, API_CACHE));
    return;
  }

  // App shell → cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((res) => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return res;
      });
    }),
  );
});

// ─── Strategy helpers ──────────────────────────────────────────────────────

async function cacheFirstWithNetworkRefresh(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    // Refresh in background
    fetch(request).then(async (res) => {
      if (res.ok) {
        await cache.put(request, res.clone());
        // Notify all clients of updated data
        const clients = await self.clients.matchAll({ type: "window" });
        clients.forEach((client) => {
          client.postMessage({ type: "PROTOCOL_UPDATED", url: request.url });
        });
      }
    }).catch(() => {});
    return cached;
  }
  try {
    const res = await fetch(request);
    if (res.ok) {
      await cache.put(request, res.clone());
    }
    return res;
  } catch {
    return new Response(
      JSON.stringify({ error: "offline", protocols: [] }),
      { status: 503, headers: { "Content-Type": "application/json" } },
    );
  }
}

async function networkFirstWithTimeout(request, cacheName, timeoutMs) {
  const cache = await caches.open(cacheName);

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const res = await fetch(request, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (res.ok) {
      await cache.put(request, res.clone());
    }
    return res;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;

    return new Response(
      JSON.stringify({ error: "offline", data: [] }),
      { status: 503, headers: { "Content-Type": "application/json" } },
    );
  }
}