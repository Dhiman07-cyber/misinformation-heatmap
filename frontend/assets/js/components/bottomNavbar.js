import { createElement } from '../utils/dom.js';

function createSvgIcon(pathD) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'h-5 w-5');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('stroke-linecap', 'round');
  path.setAttribute('stroke-linejoin', 'round');
  path.setAttribute('stroke-width', '1.8');
  path.setAttribute('d', pathD);
  svg.appendChild(path);
  return svg;
}

const ICON_PATHS = {
  home: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  dashboard: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  heatmap: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7',
  health: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z'
};

function createTooltip(label) {
  const span = document.createElement('span');
  span.className = 'absolute -top-10 scale-0 rounded bg-slate-900 px-2 py-1 text-[10px] font-bold text-white transition-all group-hover:scale-100 whitespace-nowrap';
  span.textContent = label;
  return span;
}

export function mountBottomNavbar(options = {}) {
  const { activeRoute } = options;

  const container = createElement('div', {
    className: 'fixed bottom-6 left-1/2 z-[60] -translate-x-1/2 transform-gpu lg:hidden flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/90 p-2 shadow-[0_20px_50px_rgba(0,0,0,0.5)] backdrop-blur-2xl transition-all duration-500 hover:scale-[1.02]',
    attrs: { id: 'bottom-premium-nav' }
  });

  const routes = [
    { key: 'home', href: '/', label: 'Home' },
    { key: 'dashboard', href: '/dashboard.html', label: 'Dashboard' },
    { key: 'heatmap', href: '/heatmap.html', label: 'Heatmap' }
  ];

  if (activeRoute === 'dashboard') {
    routes.push({ key: 'health', id: 'bottom-nav-health-trigger', label: 'System Health' });
  }

  routes.forEach(route => {
    const isActive = route.key === activeRoute;
    const btnBaseClass = 'group relative flex h-12 items-center justify-center rounded-full transition-all duration-500 active:scale-95';
    const activeClass = isActive ? 'w-20 bg-white/10 text-white border border-white/20 shadow-[0_0_15px_rgba(255,255,255,0.15)]' : 'w-14 text-slate-400 hover:bg-white/5 hover:text-white';

    let element;
    if (route.href) {
      element = createElement('a', {
        className: `${btnBaseClass} ${activeClass}`,
        attrs: { href: route.href, 'aria-label': route.label }
      });
    } else {
      element = createElement('button', {
        className: `${btnBaseClass} ${activeClass}`,
        attrs: { type: 'button', 'aria-label': route.label, id: route.id }
      });
    }

    element.appendChild(createSvgIcon(ICON_PATHS[route.key]));
    element.appendChild(createTooltip(route.label));
    container.appendChild(element);
  });

  document.body.appendChild(container);
}
