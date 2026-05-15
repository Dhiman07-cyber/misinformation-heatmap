import { getStats, peekCached } from '../api.js';
import { setProgress, updateStatusText } from '../components/ui.js';
import { updateMobileNavStatus, updateStatsPanels } from '../components/navbar.js';
import { setText } from '../utils/dom.js';
import { formatCount, formatPercent, numberOrNull } from '../utils/formatters.js';

function percentOf(value, total) {
  const numerator = numberOrNull(value);
  const denominator = numberOrNull(total);
  if (numerator === null || denominator === null || denominator <= 0) return null;
  return (numerator / denominator) * 100;
}

function setUnavailable() {
  [
    '#home-fake-count',
    '#home-real-count',
    '#home-states-count',
    '#home-total-events',
    '#home-misinformation-events',
    '#home-verified-events',
    '#home-accuracy-events',
    '#home-accuracy-aside',
    '#home-fake-percent',
    '#home-real-percent'
  ].forEach((selector) => setText(selector, '--'));
  setText('#home-total-label', 'Connecting');
  setText('#home-data-state', 'Connecting to real-time intelligence...');
  setProgress('home-fake-bar', 0);
  setProgress('home-real-bar', 0);
  updateStatusText('home-nav-status', 'Connecting...', 'neutral');
  updateMobileNavStatus('Connecting...');
}

function updateHome(data) {
  const total = numberOrNull(data.total_events);
  const fake = numberOrNull(data.fake_events);
  const real = numberOrNull(data.real_events);
  const totalStates = numberOrNull(data.total_states);
  const divisor = total ?? [fake, real].filter((v) => v !== null).reduce((s, v) => s + v, 0);
  const statesText = totalStates === null ? '--' : formatCount(totalStates);

  setText('#home-fake-count', formatCount(fake));
  setText('#home-real-count', formatCount(real));
  setText('#home-states-count', statesText);
  setText('#home-total-events', formatCount(total));
  setText('#home-misinformation-events', formatCount(fake));
  setText('#home-verified-events', formatCount(real));
  setText('#home-accuracy-events', formatPercent(data.classification_accuracy));
  setText('#home-accuracy-aside', formatPercent(data.classification_accuracy));
  setText('#home-total-label', total === null ? 'No total yet' : `${formatCount(total)} total`);

  const fakePct = percentOf(fake, divisor);
  const realPct = percentOf(real, divisor);

  setText('#home-fake-percent', fakePct === null ? '--' : formatPercent(fakePct));
  setText('#home-real-percent', realPct === null ? '--' : formatPercent(realPct));
  setProgress('home-fake-bar', fakePct || 0);
  setProgress('home-real-bar', realPct || 0);

  const processing = Boolean(data.processing_active);
  const mlReady = Boolean(data.ml_ready);
  const statusText = processing ? 'Live processing' : mlReady ? 'System ready' : 'Data loaded';
  updateStatusText('home-nav-status', statusText, processing || mlReady ? 'good' : 'neutral');
  updateMobileNavStatus(statusText);

  updateStatsPanels([
    { label: 'Events', value: formatCount(total), className: 'text-blue-700' },
    { label: 'Risk', value: formatCount(fake), className: 'text-saffron-700' },
    { label: 'Accuracy', value: formatPercent(data.classification_accuracy), className: 'text-emerald-700' },
    { label: 'States', value: statesText, className: 'text-slate-950' }
  ]);

  setText('#home-data-state', 'Live backend values loaded successfully.');
}

export async function initHome() {
  const cached = peekCached('/api/v1/stats');
  if (cached) {
    updateHome(cached);
  } else {
    updateStatusText('home-nav-status', 'Loading data', 'neutral');
    updateMobileNavStatus('Loading data');
  }

  try {
    const stats = await getStats();
    updateHome(stats);
  } catch {
    if (!cached) setUnavailable();
    // Retry once after 5s — covers cold-start when backend ML models are still loading
    setTimeout(async () => {
      try {
        const stats = await getStats({ cacheMs: 0 });
        updateHome(stats);
      } catch { /* next interval will handle it */ }
    }, 5000);
  }

  initTypewriter();

  window.setInterval(async () => {
    if (document.visibilityState !== 'visible') return;
    try {
      const stats = await getStats();
      updateHome(stats);
    } catch {
      // Silently preserve the last known data on background refresh failures.
      // The stale-while-revalidate cache in api.js handles returning cached data,
      // so this catch only fires when there was never any data at all.
    }
  }, 30000);
}

function initTypewriter() {
  const textElement = document.getElementById('typewriter-text');
  if (!textElement) return;

  const words = [
    'before it spreads.',
    'across Indian news.',
    'in real-time.',
    'before it goes viral.'
  ];

  let wordIndex = 0;
  let text = '';
  let isDeleting = false;
  let typeSpeed = 100;

  // Initial setup so we start by deleting the first hardcoded word
  textElement.textContent = words[0];
  text = words[0];
  isDeleting = true;

  function type() {
    const current = wordIndex % words.length;
    const fullText = words[current];

    if (isDeleting) {
      text = fullText.substring(0, text.length - 1);
      typeSpeed = 40;
    } else {
      text = fullText.substring(0, text.length + 1);
      typeSpeed = 80;
    }

    textElement.textContent = text;

    if (!isDeleting && text === fullText) {
      // Pause at the end of the word
      typeSpeed = 3000;
      isDeleting = true;
    } else if (isDeleting && text === '') {
      isDeleting = false;
      wordIndex++;
      // Pause before starting next word
      typeSpeed = 500;
    }

    setTimeout(type, typeSpeed);
  }

  // Start the effect after a brief delay
  setTimeout(type, 3000);
}
