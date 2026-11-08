{% load static %}{% get_static_prefix as static_prefix %}{% get_media_prefix as media_prefix %}const UI_CACHE = "ui-{{ version }}";
const MEDIA_CACHE = "media-v1";
const STATIC_PREFIX = "{{ static_prefix|escapejs }}";
const MEDIA_PREFIX = "{{ media_prefix|escapejs }}";
const ADMIN_PREFIX = "{% url 'admin:index' as admin_url %}{{ admin_url|escapejs }}";
const CDN_ORIGINS = ["https://cdn.jsdelivr.net"];

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith("ui-") && k !== UI_CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

const cacheable = (res) => (res.status === 200 && !res.redirected) || res.type === "opaque";

async function cacheFirst(cacheName, request) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  if (hit) return hit;
  const res = await fetch(request);
  if (cacheable(res)) await cache.put(request, res.clone());
  return res;
}

// Pages carry live data, so prefer the network and fall back to the cache offline.
async function networkFirst(request) {
  const cache = await caches.open(UI_CACHE);
  try {
    const res = await fetch(request);
    if (cacheable(res)) await cache.put(request, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(request, { ignoreVary: true });
    if (hit) return hit;
    throw err;
  }
}

// <audio> asks for byte ranges; answer them from the fully cached file.
async function sliceRange(request, response) {
  const range = /^bytes=(\d*)-(\d*)$/.exec(request.headers.get("range") || "");
  if (!range) return response;
  const blob = await response.blob();
  const size = blob.size;
  let start, end;
  if (range[1]) {
    start = Number(range[1]);
    end = range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
  } else {
    start = Math.max(size - Number(range[2]), 0);
    end = size - 1;
  }
  if (start >= size || start > end) {
    return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
  }
  return new Response(blob.slice(start, end + 1), {
    status: 206,
    headers: {
      "Content-Type": response.headers.get("Content-Type") || "application/octet-stream",
      "Content-Length": String(end - start + 1),
      "Content-Range": `bytes ${start}-${end}/${size}`,
      "Accept-Ranges": "bytes",
    },
  });
}

async function handleMedia(request) {
  const cache = await caches.open(MEDIA_CACHE);
  const hit = await cache.match(request.url);
  if (hit) return sliceRange(request, hit);
  if (request.headers.has("range")) return fetch(request);
  // Images and other whole-file requests get cached as they load.
  const res = await fetch(request);
  if (res.status === 200) await cache.put(request.url, res.clone());
  return res;
}

const pending = new Map();

// Pages loaded before the worker took control (or before a UI update) missed the fetch handler.
async function precache(urls) {
  const ui = await caches.open(UI_CACHE);
  await Promise.allSettled(urls.map(async (href) => {
    const url = new URL(href, self.location.origin);
    const sameOrigin = url.origin === self.location.origin;
    if (sameOrigin && url.pathname.startsWith(MEDIA_PREFIX)) return cacheMedia(url.href);
    if (sameOrigin ? url.pathname.startsWith(ADMIN_PREFIX) : !CDN_ORIGINS.includes(url.origin)) return;
    if (await ui.match(url.href, { ignoreVary: true })) return;
    const res = await fetch(url.href, sameOrigin ? {} : { mode: "no-cors" });
    if (cacheable(res)) await ui.put(url.href, res);
  }));
}

function cacheMedia(url) {
  if (!pending.has(url)) {
    pending.set(url, (async () => {
      const cache = await caches.open(MEDIA_CACHE);
      if (await cache.match(url)) return;
      const res = await fetch(url);
      if (res.status === 200) await cache.put(url, res);
    })().finally(() => pending.delete(url)));
  }
  return pending.get(url);
}

self.addEventListener("message", (event) => {
  if (event.data?.type === "precache") {
    event.waitUntil(precache(event.data.urls));
    return;
  }
  if (event.data?.type !== "cache-media") return;
  const url = new URL(event.data.url, self.location.origin);
  if (url.origin === self.location.origin && url.pathname.startsWith(MEDIA_PREFIX)) {
    event.waitUntil(cacheMedia(url.href).catch(() => {}));
  }
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin === self.location.origin) {
    if (url.pathname.startsWith(MEDIA_PREFIX)) return event.respondWith(handleMedia(request));
    if (url.pathname.startsWith(STATIC_PREFIX)) return event.respondWith(cacheFirst(UI_CACHE, request));
    if (request.mode === "navigate" && !url.pathname.startsWith(ADMIN_PREFIX)) return event.respondWith(networkFirst(request));
  } else if (CDN_ORIGINS.includes(url.origin)) {
    event.respondWith(cacheFirst(UI_CACHE, request));
  }
});
