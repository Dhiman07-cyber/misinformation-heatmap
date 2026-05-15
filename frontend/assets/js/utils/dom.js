import { sanitizeClassList, setSafeAttribute, toSafeText } from './security.js';

export function qs(selector, root = document) {
  if (typeof selector !== 'string' || !selector) return null;
  return root.querySelector(selector);
}

export function qsa(selector, root = document) {
  if (typeof selector !== 'string' || !selector) return [];
  return Array.from(root.querySelectorAll(selector));
}

const SVG_TAGS = new Set([
  'svg', 'path', 'circle', 'rect', 'line', 'polyline', 'polygon', 'ellipse',
  'g', 'defs', 'linearGradient', 'stop', 'filter', 'feGaussianBlur', 'feComposite'
]);

/**
 * @param {string} tag
 * @param {{ className?: string, text?: string, attrs?: Record<string, unknown>, dataset?: Record<string, unknown>, style?: string }} [options]
 * @param {Array<Node|string|number>} [children]
 */
export function createElement(tag, options = {}, children = []) {
  const isSvg = SVG_TAGS.has(tag);
  const element = isSvg
    ? document.createElementNS('http://www.w3.org/2000/svg', tag)
    : document.createElement(tag);

  const { className, text, attrs, dataset, style } = options;

  if (className) {
    const safeClass = sanitizeClassList(className);
    if (safeClass) {
      if (isSvg) element.setAttribute('class', safeClass);
      else element.className = safeClass;
    }
  }

  if (text !== undefined) {
    if (isSvg) element.append(document.createTextNode(toSafeText(text, '')));
    else element.textContent = toSafeText(text, '');
  }

  if (attrs) {
    Object.entries(attrs).forEach(([name, value]) => {
      if (value === false || value === null || value === undefined) return;
      setSafeAttribute(element, name, value);
    });
  }

  if (dataset) {
    Object.entries(dataset).forEach(([name, value]) => {
      if (value === null || value === undefined) return;
      const safeName = name.replace(/[^a-zA-Z0-9_-]/g, '');
      if (safeName) element.dataset[safeName] = toSafeText(value, '', 200);
    });
  }

  if (style && element instanceof HTMLElement) {
    element.setAttribute('style', String(style).slice(0, 500));
  }

  const safeChildren = Array.isArray(children) ? children : [children];
  safeChildren.filter(Boolean).forEach((child) => {
    if (typeof child === 'string' || typeof child === 'number') {
      element.append(document.createTextNode(String(child)));
    } else {
      element.append(child);
    }
  });

  return element;
}

export function setText(target, value, fallback = '--') {
  const element = typeof target === 'string' ? qs(target) : target;
  if (!element) return;
  element.textContent = toSafeText(value, fallback);
}

export function setWidth(target, value) {
  const element = typeof target === 'string' ? qs(target) : target;
  if (!element) return;
  const number = Number(value);
  const width = Number.isFinite(number) ? Math.max(0, Math.min(100, number)) : 0;
  element.style.width = `${width}%`;
}

export function replaceChildren(target, children = []) {
  const element = typeof target === 'string' ? qs(target) : target;
  if (!element) return;
  const safeChildren = Array.isArray(children) ? children : [children];
  element.replaceChildren(...safeChildren.filter(Boolean));
}

export function clearElement(target) {
  const element = typeof target === 'string' ? qs(target) : target;
  if (!element) return;
  element.replaceChildren();
}

export function toggleHidden(target, hidden) {
  const element = typeof target === 'string' ? qs(target) : target;
  if (!element) return;
  element.hidden = Boolean(hidden);
}

export function updateClassList(element, classNames, enabled) {
  if (!element) return;
  sanitizeClassList(classNames, '').split(/\s+/).filter(Boolean).forEach((className) => {
    element.classList.toggle(className, Boolean(enabled));
  });
}
