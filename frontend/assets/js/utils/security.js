/** @typedef {'fake'|'real'|'uncertain'|'unknown'} Classification */

const MAX_TEXT_LENGTH = 2000;
const MAX_PLAIN_TEXT_LENGTH = 600;
const MAX_STATE_LENGTH = 80;
const MAX_API_PATH_LENGTH = 256;

const FORBIDDEN_ATTR_PREFIX = /^on/i;
const SAFE_ATTR_NAMES = new Set([
  'id',
  'class',
  'href',
  'src',
  'alt',
  'title',
  'type',
  'role',
  'tabindex',
  'aria-label',
  'aria-hidden',
  'aria-live',
  'aria-expanded',
  'aria-controls',
  'aria-current',
  'aria-describedby',
  'viewBox',
  'preserveAspectRatio',
  'stroke',
  'stroke-width',
  'stroke-linecap',
  'stroke-linejoin',
  'fill',
  'd',
  'name',
  'for',
  'rel',
  'target',
  'width',
  'height',
  'xmlns',
  'viewbox'
]);

/** Tailwind utility tokens allowed in dynamic class strings from API-derived UI. */
const SAFE_CLASS_TOKEN = /^[a-z0-9_:/\-\[\].%]+$/i;

export const CLASSIFICATION_BADGE_CLASSES = {
  fake: 'border-red-200 bg-red-50 text-red-700',
  real: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  uncertain: 'border-amber-200 bg-amber-50 text-amber-700',
  unknown: 'border-slate-200 bg-slate-100 text-slate-600'
};

/**
 * Strip control chars and normalize whitespace for safe text insertion.
 * @param {unknown} value
 * @param {string} [fallback]
 * @param {number} [maxLen]
 */
export function toSafeText(value, fallback = '--', maxLen = MAX_TEXT_LENGTH) {
  if (value === null || value === undefined) return fallback;
  const text = String(value)
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxLen);
  return text || fallback;
}

/**
 * Convert untrusted HTML-ish feed text into plain text for display.
 * The result is rendered with textContent by callers, never as HTML.
 * @param {unknown} value
 * @param {string} [fallback]
 * @param {number} [maxLen]
 */
export function toPlainText(value, fallback = '', maxLen = MAX_PLAIN_TEXT_LENGTH) {
  if (value === null || value === undefined) return fallback;
  const raw = String(value).slice(0, Math.max(maxLen * 4, MAX_PLAIN_TEXT_LENGTH));
  if (!raw.trim()) return fallback;

  const parsed = new DOMParser().parseFromString(raw, 'text/html');
  parsed.querySelectorAll('script, style, template, noscript').forEach((node) => node.remove());
  return toSafeText(parsed.body?.textContent || raw, fallback, maxLen);
}

/**
 * Allow only http(s) URLs; reject javascript:, data:, etc.
 * @param {unknown} value
 */
export function safeUrl(value) {
  if (value === null || value === undefined) return null;
  try {
    const raw = String(value).trim();
    if (!raw || raw.length > 2048) return null;
    const url = new URL(raw, window.location.origin);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    if (url.username || url.password) return null;
    return url.href;
  } catch {
    return null;
  }
}

/**
 * Sanitize dynamic class lists (blocks attribute injection via className).
 * @param {unknown} value
 * @param {string} [fallback]
 */
export function sanitizeClassList(value, fallback = '') {
  const raw = toSafeText(value, '', 500);
  if (!raw) return fallback;
  const tokens = raw.split(/\s+/).filter((token) => SAFE_CLASS_TOKEN.test(token));
  return tokens.length ? tokens.join(' ') : fallback;
}

/**
 * @param {unknown} classification
 */
export function badgeClassForClassification(classification) {
  const key = toSafeText(classification, 'unknown', 32).toLowerCase();
  if (key === 'fake' || key === 'misinformation') return CLASSIFICATION_BADGE_CLASSES.fake;
  if (key === 'real' || key === 'verified') return CLASSIFICATION_BADGE_CLASSES.real;
  if (key === 'uncertain' || key === 'review') return CLASSIFICATION_BADGE_CLASSES.uncertain;
  return CLASSIFICATION_BADGE_CLASSES.unknown;
}

/**
 * Validate relative API paths (no open redirects / path traversal).
 * @param {unknown} path
 */
export function sanitizeApiPath(path) {
  const raw = String(path || '').trim();
  if (!raw || raw.length > MAX_API_PATH_LENGTH) return null;
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.includes('..')) return null;
  if (/[<>"'`\\\s]/.test(raw)) return null;
  return raw;
}

/**
 * State/region slug for /api/v1/events/state/{state}
 * @param {unknown} state
 */
export function sanitizeStateParam(state) {
  const text = toSafeText(state, '', MAX_STATE_LENGTH);
  if (!text) return null;
  const cleaned = text.replace(/[^a-zA-Z0-9\s.\-()&']/g, '').trim();
  return cleaned || null;
}

/**
 * @param {string} name
 * @param {unknown} value
 */
export function isSafeAttribute(name, value) {
  if (!name || FORBIDDEN_ATTR_PREFIX.test(name)) return false;
  const lower = name.toLowerCase();
  if (!SAFE_ATTR_NAMES.has(lower) && !lower.startsWith('aria-') && !lower.startsWith('data-')) {
    return false;
  }
  if (lower === 'href' || lower === 'src') {
    return safeUrl(value) !== null || String(value).startsWith('/');
  }
  if (lower === 'style') return false;
  return true;
}

/**
 * @param {Element} element
 * @param {string} name
 * @param {unknown} value
 */
export function setSafeAttribute(element, name, value) {
  if (!element || !isSafeAttribute(name, value)) return;
  const lower = name.toLowerCase();
  if (lower === 'href' || lower === 'src') {
    const url = safeUrl(value);
    if (url) element.setAttribute(name, url);
    else if (lower === 'src' && String(value).startsWith('/')) {
      element.setAttribute(name, String(value).slice(0, 512));
    }
    return;
  }
  element.setAttribute(name, value === true ? '' : String(value));
}

export function isInteractiveInput(target) {
  if (!(target instanceof Element)) return false;
  const tag = target.tagName.toLowerCase();
  return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable;
}
