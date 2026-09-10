/**
 * NyaySetu Pro - Production Resilient Service Worker
 * Version: nyaysetu-pro-v1.0.2
 *
 * Safety Guarantees:
 * 1. Network-First for navigation / HTML: guarantees fresh deployments are never blocked by stale cache.
 * 2. Network-Only for all API calls (/api/*), Razorpay, Firebase, and authentication requests:
 *    zero stale legal data, zero stale tokens, zero payment interference.
 * 3. Cache-First only for immutable, content-hashed assets (/_expo/static/*, /assets/*, icons).
 * 4. Automatic cache purging of stale caches on activation.
 */

const CACHE_NAME = "nyaysetu-static-v2";
const IMMUTABLE_ASSETS = [
  "/icons/favicon-32x32.v2.png",
  "/icons/favicon-16x16.v2.png",
  "/icons/apple-touch-icon.v2.png",
  "/icons/pwa-192x192.v2.png",
  "/icons/pwa-512x512.v2.png",
  "/logo.webp",
  "/manifest.json",
  "/robots.txt"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(IMMUTABLE_ASSETS).catch((err) => {
        console.warn("[SW] Pre-cache skipped some optional assets:", err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.info("[SW] Purging outdated cache:", key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 1. Only handle GET requests
  if (req.method !== "GET") {
    return;
  }

  // 2. NETWORK-ONLY: Never cache API, Auth, Razorpay, or third-party dynamic services
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/auth/") ||
    url.pathname.includes("download") ||
    url.hostname.includes("vercel.app") ||
    url.hostname.includes("razorpay.com") ||
    url.hostname.includes("firebase") ||
    url.hostname.includes("googleapis.com") ||
    url.hostname.includes("google.com") ||
    url.hostname.includes("gstatic.com")
  ) {
    return;
  }

  // 3. NETWORK-FIRST for HTML navigation (guarantees new deploys load immediately)
  if (req.mode === "navigate" || req.headers.get("accept")?.includes("text/html")) {
    event.respondWith(
      fetch(req)
        .then((networkRes) => {
          if (networkRes && networkRes.status === 200) {
            const resClone = networkRes.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
          }
          return networkRes;
        })
        .catch(() => caches.match(req).then((cached) => cached || caches.match("/index.html")))
    );
    return;
  }

  // 4. CACHE-FIRST for content-hashed immutable static assets
  if (
    url.pathname.startsWith("/_expo/static/") ||
    url.pathname.startsWith("/assets/") ||
    url.pathname.startsWith("/icons/") ||
    url.pathname.endsWith(".webp") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".ico")
  ) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((networkRes) => {
          if (networkRes && networkRes.status === 200) {
            const resClone = networkRes.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
          }
          return networkRes;
        });
      })
    );
    return;
  }

  // Default: Network with cache fallback
  event.respondWith(
    fetch(req).catch(() => caches.match(req))
  );
});
