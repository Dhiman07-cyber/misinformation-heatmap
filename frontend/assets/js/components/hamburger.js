import { createElement, qs, qsa } from '../utils/dom.js';
import { createStatPanel } from './ui.js';

export const ROUTES = [
  { key: 'home', label: 'Home', href: '/' },
  { key: 'dashboard', label: 'Dashboard', href: '/dashboard.html' },
  { key: 'heatmap', label: 'Heatmap', href: '/heatmap.html' }
];

function createMobileLink(route, activeRoute) {
  const active = route.key === activeRoute;
  return createElement('a', {
    className: `rounded-lg border px-4 py-4 text-base font-bold shadow-premium outline-none transition-all duration-200 hover:border-saffron-300 hover:bg-saffron-50 hover:text-saffron-600 focus-visible:ring-2 focus-visible:ring-saffron-500 focus-visible:ring-offset-2 ${active ? 'border-saffron-300 bg-saffron-50 text-saffron-600' : 'border-slate-200 bg-white text-slate-800'}`,
    text: route.label,
    attrs: {
      href: route.href,
      ...(active ? { 'aria-current': 'page' } : {})
    }
  });
}

export function createMobileMenu(options = {}) {
  const { activeRoute, showStats } = options;
  const closeButton = createElement('button', {
    className: 'rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700 shadow-premium outline-none transition-all duration-200 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-saffron-500 focus-visible:ring-offset-2',
    text: 'Close',
    attrs: { type: 'button', id: 'mobile-menu-close', 'aria-label': 'Close navigation menu' }
  });

  const menu = createElement('div', {
    className: 'fixed inset-0 z-50 hidden overflow-y-auto bg-white/95 backdrop-blur-xl',
    attrs: { id: 'mobile-menu', 'aria-hidden': 'true' }
  }, [
    createElement('div', {
      className: 'mx-auto flex min-h-full w-full max-w-md flex-col justify-between px-5 py-6'
    }, [
      createElement('div', {}, [
        createElement('div', { className: 'mb-7 flex items-center justify-between gap-4' }, [
          createElement('a', {
            className: 'inline-flex min-w-0 items-center gap-3 rounded-lg text-slate-950 no-underline outline-none transition hover:opacity-90 focus-visible:ring-2 focus-visible:ring-saffron-500 focus-visible:ring-offset-2',
            attrs: { href: '/', 'aria-label': 'Misinformation Heatmap home' }
          }, [
            createElement('img', {
              className: 'h-10 w-10 shrink-0 rounded-lg border border-slate-200 object-cover shadow-card',
              attrs: { src: '/assets/ind.png', alt: 'India logo' }
            }),
            createElement('span', { className: 'min-w-0 text-sm font-black leading-tight tracking-tight text-slate-950 whitespace-nowrap' }, [
              createElement('span', { className: 'text-slate-950', text: 'Misinformation' }),
              createElement('span', { className: 'text-india-green-600 ml-1', text: 'Heatmap' })
            ])
          ]),
          closeButton
        ]),
        createElement('div', { className: 'grid gap-3' }, ROUTES.map((route) => createMobileLink(route, activeRoute)))
      ]),
      createElement('div', { className: 'mt-8 grid gap-4' }, [
        showStats ? createElement('div', { attrs: { id: 'mobile-stats-panel' } }, [
          createStatPanel([
            { label: 'Events', value: '--', className: 'text-blue-700' },
            { label: 'Active', value: '--', className: 'text-saffron-700' },
            { label: 'Accuracy', value: '--', className: 'text-emerald-700' },
            { label: 'Selected', value: '--', className: 'text-slate-950' }
          ], { title: 'Map metrics' })
        ]) : null,
        createElement('div', {
          className: 'rounded-lg border border-slate-200 bg-white p-4 shadow-card'
        }, [
          createElement('p', { className: 'text-xs font-black text-slate-500', text: 'Alpha Version 1.1' }),
          createElement('p', { className: 'mt-2 text-sm font-semibold text-slate-900', attrs: { id: 'mobile-nav-status' }, text: 'Checking live pipeline' })
        ])
      ])
    ])
  ]);

  return menu;
}

export function bindHamburger(toggle, menu) {
  if (!toggle || !menu) return;
  const close = qs('#mobile-menu-close', menu);

  function setOpen(isOpen) {
    const lines = toggle.querySelectorAll('span');
    if (isOpen) {
      lines[0].style.transform = 'translateY(8px) rotate(45deg)';
      lines[1].style.opacity = '0';
      lines[2].style.transform = 'translateY(-8px) rotate(-45deg)';
    } else {
      lines[0].style.transform = '';
      lines[1].style.opacity = '';
      lines[2].style.transform = '';
    }
    toggle.classList.toggle('is-open', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
    toggle.setAttribute('aria-label', isOpen ? 'Close navigation menu' : 'Open navigation menu');
    menu.classList.toggle('is-open', isOpen);
    menu.classList.toggle('flex', isOpen);
    menu.classList.toggle('hidden', !isOpen);
    menu.setAttribute('aria-hidden', String(!isOpen));
    document.body.classList.toggle('overflow-hidden', isOpen);
    
    // Hide bottom navbar when mobile menu is open
    const bottomNav = qs('#bottom-premium-nav');
    if (bottomNav) {
      if (isOpen) bottomNav.classList.add('hidden');
      else bottomNav.classList.remove('hidden');
    }

    if (isOpen) {
      const firstFocusable = qs('a, button', menu);
      if (firstFocusable) firstFocusable.focus({ preventScroll: true });
    }
  }

  toggle.addEventListener('click', () => setOpen(!menu.classList.contains('is-open')));
  if (close) close.addEventListener('click', () => setOpen(false));

  qsa('a', menu).forEach((link) => {
    link.addEventListener('click', () => setOpen(false));
  });

  menu.addEventListener('click', (event) => {
    if (event.target === menu) setOpen(false);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu.classList.contains('is-open')) {
      setOpen(false);
      toggle.focus({ preventScroll: true });
    }
  });
}
