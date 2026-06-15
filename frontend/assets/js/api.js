import { sanitizeApiPath, sanitizeStateParam } from './utils/security.js';

const REMOTE_API_BASE = 'https://ndg07-heatmap.hf.space';
const LOCAL_DEV_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);
const isViteDev = LOCAL_DEV_HOSTS.has(window.location.hostname) && ['5173', '4173'].includes(window.location.port);
const API_BASE = window.location.hostname.endsWith('.netlify.app') || isViteDev
  ? REMOTE_API_BASE
  : '';

const REQUEST_TIMEOUT_MS = 45000;
const RETRY_DELAY_MS = 250;
const STORAGE_PREFIX = 'misinfo:api:';
const STORAGE_TTL_MS = 10 * 60 * 1000;
const MAX_STORAGE_BYTES = 512_000;

const cache = new Map();
const inflight = new Map();
const NON_PERSISTED_PATHS = new Set(['/api/v1/stats']);

function cacheKey(path) {
  return `${API_BASE}${path}`;
}

function canPersist(path) {
  return !NON_PERSISTED_PATHS.has(path);
}

function readStorage(key, { ignoreTtl = false } = {}) {
  try {
    const raw = sessionStorage.getItem(STORAGE_PREFIX + key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed) return null;
    if (!ignoreTtl && Date.now() - parsed.time > STORAGE_TTL_MS) return null;
    return parsed.data;
  } catch {
    return null;
  }
}

function writeStorage(key, data) {
  try {
    const payload = JSON.stringify({ time: Date.now(), data });
    if (payload.length > MAX_STORAGE_BYTES) return;
    sessionStorage.setItem(STORAGE_PREFIX + key, payload);
  } catch {
    // Storage full or unavailable
  }
}

function shouldRetryResponse(status) {
  return status === 429 || status === 502 || status === 503 || status === 504;
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function fetchWithRetry(url, signal, attempt = 0) {
  try {
    const response = await fetch(url, { signal, headers: { Accept: 'application/json' } });
    if (!response.ok) {
      if (attempt === 0 && shouldRetryResponse(response.status)) {
        await delay(RETRY_DELAY_MS);
        return fetchWithRetry(url, signal, 1);
      }
      throw new Error(`Request failed with status ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    if (signal.aborted) throw error;
    if (attempt === 0 && error instanceof TypeError) {
      await delay(RETRY_DELAY_MS);
      return fetchWithRetry(url, signal, 1);
    }
    throw error;
  }
}

/** Return last-known API payload synchronously (memory or sessionStorage). */
export function peekCached(path) {
  const safePath = sanitizeApiPath(path);
  if (!safePath) return null;
  const key = cacheKey(safePath);
  const cached = cache.get(key);
  if (cached) return cached.data;
  if (!canPersist(safePath)) return null;
  return readStorage(key);
}

function resolveFallback(key, skipStorage, cachedEntry, primary, secondary) {
  if (cachedEntry?.data != null) return cachedEntry.data;
  if (primary != null) return primary;
  if (!skipStorage && secondary != null) return secondary;
  return null;
}

function runBackgroundFetch(path, key, { skipStorage, timeoutMs, cachedEntry, stored, storedStale }) {
  const existing = inflight.get(key);
  if (existing) return existing;

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const fallback = resolveFallback(key, skipStorage, cachedEntry, stored, storedStale);

  const request = fetchWithRetry(API_BASE + path, controller.signal)
    .then((data) => {
      cache.set(key, { time: Date.now(), data });
      if (!skipStorage) writeStorage(key, data);
      return data;
    })
    .catch((error) => {
      if (fallback !== null) return fallback;
      if (error?.name === 'AbortError') {
        throw new Error('Request timed out. Showing last known data.');
      }
      throw error;
    })
    .finally(() => {
      window.clearTimeout(timeout);
      inflight.delete(key);
    });

  inflight.set(key, request);
  return request;
}

export async function fetchJson(path, options = {}) {
  const safePath = sanitizeApiPath(path);
  if (!safePath) {
    throw new Error('Invalid API path');
  }

  const { cacheMs = 0, skipStorage = false, timeoutMs = REQUEST_TIMEOUT_MS, force = false } = options;
  const key = cacheKey(safePath);
  const cached = cache.get(key);
  const now = Date.now();
  const useStorage = !skipStorage && canPersist(safePath);

  if (!force && cached && cacheMs > 0 && now - cached.time < cacheMs) {
    return cached.data;
  }

  const stored = useStorage ? readStorage(key) : null;
  const storedStale = useStorage ? readStorage(key, { ignoreTtl: true }) : null;
  const stale = resolveFallback(key, !useStorage, cached, stored, storedStale);

  if (!force && stale !== null && cacheMs > 0) {
    runBackgroundFetch(safePath, key, { skipStorage: !useStorage, timeoutMs, cachedEntry: cached, stored, storedStale }).catch(() => {});
    return stale;
  }

  const pending = inflight.get(key);
  if (pending) return pending;

  return runBackgroundFetch(safePath, key, { skipStorage: !useStorage, timeoutMs, cachedEntry: cached, stored, storedStale });
}

export function clearApiCache() {
  cache.clear();
  try {
    Object.keys(sessionStorage).forEach((k) => {
      if (k.startsWith(STORAGE_PREFIX)) sessionStorage.removeItem(k);
    });
  } catch {
    // ignore
  }
}

export function clearStateEventsCache(state) {
  const safeState = sanitizeStateParam(state);
  if (!safeState) return;
  const encoded = encodeURIComponent(safeState);
  for (const key of cache.keys()) {
    if (key.includes(`/api/v1/events/state/${encoded}`)) {
      cache.delete(key);
    }
  }
  try {
    Object.keys(sessionStorage).forEach((k) => {
      if (k.startsWith(STORAGE_PREFIX) && k.includes(`/api/v1/events/state/${encoded}`)) {
        sessionStorage.removeItem(k);
      }
    });
  } catch {
    // ignore
  }
}

function extractArray(payload, ...keys) {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === 'object') {
    for (const key of keys) {
      if (Array.isArray(payload[key])) return payload[key];
    }
  }
  return [];
}

export function getStats(options = {}) {
  return fetchJson('/api/v1/stats', { ...options, cacheMs: 0, skipStorage: true });
}

export function getHealth(options = {}) {
  return fetchJson('/health', { cacheMs: 10000, ...options });
}

export async function getHeatmapData(options = {}) {
  const payload = await fetchJson('/api/v1/heatmap/data', { cacheMs: 30000, ...options });
  return extractArray(payload, 'heatmap', 'heatmap_data', 'data');
}

export async function getLiveEvents(limit = 20, options = {}) {
  const safeLimit = Math.max(1, Math.min(500, Math.floor(Number(limit) || 20)));
  const path = `/api/v1/events/live?limit=${safeLimit}`;
  const payload = await fetchJson(path, { cacheMs: 8000, ...options });
  return extractArray(payload, 'events', 'data');
}

export async function getStateEvents(state, options = {}) {
  const safeState = sanitizeStateParam(state);
  if (!safeState) return [];
  const encoded = encodeURIComponent(safeState);
  const { limit = 100, ...fetchOptions } = options;
  const safeLimit = Math.max(1, Math.min(100, Math.floor(Number(limit) || 100)));
  const payload = await fetchJson(`/api/v1/events/state/${encoded}?limit=${safeLimit}`, { cacheMs: 8000, ...fetchOptions });
  return extractArray(payload, 'events', 'data');
}
