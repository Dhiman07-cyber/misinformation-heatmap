import { createElement, qs, replaceChildren, setText } from '../utils/dom.js';
import { createMobileMenu, bindHamburger, ROUTES } from './hamburger.js';
import { createStatPanel, STATUS_CLASSES } from './ui.js';
import { mountBottomNavbar } from './bottomNavbar.js';

function createDesktopLink(route, activeRoute) {
  const active = route.key === activeRoute;
  return createElement('a', {
    className: `rounded-lg px-3 py-2 text-sm font-bold outline-none transition-all duration-200 hover:bg-slate-100 hover:text-ashoka-blue-600 focus-visible:ring-2 focus-visible:ring-saffron-500 focus-visible:ring-offset-2 ${active ? 'border border-saffron-200 bg-saffron-50 text-saffron-600 shadow-sm' : 'text-slate-600'}`,
    text: route.label,
    attrs: {
      href: route.href,
      ...(active ? { 'aria-current': 'page' } : {})
    }
  });
}

function createStatusPill(id, initialText) {
  return createElement('div', {
    className: `inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold ${STATUS_CLASSES.neutral}`,
    attrs: { role: 'status', 'aria-live': 'polite', 'data-status-pill': '' }
  }, [
    createElement('span', { className: 'h-2 w-2 rounded-full bg-current opacity-80', attrs: { 'aria-hidden': 'true' } }),
    createElement('span', { attrs: { id }, text: initialText })
  ]);
}

function createStatsPopover() {
  const popover = createElement('div', {
    className: 'absolute right-0 top-full z-50 mt-3 hidden w-[480px] origin-top-right rounded-2xl border border-saffron-100 bg-white p-1.5 shadow-premium group-hover:block group-focus-within:block animate-fade-in',
    attrs: { id: 'navbar-stats-popover', role: 'dialog', 'aria-label': 'Heatmap metrics' }
  }, [
    createElement('div', { className: 'flex divide-x divide-slate-100' }, [
      { label: 'Total Events', id: 'nav-stat-events', color: 'text-orange-500' },
      { label: 'Active States', id: 'nav-stat-active', color: 'text-india-green-600' },
      { label: 'Last Update', id: 'nav-stat-update', color: 'text-orange-500' },
      { label: 'Accuracy', id: 'nav-stat-accuracy', color: 'text-india-green-600' }
    ].map(stat => createElement('div', { className: 'flex-1 px-4 py-3 text-center' }, [
      createElement('p', { className: `text-lg font-bold leading-tight ${stat.color}`, text: '--', attrs: { id: stat.id } }),
      createElement('p', { className: 'mt-0.5 text-[10px] font-bold text-slate-400', text: stat.label })
    ])))
  ]);

  return createElement('div', { className: 'group relative hidden lg:block' }, [
    createElement('button', {
      className: 'inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-800 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-saffron-300 hover:bg-saffron-50 hover:text-saffron-600 focus-visible:ring-2 focus-visible:ring-saffron-500',
      attrs: {
        type: 'button',
        'aria-label': 'Show heatmap metrics'
      }
    }, [
      createElement('svg', {
        className: 'h-5 w-5',
        attrs: { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }
      }, [
        createElement('path', {
          attrs: { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2.5', d: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' }
        })
      ])
    ]),
    popover
  ]);
}

export function mountNavbar(options = {}) {
  const mount = qs('[data-navbar]');
  if (!mount) return;
  const page = options.page || document.body.dataset.page || 'home';
  const showStats = true;
  const statusId = options.statusId || `${page}-nav-status`;

  const header = createElement('header', {
    className: 'fixed top-0 z-40 w-full border-b border-slate-200/80 bg-white/90 backdrop-blur-xl'
  }, [
    createElement('nav', {
      className: 'mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:h-20 lg:h-16 sm:px-6 lg:px-8',
      attrs: { 'aria-label': 'Primary navigation' }
    }, [
      createElement('a', {
        className: 'inline-flex min-w-0 items-center gap-3 rounded-lg text-slate-950 no-underline outline-none transition hover:opacity-90 focus-visible:ring-2 focus-visible:ring-saffron-500 focus-visible:ring-offset-2',
        attrs: { href: '/', 'aria-label': 'Misinformation Heatmap home' }
      }, [
        createElement('img', {
          className: 'h-9 w-9 shrink-0 rounded-lg border border-slate-200 object-cover shadow-card sm:h-11 sm:w-11 lg:h-9 lg:w-9',
          attrs: { src: '/assets/ind.png', alt: 'India logo' }
        }),
        createElement('span', { className: 'min-w-0' }, [
          createElement('span', { className: 'block truncate text-sm font-extrabold leading-tight tracking-tight text-slate-950 sm:text-lg lg:text-base', text: 'Misinformation' }),
          createElement('span', { className: 'block truncate text-[11px] font-bold leading-tight text-india-green-600 sm:text-base lg:text-sm', text: 'Heatmap' })
        ])
      ]),
      createElement('div', { className: 'hidden items-center gap-1 lg:flex', attrs: { 'data-desktop-nav': '' } }, ROUTES.map((route) => createDesktopLink(route, page))),
      createElement('div', { className: 'flex items-center gap-3' }, [
        createElement('div', { className: 'hidden sm:flex' }, [
          createStatusPill(statusId, options.initialStatus || 'Checking')
        ]),
        page === 'heatmap' ? createStatsPopover() : null,
        createElement('button', {
          className: 'inline-flex h-11 w-11 flex-col items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white text-slate-950 shadow-md outline-none outline-offset-2 transition-all duration-150 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2 lg:hidden',
          attrs: {
            type: 'button',
            id: 'menu-toggle',
            'aria-controls': 'mobile-menu',
            'aria-expanded': 'false',
            'aria-label': 'Open navigation menu'
          }
        }, [
          createElement('span', { className: 'h-0.5 w-5 rounded-full bg-current transition-all duration-150' }),
          createElement('span', { className: 'h-0.5 w-5 rounded-full bg-current transition-all duration-150' }),
          createElement('span', { className: 'h-0.5 w-5 rounded-full bg-current transition-all duration-150' })
        ])
      ])
    ])
  ]);

  const mobileMenu = createMobileMenu({ activeRoute: page, showStats });
  replaceChildren(mount, [header, mobileMenu]);
  bindHamburger(qs('#menu-toggle', header), mobileMenu);

  mountBottomNavbar({ activeRoute: page });
}

export function updateMobileNavStatus(text) {
  setText('#mobile-nav-status', text);
}

export function updateStatsPanels(items) {
  // Desktop specific IDs
  const idMap = {
    'Total Events': '#nav-stat-events',
    'Active States': '#nav-stat-active',
    'Last Update': '#nav-stat-update',
    'Accuracy': '#nav-stat-accuracy'
  };

  items.forEach(item => {
    const selector = idMap[item.label];
    if (selector) {
      setText(selector, item.value);
    }
  });

  const mobile = qs('#mobile-stats-panel');
  if (mobile) {
    replaceChildren(mobile, createStatPanel(items, { title: 'Map metrics' }));
  }
}
