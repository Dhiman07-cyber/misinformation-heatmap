import { createElement, replaceChildren, setText, setWidth } from '../utils/dom.js';
import { classificationLabel, formatDateTime, getEventClassification, getEventSource, getEventState, getEventTitle } from '../utils/formatters.js';
import { badgeClassForClassification, safeUrl, sanitizeClassList, toPlainText, toSafeText } from '../utils/security.js';

export const STATUS_CLASSES = {
  good: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warn: 'border-amber-200 bg-amber-50 text-amber-700',
  bad: 'border-red-200 bg-red-50 text-red-700',
  neutral: 'border-slate-200 bg-slate-50 text-slate-600'
};

export function updateStatusText(id, text, state = 'neutral') {
  const element = document.getElementById(id);
  if (!element) return;
  const pill = element.closest('[data-status-pill]');
  if (pill) {
    Object.values(STATUS_CLASSES).forEach((className) => {
      className.split(' ').forEach((item) => {
        if (item) pill.classList.remove(item);
      });
    });
    STATUS_CLASSES[state in STATUS_CLASSES ? state : 'neutral'].split(' ').forEach((item) => {
      if (item) pill.classList.add(item);
    });
  }
  setText(element, text);
}

export function setProgress(id, value) {
  setWidth(`#${id}`, value);
}

export function renderEmptyState(container, title, detail) {
  replaceChildren(container, createElement('article', {
    className: 'rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4'
  }, [
    createElement('p', { className: 'text-sm font-bold text-slate-900', text: title }),
    createElement('p', { className: 'mt-1 text-sm leading-6 text-slate-600', text: detail })
  ]));
}

export function createEventItem(event, options = {}) {
  const classification = getEventClassification(event);
  const type = options.type || classification;
  const tokenText = type === 'real' ? 'OK' : type === 'fake' ? 'FA' : (classificationLabel(classification) || '??').slice(0, 2).toUpperCase();
  const tokenClass = {
    fake: 'border-red-200 bg-red-50 text-red-700',
    real: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    uncertain: 'border-amber-200 bg-amber-50 text-amber-700',
    unknown: 'border-slate-200 bg-slate-100 text-slate-600'
  }[type] || 'border-slate-200 bg-slate-100 text-slate-600';

  const titleText = getEventTitle(event);
  const href = safeUrl(event && (event.url || event.link || event.article_url));
  const sourceRaw = event && (event.source || event.source_name || event.publisher);
  const stateRaw = event && (event.state || event.region || event.location);
  const sourceText = getEventSource(event);
  const stateText = getEventState(event);
  const timeText = formatDateTime(event && event.timestamp);
  // Only fields intended as summaries belong in the modal. The API's `content`
  // field is a truncated article excerpt, so showing it here overstates what we know.
  const bodyText = toPlainText(event && (event.description || event.summary || event.content), '');
  const hasSource = Boolean(toSafeText(sourceRaw, ''));
  const hasState = Boolean(toSafeText(stateRaw, ''));
  const hasTimestamp = timeText !== '--';

  const badgeClass = badgeClassForClassification(classification);

  const metaBadges = [
    createElement('span', {
      className: `inline-flex w-fit rounded-full border px-2 py-0.5 text-[10px] font-bold ${badgeClass}`,
      text: classificationLabel(classification)
    })
  ];
  if (hasSource) {
    metaBadges.push(createElement('span', { 
      className: 'inline-flex w-fit rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700', 
      text: sourceText 
    }));
  }
  if (hasState) {
    metaBadges.push(createElement('span', { 
      className: 'inline-flex w-fit rounded-full border border-purple-200 bg-purple-50 px-2 py-0.5 text-[10px] font-bold text-purple-700', 
      text: stateText 
    }));
  }
  if (hasTimestamp) {
    metaBadges.push(createElement('span', { 
      className: 'inline-flex w-fit rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-bold text-slate-700', 
      text: timeText 
    }));
  }

  const meta = createElement('div', {
    className: 'mt-2 flex flex-wrap items-center gap-1.5'
  }, metaBadges);

  const article = createElement('button', {
    className: 'group flex w-full min-w-0 gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left shadow-sm transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-saffron-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron-500 focus-visible:ring-offset-2',
    attrs: {
      type: 'button',
      'aria-label': `Open details for ${titleText}`
    }
  }, [
    createElement('div', {
      className: `flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border text-xs font-bold ${tokenClass}`,
      text: tokenText
    }),
    createElement('div', { className: 'min-w-0 flex-1' }, [
      createElement('h3', {
        className: 'line-clamp-2 break-words text-sm font-bold leading-6 text-slate-950 group-hover:text-saffron-700 transition-colors',
        text: titleText
      }),
      meta
    ])
  ]);

  // Parse ml_result and fact_check from JSON strings into structured objects
  let mlParsed = null;
  let factParsed = null;
  try {
    if (event && event.ml_result) {
      const raw = typeof event.ml_result === 'string' ? JSON.parse(event.ml_result) : event.ml_result;
      mlParsed = raw;
    }
  } catch (_) { /* ignore parse errors */ }
  try {
    if (event && event.fact_check) {
      const raw = typeof event.fact_check === 'string' ? JSON.parse(event.fact_check) : event.fact_check;
      factParsed = raw;
    }
  } catch (_) { /* ignore parse errors */ }

  article.addEventListener('click', () => {
    document.dispatchEvent(new CustomEvent('openEventModal', {
      detail: {
        titleText,
        href,
        classification,
        sourceText,
        stateText,
        timeText,
        hasSource,
        hasState,
        hasTimestamp,
        bodyText,
        mlParsed,
        factParsed
      }
    }));
  });

  return article;
}

export function renderEventList(container, events, options = {}) {
  const safeEvents = Array.isArray(events) ? events.filter(Boolean).slice(0, options.limit || 12) : [];
  if (!safeEvents.length) {
    renderEmptyState(
      container,
      options.emptyTitle || 'No data yet',
      options.emptyDetail || 'The layout is ready for incoming live events.'
    );
    return safeEvents;
  }

  replaceChildren(container, safeEvents.map((event) => createEventItem(event, options)));
  return safeEvents;
}

export function createHealthRow(indicator, options = {}) {
  const state = indicator.state || 'neutral';
  const isDark = options.theme === 'dark';
  
  const badgeClasses = {
    good: isDark ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-emerald-50 border-emerald-200 text-emerald-700',
    warn: isDark ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' : 'bg-amber-50 border-amber-200 text-amber-700',
    bad: isDark ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-red-50 border-red-200 text-red-700',
    neutral: isDark ? 'bg-white/5 border-white/10 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-600'
  };

  const badgeClass = badgeClasses[state] || badgeClasses.neutral;
  const containerClass = isDark 
    ? 'rounded-2xl border border-white/5 bg-white/5 p-4 transition-all hover:bg-white/10 hover:border-white/10'
    : 'rounded-lg border border-slate-200 bg-slate-50 p-3';

  return createElement('div', {
    className: containerClass
  }, [
    createElement('div', { className: 'flex items-start justify-between gap-4' }, [
      createElement('div', { className: 'min-w-0 flex-1' }, [
        createElement('p', { className: `text-sm font-bold ${isDark ? 'text-white' : 'text-slate-950'}`, text: indicator.label }),
        createElement('p', { className: `mt-1 text-xs leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-600'}`, text: indicator.detail || 'No additional detail.' })
      ]),
      createElement('span', {
        className: `shrink-0 rounded-full border px-3 py-1 text-[10px] font-bold ${badgeClass}`,
        text: indicator.value || 'Connecting...'
      })
    ])
  ]);
}

export function createStatPanel(items, options = {}) {
  const title = toSafeText(options.title, 'Live metrics');
  const panel = createElement('div', {
    className: 'rounded-xl border border-slate-200 bg-white p-5 shadow-premium backdrop-blur-md'
  }, [
    createElement('p', { className: 'text-xs font-bold text-slate-500', text: title }),
    createElement('dl', {
      className: 'mt-4 grid grid-cols-2 gap-4'
    }, items.map((item) => createElement('div', {
      className: 'rounded-xl border border-slate-200 bg-slate-50 p-3.5 transition-colors hover:bg-white'
    }, [
      createElement('dt', { className: 'text-xs font-bold text-slate-500', text: item.label }),
      createElement('dd', {
        className: `mt-1 text-xl font-bold ${item.className || 'text-slate-950'}`,
        text: item.value
      })
    ])))
  ]);
  return panel;
}

export function createFeedLoadingSpinner() {
  return createElement('div', {
    className: 'flex items-center justify-center py-12 animate-pulse',
    attrs: { role: 'status', 'aria-live': 'polite', 'aria-label': 'Loading feed' }
  }, [
    createElement('div', { className: 'h-6 w-6 rounded-full border-2 border-slate-200 border-t-slate-500 animate-spin', attrs: { 'aria-hidden': 'true' } })
  ]);
}

function createDetailBadge(text, colorClass) {
  const base = 'inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold';
  return createElement('span', {
    className: `${base} ${sanitizeClassList(colorClass)}`,
    text
  });
}

/**
 * Populate event detail modal using DOM APIs only (no innerHTML).
 * @param {object} detail
 */
export function populateEventDetailModal(detail = {}) {
  const classification = detail.classification || 'unknown';
  const badgeClass = badgeClassForClassification(classification);

  const badgesContainer = document.getElementById('event-detail-badges');
  if (badgesContainer) {
    const badges = [createDetailBadge(classificationLabel(classification), badgeClass)];
    if (detail.hasSource) {
      badges.push(createDetailBadge(detail.sourceText, 'border-blue-200 bg-blue-50 text-blue-700'));
    }
    if (detail.hasState) {
      badges.push(createDetailBadge(detail.stateText, 'border-purple-200 bg-purple-50 text-purple-700'));
    }
    if (detail.hasTimestamp) {
      badges.push(createDetailBadge(detail.timeText, 'border-slate-200 bg-slate-50 text-slate-700'));
    }
    replaceChildren(badgesContainer, badges);
  }

  setText('#event-detail-title', detail.titleText || 'Untitled event');

  const contentContainer = document.getElementById('event-detail-content');
  if (contentContainer) {
    const bodyText = toPlainText(detail.bodyText, '');
    const ml = detail.mlParsed;
    const fc = detail.factParsed;
    const hasContent = Boolean(bodyText || ml || fc);
    contentContainer.classList.toggle('hidden', !hasContent);
    
    const elements = [];

    // ─── AI Analysis Card ───────────────────────────────────
    if (ml && typeof ml === 'object') {
      const prediction = (ml.prediction || '').toLowerCase();
      const confidence = ml.confidence ?? ml.fake_probability ?? 0;
      const confPct = Math.round(confidence * 100);
      const isFake = prediction === 'fake';
      
      // Color scheme based on prediction
      const borderColor = isFake 
        ? 'border-red-200' 
        : 'border-emerald-200';
      const bgColor = isFake 
        ? 'bg-gradient-to-br from-red-50 to-rose-50/50' 
        : 'bg-gradient-to-br from-emerald-50 to-green-50/50';
      const verdictBg = isFake 
        ? 'bg-red-600' 
        : 'bg-emerald-600';
      const verdictText = isFake 
        ? 'Likely Misinformation' 
        : 'Likely Authentic';
      const barBg = isFake 
        ? 'bg-red-500' 
        : 'bg-emerald-500';
      const barTrack = isFake 
        ? 'bg-red-100' 
        : 'bg-emerald-100';

      const aiCard = createElement('div', { className: `mb-4 rounded-xl border ${borderColor} ${bgColor} p-4` }, [
        // Header row: icon + label
        createElement('div', { className: 'flex items-center gap-2 mb-3' }, [
          createElement('div', { className: 'flex h-5 w-5 items-center justify-center rounded-md bg-slate-900 text-[9px] font-bold text-white', text: 'AI' }),
          createElement('span', { className: 'text-[10px] font-bold text-slate-500 uppercase tracking-wider', text: 'AI Analysis' })
        ]),
        // Verdict badge
        createElement('div', { className: 'mb-3' }, [
          createElement('span', { className: `inline-flex items-center gap-1.5 rounded-full ${verdictBg} px-3 py-1 text-xs font-bold text-white shadow-sm`, text: verdictText })
        ]),
        // Confidence bar
        createElement('div', { className: 'flex items-center gap-3' }, [
          createElement('span', { className: 'text-[11px] font-bold text-slate-600 shrink-0', text: 'Confidence' }),
          createElement('div', { className: `flex-1 h-2 rounded-full ${barTrack} overflow-hidden` }, [
            createElement('div', { className: `h-full rounded-full ${barBg} transition-all duration-500`, style: `width: ${confPct}%` })
          ]),
          createElement('span', { className: 'text-[11px] font-extrabold text-slate-800 tabular-nums shrink-0', text: `${confPct}%` })
        ])
      ]);
      elements.push(aiCard);
    }

    // ─── Fact Check Card ────────────────────────────────────
    if (fc && typeof fc === 'object') {
      const checked = fc.checked === true;
      const verdict = (fc.verdict || 'unknown').toLowerCase();
      const fcSource = fc.source || null;
      const fcDetails = fc.details || '';
      
      if (checked && verdict !== 'unknown') {
        // Active fact-check found
        const verdictColors = {
          'false':      { border: 'border-red-200', bg: 'bg-gradient-to-br from-red-50 to-orange-50/30', badge: 'bg-red-600', label: 'FALSE' },
          'misleading': { border: 'border-amber-200', bg: 'bg-gradient-to-br from-amber-50 to-yellow-50/30', badge: 'bg-amber-600', label: 'MISLEADING' },
          'true':       { border: 'border-emerald-200', bg: 'bg-gradient-to-br from-emerald-50 to-green-50/30', badge: 'bg-emerald-600', label: 'TRUE' },
        };
        const style = verdictColors[verdict] || verdictColors['false'];

        const fcChildren = [
          // Header
          createElement('div', { className: 'flex items-center gap-2 mb-3' }, [
            createElement('div', { className: 'flex h-5 w-5 items-center justify-center rounded-md bg-blue-600 text-[9px] font-bold text-white', text: '✓' }),
            createElement('span', { className: 'text-[10px] font-bold text-slate-500 uppercase tracking-wider', text: 'Fact Check' })
          ]),
          // Verdict badge
          createElement('div', { className: 'mb-2' }, [
            createElement('span', { className: `inline-flex items-center rounded-full ${style.badge} px-3 py-1 text-xs font-bold text-white shadow-sm`, text: style.label })
          ])
        ];

        // Source attribution
        if (fcSource) {
          fcChildren.push(
            createElement('p', { className: 'text-[11px] text-slate-500 mb-1.5' }, [
              createElement('span', { className: 'font-bold', text: 'Source: ' }),
              createElement('span', { className: 'text-blue-700 font-bold', text: fcSource })
            ])
          );
        }

        // Details
        if (fcDetails && fcDetails !== 'No matching fact-checks found') {
          fcChildren.push(
            createElement('p', { className: 'text-sm text-slate-600 leading-relaxed', text: fcDetails })
          );
        }

        elements.push(createElement('div', { className: `mb-4 rounded-xl border ${style.border} ${style.bg} p-4` }, fcChildren));
      } else {
        // No fact-check match
        elements.push(createElement('div', { className: 'mb-4 rounded-xl border border-slate-200 bg-slate-50/50 p-4' }, [
          createElement('div', { className: 'flex items-center gap-2' }, [
            createElement('div', { className: 'flex h-5 w-5 items-center justify-center rounded-md bg-slate-400 text-[9px] font-bold text-white', text: '?' }),
            createElement('span', { className: 'text-[10px] font-bold text-slate-400 uppercase tracking-wider', text: 'Fact Check' })
          ]),
          createElement('p', { className: 'mt-2 text-sm text-slate-400 italic', text: 'No matching fact-checks found for this article.' })
        ]));
      }
    }

    // ─── Article Excerpt ────────────────────────────────────
    if (bodyText) {
      elements.push(createElement('div', { className: 'rounded-xl border border-slate-200/60 bg-white/60 p-4' }, [
        createElement('p', { className: 'text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2', text: 'Article excerpt' }),
        createElement('p', { className: 'whitespace-pre-wrap text-sm leading-relaxed text-slate-600', text: bodyText })
      ]));
    }
    
    replaceChildren(contentContainer, elements);
  }

  const linkBtn = document.getElementById('event-detail-link');
  if (linkBtn instanceof HTMLAnchorElement) {
    const href = safeUrl(detail.href);
    if (href) {
      linkBtn.href = href;
      linkBtn.rel = 'noopener noreferrer';
      linkBtn.classList.remove('hidden');
    } else {
      linkBtn.removeAttribute('href');
      linkBtn.classList.add('hidden');
    }
  }
}

export function showToast(message) {
  const existing = document.getElementById('global-toast');
  if (existing) existing.remove();

  const toast = createElement('div', {
    id: 'global-toast',
    className: 'fixed top-6 right-6 z-[100] flex items-center gap-3 rounded-xl border border-slate-200/60 bg-gradient-to-r from-saffron-50/80 via-white to-india-green-50/80 px-5 py-3 shadow-[0_15px_40px_rgba(0,0,0,0.1)] backdrop-blur-xl',
  }, [
    createElement('div', { className: 'flex items-center gap-1.5' }, [
      createElement('div', { className: 'h-1.5 w-1.5 rounded-full bg-saffron-500 animate-pulse' }),
      createElement('div', { className: 'h-1.5 w-1.5 rounded-full bg-slate-200' }),
      createElement('div', { className: 'h-1.5 w-1.5 rounded-full bg-india-green-500 animate-pulse', style: 'animation-delay: 0.5s' }),
    ]),
    createElement('span', { className: 'text-[11px] font-bold tracking-tight text-slate-800', text: message })
  ]);
  
  toast.style.animation = 'toastInRight 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards';

  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'toastOutRight 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards';
    setTimeout(() => toast.remove(), 500);
  }, 4500);
}
