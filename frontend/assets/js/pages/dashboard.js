import { clearApiCache, getHealth, getHeatmapData, getLiveEvents, getStats, peekCached } from '../api.js';
import { createHealthRow, renderEventList, setProgress, updateStatusText } from '../components/ui.js';
import { updateMobileNavStatus, updateStatsPanels } from '../components/navbar.js';
import { replaceChildren, setText } from '../utils/dom.js';
import { formatClock, formatCount, formatPercent, numberOrNull } from '../utils/formatters.js';
import { toSafeText } from '../utils/security.js';

const RING_CIRCUMFERENCE = 465;
let refreshInFlight = false;

function percentOf(value, total) {
  const numerator = numberOrNull(value);
  const denominator = numberOrNull(total);
  if (numerator === null || denominator === null || denominator <= 0) return null;
  return (numerator / denominator) * 100;
}

function updateStats(stats) {
  const total = numberOrNull(stats.total_events);
  const fake = numberOrNull(stats.fake_events);
  const real = numberOrNull(stats.real_events);
  const review = numberOrNull(stats.uncertain_events);
  const totalStates = numberOrNull(stats.total_states);
  const divisor = total ?? [fake, real, review].filter((v) => v !== null).reduce((s, v) => s + v, 0);

  setText('#dashboard-total-events', formatCount(total));
  setText('#dashboard-fake-events', formatCount(fake));
  setText('#dashboard-real-events', formatCount(real));

  const accuracy = numberOrNull(stats.classification_accuracy);
  setText('#dashboard-under-review-events', formatCount(review));

  setProgress('dashboard-total-bar', total === null ? 0 : 100);
  setProgress('dashboard-fake-bar', percentOf(fake, divisor) || 0);
  setProgress('dashboard-real-bar', percentOf(real, divisor) || 0);
  setProgress('dashboard-under-review-bar', percentOf(review, divisor) || 0);
  const normalizedAccuracy = accuracy === null ? 0 : Math.max(0, Math.min(100, Math.abs(accuracy) <= 1 ? accuracy * 100 : accuracy));

  setText('#dashboard-accuracy-pct', formatPercent(accuracy));
  setText('#dashboard-accuracy-badge', accuracy === null ? 'Unavailable' : 'High Confidence');
  const ring = document.getElementById('dashboard-accuracy-ring');
  if (ring) ring.style.strokeDashoffset = String(RING_CIRCUMFERENCE * (1 - normalizedAccuracy / 100));

  setText('#dashboard-precision', formatPercent(stats.precision, '--', 1));
  setText('#dashboard-recall', formatPercent(stats.recall, '--', 1));
  setText('#dashboard-f1', formatPercent(stats.f1_score ?? stats.f1, '--', 1));

  const processing = Boolean(stats.processing_active);
  const mlReady = Boolean(stats.ml_ready);
  const statusText = processing ? 'Live processing' : mlReady ? 'System ready' : 'Stats loaded';
  const statusState = processing || mlReady ? 'good' : 'neutral';
  updateStatusText('dashboard-nav-status', statusText, statusState);
  updateMobileNavStatus(statusText);

  // Update desktop floating pill status indicator
  const desktopHealthDot = document.getElementById('desktop-health-dot');
  const desktopHealthPing = document.getElementById('desktop-health-ping');
  if (desktopHealthDot && desktopHealthPing) {
    const isGood = statusState === 'good';
    desktopHealthDot.className = `h-full w-full rounded-full transition-colors duration-500 ${isGood ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]'}`;
    desktopHealthPing.className = `absolute h-full w-full animate-ping rounded-full opacity-40 transition-colors duration-500 ${isGood ? 'bg-emerald-500' : 'bg-amber-500'}`;
  }

  const lastUpdate = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });

  updateStatsPanels([
    { label: 'Events', value: formatCount(total), className: 'text-blue-700' },
    { label: 'Risk', value: formatCount(fake), className: 'text-saffron-700' },
    { label: 'Accuracy', value: formatPercent(accuracy), className: 'text-emerald-700' },
    { label: 'Last Update', value: lastUpdate },
    { label: 'Coverage', value: totalStates === null ? '--' : formatCount(totalStates), className: 'text-slate-950' }
  ]);
}

function updateStatsUnavailable() {
  [
    '#dashboard-total-events',
    '#dashboard-fake-events',
    '#dashboard-real-events',
    '#dashboard-under-review-events',
    '#dashboard-accuracy-pct',
    '#dashboard-precision',
    '#dashboard-recall',
    '#dashboard-f1'
  ].forEach((selector) => setText(selector, '--'));
  ['dashboard-total-bar', 'dashboard-fake-bar', 'dashboard-real-bar', 'dashboard-under-review-bar'].forEach((id) => setProgress(id, 0));
  setText('#dashboard-accuracy-badge', 'Connecting...');
}

function updateCoverage(heatmapData) {
  const records = Array.isArray(heatmapData) ? heatmapData : [];
  const regions = records.length;
  const active = records.filter((record) => numberOrNull(record.event_count ?? record.total_events) > 0).length;
  const events = records.reduce((sum, record) => sum + (numberOrNull(record.event_count ?? record.total_events) || 0), 0);
  const confidences = records
    .map((record) => numberOrNull(record.avg_confidence ?? record.ai_confidence ?? record.confidence ?? record.classification_confidence))
    .filter((value) => value !== null);
  const avgConf = confidences.length
    ? confidences.reduce((sum, value) => sum + value, 0) / confidences.length
    : null;

  setText('#dashboard-coverage-regions', formatCount(regions));
  setText('#dashboard-coverage-active', formatCount(active));
  setText('#dashboard-coverage-events', formatCount(events));
  setText('#dashboard-coverage-confidence', formatPercent(avgConf));
  setText(
    '#dashboard-coverage-note',
    regions ? 'Coverage is derived from the current heatmap API payload.' : 'The heatmap API returned no geographic records yet.'
  );
}

function updateCoverageUnavailable() {
  ['#dashboard-coverage-regions', '#dashboard-coverage-active', '#dashboard-coverage-events', '#dashboard-coverage-confidence'].forEach(id => setText(id, '--'));
  setText('#dashboard-coverage-note', 'Connecting to real-time spatial index...');
}

function renderHealthIndicators(results) {
  const stats = results.stats.status === 'fulfilled' ? results.stats.value : null;
  const health = results.health.status === 'fulfilled' ? results.health.value : null;
  const heatmap = results.heatmap.status === 'fulfilled' ? results.heatmap.value : null;
  const events = results.events.status === 'fulfilled' ? results.events.value : null;

  const indicators = [
    {
      id: 'gateway',
      label: 'Gateway Diagnostics',
      value: health ? toSafeText(health.status || health.message || 'Operational', 'Operational') : 'Connecting...',
      state: health ? 'good' : 'neutral',
      detail: health ? 'Primary API gateway is responding to health probes.' : 'Waiting for connection to gateway...'
    },
    {
      id: 'analytics',
      label: 'Analytics Engine',
      value: stats ? (stats.processing_active ? 'Active' : 'Idle') : 'Connecting...',
      state: stats ? (stats.processing_active ? 'good' : 'warn') : 'neutral',
      detail: stats ? 'Derived from live processing throughput flags.' : 'Analytics engine metrics are syncing...'
    },
    {
      id: 'neural',
      label: 'Neural Core Status',
      value: stats ? (stats.ml_ready ? 'Stable' : 'Initializing') : 'Connecting...',
      state: stats ? (stats.ml_ready ? 'good' : 'warn') : 'neutral',
      detail: stats ? 'Classification models are loaded and performing inference.' : 'Model core is warming up...'
    },
    {
      id: 'geospatial',
      label: 'Geospatial Index',
      value: heatmap ? `${heatmap.length} nodes` : 'Connecting...',
      state: heatmap ? (heatmap.length ? 'good' : 'warn') : 'neutral',
      detail: heatmap ? 'Geographic data clusters are synchronized for mapping.' : 'Spatial indexing service is synchronizing...'
    },
    {
      id: 'signal',
      label: 'Signal Integrity',
      value: events ? (events.length ? `${events.length} active` : 'Zero signals') : 'Connecting...',
      state: events ? (events.length ? 'good' : 'warn') : 'neutral',
      detail: events ? 'Signal feed is ingesting and classifying recent events.' : 'Integrity check: synchronizing signals...'
    }
  ];

  replaceChildren('#dashboard-health-indicators', indicators.map((ind) => createHealthRow(ind, { theme: 'light' })));

  const hasBad = indicators.some((indicator) => indicator.state === 'bad');
  const hasWarn = indicators.some((indicator) => indicator.state === 'warn');
  const status = hasBad ? 'Critical' : hasWarn ? 'Degraded' : (stats && health ? 'Operational' : 'Connecting');

  setText('#dashboard-health-badge', status);
}

function renderActivity(events) {
  const rendered = renderEventList('#dashboard-activity-feed', events, {
    limit: 15,
    emptyTitle: 'No recent events',
    emptyDetail: 'The pipeline is reachable, but no classifications were returned.'
  });
  setText('#dashboard-events-count', `${rendered.length} events`);
}

function renderActivityUnavailable() {
  renderEventList('#dashboard-activity-feed', [], {
    emptyTitle: 'Connecting to feed',
    emptyDetail: 'Synchronizing real-time events...'
  });
  setText('#dashboard-events-count', 'Connecting');
}

function hydrateDashboardFromCache() {
  const stats = peekCached('/api/v1/stats');
  const heatmapPayload = peekCached('/api/v1/heatmap/data');
  const eventsPayload = peekCached('/api/v1/events/live?limit=15');
  const health = peekCached('/health');

  if (stats) updateStats(stats);
  if (heatmapPayload) {
    const rows = Array.isArray(heatmapPayload)
      ? heatmapPayload
      : (heatmapPayload.heatmap || heatmapPayload.heatmap_data || heatmapPayload.data || []);
    if (rows.length) updateCoverage(rows);
  }
  if (eventsPayload) {
    const events = Array.isArray(eventsPayload)
      ? eventsPayload
      : (eventsPayload.events || eventsPayload.data || []);
    if (events.length) renderActivity(events);
  }
  if (stats || heatmapPayload || eventsPayload || health) {
    renderHealthIndicators({
      stats: { status: stats ? 'fulfilled' : 'rejected', value: stats },
      heatmap: {
        status: heatmapPayload ? 'fulfilled' : 'rejected',
        value: Array.isArray(heatmapPayload)
          ? heatmapPayload
          : (heatmapPayload?.heatmap || heatmapPayload?.heatmap_data || heatmapPayload?.data || null)
      },
      events: {
        status: eventsPayload ? 'fulfilled' : 'rejected',
        value: Array.isArray(eventsPayload)
          ? eventsPayload
          : (eventsPayload?.events || eventsPayload?.data || null)
      },
      health: { status: health ? 'fulfilled' : 'rejected', value: health }
    });
    setText('#dashboard-last-updated', `Last updated: ${formatClock()}`);
  }
  return Boolean(stats || heatmapPayload || eventsPayload);
}

export async function refreshDashboard(force = false) {
  if (refreshInFlight) return;
  refreshInFlight = true;
  const refreshButton = document.getElementById('dashboard-refresh');
  if (refreshButton) refreshButton.disabled = true;
  if (force) clearApiCache();
  else hydrateDashboardFromCache();

  const fetchOptions = force ? { cacheMs: 0 } : {};
  const results = { 
    stats: { status: 'pending', value: null }, 
    heatmap: { status: 'pending', value: null }, 
    events: { status: 'pending', value: null }, 
    health: { status: 'pending', value: null } 
  };

  const updateUI = () => renderHealthIndicators(results);

  await Promise.allSettled([
    getStats(fetchOptions).then((value) => {
      results.stats = { status: 'fulfilled', value };
      updateStats(value);
      updateUI();
    }).catch((reason) => {
      results.stats = { status: 'rejected', reason };
      updateUI();
    }),
    getHeatmapData(fetchOptions).then((value) => {
      const rows = Array.isArray(value) ? value : (value?.heatmap || value?.heatmap_data || value?.data || []);
      results.heatmap = { status: 'fulfilled', value: rows };
      updateCoverage(rows);
      updateUI();
    }).catch((reason) => {
      results.heatmap = { status: 'rejected', reason };
      updateUI();
    }),
    getLiveEvents(15, fetchOptions).then((value) => {
      const list = Array.isArray(value) ? value : (value?.events || value?.data || []);
      results.events = { status: 'fulfilled', value: list };
      renderActivity(list);
      updateUI();
    }).catch((reason) => {
      results.events = { status: 'rejected', reason };
      updateUI();
    }),
    getHealth(fetchOptions).then((value) => {
      results.health = { status: 'fulfilled', value };
      updateUI();
    }).catch((reason) => {
      results.health = { status: 'rejected', reason };
      updateUI();
    })
  ]);

  renderHealthIndicators(results);
  setText('#dashboard-last-updated', `Last updated: ${formatClock()}`);

  refreshInFlight = false;
  if (refreshButton) refreshButton.disabled = false;
}

export function initDashboard() {
  const refreshButton = document.getElementById('dashboard-refresh');
  const mobileRefreshButton = document.getElementById('dashboard-refresh-mobile');
  
  if (refreshButton) {
    refreshButton.addEventListener('click', () => refreshDashboard(true));
  }
  if (mobileRefreshButton) {
    mobileRefreshButton.addEventListener('click', () => refreshDashboard(true));
  }

  const healthOverlay = document.getElementById('dashboard-health-overlay');
  const healthTrigger = document.getElementById('bottom-nav-health-trigger');
  const desktopHealthTrigger = document.getElementById('desktop-health-trigger');
  const closeOverlay = document.getElementById('close-health-overlay');

  const toggleOverlay = (show) => {
    if (show) {
      healthOverlay.classList.remove('hidden', 'closing');
      // Force reflow
      healthOverlay.offsetHeight;
      healthOverlay.classList.add('active');
    } else {
      healthOverlay.classList.remove('active');
      healthOverlay.classList.add('closing');
      setTimeout(() => {
        if (healthOverlay.classList.contains('closing')) {
          healthOverlay.classList.add('hidden');
          healthOverlay.classList.remove('closing');
        }
      }, 300); // Match CSS animation duration (0.3s)
    }
  };

  const triggers = [healthTrigger, desktopHealthTrigger].filter(Boolean);
  if (triggers.length > 0 && healthOverlay) {
    triggers.forEach(trigger => {
      trigger.addEventListener('click', () => {
        const isActive = healthOverlay.classList.contains('active');
        toggleOverlay(!isActive);
      });
    });
  }

  if (closeOverlay && healthOverlay) {
    closeOverlay.addEventListener('click', () => toggleOverlay(false));
  }

  if (healthOverlay) {
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && healthOverlay.classList.contains('active')) {
        toggleOverlay(false);
      }
    });

    healthOverlay.addEventListener('click', (event) => {
      if (event.target === healthOverlay) toggleOverlay(false);
    });
  }

  refreshDashboard().catch(() => {
    // Retry once after 5s — covers cold-start when backend ML models are still loading
    setTimeout(() => refreshDashboard().catch(() => {}), 5000);
  });
  
  window.setInterval(() => {
    if (document.visibilityState === 'visible') {
      refreshDashboard().catch(() => {});
    }
  }, 30000);
}
