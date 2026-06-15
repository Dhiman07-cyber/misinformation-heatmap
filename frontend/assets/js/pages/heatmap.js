import { clearApiCache, clearStateEventsCache, getHeatmapData, getLiveEvents, getStateEvents, getStats, peekCached } from '../api.js';
import {
  createEventItem,
  createFeedLoadingSpinner,
  populateEventDetailModal,
  renderEventList,
  setProgress,
  showToast,
  updateStatusText
} from '../components/ui.js';
import { updateMobileNavStatus, updateStatsPanels } from '../components/navbar.js';
import { createElement, qs, qsa, replaceChildren, setText } from '../utils/dom.js';
import {
  formatCount,
  formatPercent,
  formatRatioAsPercent,
  getEventClassification,
  getFakeRatio,
  getEventState,
  getEventTitle,
  normalizeName,
  numberOrNull,
  riskFromRecord
} from '../utils/formatters.js';
import { isInteractiveInput, toSafeText } from '../utils/security.js';

const SVG_PATH = '/assets/map/in.svg';
const MIN_ZOOM = 0.72;
const MAX_ZOOM = 2.8;
const BUTTON_ZOOM_STEP = 0.12;
const MAP_BOUNDS_PADDING = 100;

const STATE_ALIASES = {
  'andaman and nicobar': 'Andaman and Nicobar Islands',
  'andaman and nicobar islands': 'Andaman and Nicobar Islands',
  'dadra and nagar haveli and daman and diu': 'Dadra and Nagar Haveli and Daman and Diu',
  'daman and diu': 'Dadra and Nagar Haveli and Daman and Diu',
  orissa: 'Odisha',
  uttaranchal: 'Uttarakhand',
  delhi: 'Delhi'
};

let heatmapData = [];
let stateLookup = new Map();
let latestStats = null;
let svgLoadPromise = null;
let selectedState = null;
let selectedStateRecord = null;
let svgMap = null;
let currentZoom = window.innerWidth <= 1024 ? 1.0 : 1.15;
let currentX = 0;
let currentY = 0;
let isDragging = false;
let lastPointerX = 0;
let lastPointerY = 0;
let pinchStartDistance = 0;
let pinchStartZoom = 1;
let mapInteractionActive = false;
let refreshInFlight = false;
let feedsGeneration = 0;
let globalEventsPool = null;

const FEED_DISPLAY_LIMIT = 10;
const LIVE_EVENTS_FETCH_LIMIT = 80;
const STATE_EVENTS_FETCH_LIMIT = 100;

function feedDelay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function mapStatus(text, state = 'neutral') {
  updateStatusText('heatmap-nav-status', text, state);
  updateMobileNavStatus(text);
}

function heatmapRecords() {
  return Array.isArray(heatmapData) ? heatmapData.filter(Boolean) : [];
}

function rebuildStateLookup(records = heatmapRecords()) {
  const map = new Map();
  for (const record of records) {
    const keys = [
      normalizeName(record.state),
      normalizeName(record.name),
      normalizeName(record.region)
    ].filter(Boolean);
    for (const key of keys) {
      if (!map.has(key)) map.set(key, record);
    }
  }
  for (const [alias, canonical] of Object.entries(STATE_ALIASES)) {
    const target = map.get(normalizeName(canonical));
    if (target) map.set(normalizeName(alias), target);
  }
  stateLookup = map;
}

function applyHeatmapPayload(records) {
  if (!Array.isArray(records)) return false;
  if (!records.length) return heatmapRecords().length > 0;
  heatmapData = records;
  rebuildStateLookup(records);
  return true;
}

function syncHeatmapView() {
  if (!svgMap) return;
  svgMap.removeAttribute('fill');
  if (heatmapRecords().length) {
    applyHeatmapColors();
    updateStatsPopover();
    mapStatus('Map live', 'good');
  } else {
    mapStatus('No heatmap data', 'warn');
  }
  hideLoading();
}

function hydrateHeatmapFromCache() {
  const stats = peekCached('/api/v1/stats');
  if (stats) {
    latestStats = stats;
    updateStatsPopover();
  }
  const payload = peekCached('/api/v1/heatmap/data');
  if (!payload) return false;
  const rows = Array.isArray(payload) ? payload : (payload.heatmap || payload.heatmap_data || payload.data || []);
  if (!rows.length) return false;
  applyHeatmapPayload(rows);
  return true;
}

function getRecordCount(record) {
  return numberOrNull(record && (record.event_count ?? record.total_events ?? record.events));
}

function totalMappedEvents() {
  return heatmapRecords().reduce((sum, record) => sum + (getRecordCount(record) || 0), 0);
}

function activeMappedStates() {
  return heatmapRecords().filter((record) => (getRecordCount(record) || 0) > 0).length;
}

function updateStatsPopover() {
  const total = numberOrNull(latestStats && latestStats.total_events) ?? totalMappedEvents();
  const active = activeMappedStates();
  const accuracy = latestStats ? formatPercent(latestStats.classification_accuracy) : '--';
  const rawTs = latestStats && (latestStats.last_update_time || latestStats.last_update || latestStats.timestamp);
  const updateDate = rawTs ? new Date(rawTs) : null;
  const timeString = updateDate && !Number.isNaN(updateDate.getTime())
    ? updateDate.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    })
    : new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });

  updateStatsPanels([
    { label: 'Total Events', value: formatCount(total) },
    { label: 'Active States', value: heatmapRecords().length ? `${active} States` : '--' },
    { label: 'Last Update', value: timeString },
    { label: 'Accuracy', value: accuracy }
  ]);
}

function updateProgressBar(percent) {
  setProgress('heatmap-progress-bar', percent);
}

function hideLoading() {
  const loading = qs('#heatmap-loading');
  if (loading) loading.remove();
}

function showMapError(message) {
  const root = qs('#heatmap-svg-root');
  if (!root) return;
  replaceChildren(root, createElement('div', { className: 'max-w-sm px-6 text-center' }, [
    createElement('p', { className: 'text-lg font-bold text-slate-950', text: 'Map could not load' }),
    createElement('p', { className: 'mt-2 text-sm leading-6 text-slate-600', text: message })
  ]));
}

async function loadSvgMap() {
  updateProgressBar(20);
  const response = await fetch(SVG_PATH, { headers: { Accept: 'image/svg+xml,text/xml' } });
  if (!response.ok) throw new Error('SVG asset is unavailable.');
  const svgText = await response.text();
  const parsed = new DOMParser().parseFromString(svgText, 'image/svg+xml');
  if (parsed.querySelector('parsererror')) {
    console.error('SVG Parsing Error:', parsed.querySelector('parsererror').textContent);
    throw new Error('SVG asset could not be parsed safely.');
  }
  const sourceSvg = parsed.querySelector('svg');
  if (!sourceSvg) {
    console.error('SVG Source Error: No <svg> tag found in fetched content.');
    throw new Error('SVG root is missing.');
  }
  sanitizeInlineSvg(sourceSvg);

  const root = qs('#heatmap-svg-root');
  if (!root) throw new Error('Map container is missing.');
  replaceChildren(root, document.importNode(sourceSvg, true));
  svgMap = qs('svg', root);
  if (!svgMap) throw new Error('Map SVG was not inserted.');

  configureSvg();
  bindMapPaths();
  setupZoomAndPan();
  resetZoom();
  updateProgressBar(55);
}

function sanitizeInlineSvg(sourceSvg) {
  sourceSvg
    .querySelectorAll('script, foreignObject, iframe, object, embed, image, use, a, style, link')
    .forEach((node) => node.remove());

  [sourceSvg, ...sourceSvg.querySelectorAll('*')].forEach((element) => {
    Array.from(element.attributes).forEach((attribute) => {
      const name = attribute.name.toLowerCase();
      if (name.startsWith('on') || name === 'style' || name === 'href' || name === 'xlink:href') {
        element.removeAttribute(attribute.name);
      }
    });
  });
}

function configureSvg() {
  const sourceViewBox = svgMap.getAttribute('viewBox') || svgMap.getAttribute('viewbox') || '0 0 1000 1000';
  svgMap.setAttribute('viewBox', sourceViewBox);
  svgMap.removeAttribute('viewbox');
  svgMap.removeAttribute('width');
  svgMap.removeAttribute('height');
  svgMap.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  const classes = 'h-full max-h-full w-full max-w-full transition-transform duration-100 ease-out origin-center drop-shadow-md will-change-transform';
  svgMap.classList.add(...classes.split(' '));
  svgMap.setAttribute('aria-label', 'India state risk map');
}

function bindMapPaths() {
  qsa('path', svgMap).forEach((path) => {
    const fallbackName = path.getAttribute('name') || path.getAttribute('title') || path.id || 'Map region';
    const pathClasses = 'heatmap-path cursor-pointer stroke-white outline-none transition-[fill,stroke,stroke-width] duration-200 ease-out';
    path.classList.add(...pathClasses.split(' '));
    path.style.strokeWidth = '0.75';
    path.setAttribute('tabindex', '0');
    path.setAttribute('role', 'button');
    path.setAttribute('aria-label', fallbackName);
    path.addEventListener('click', handleStateClick);
    path.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleStateClick(event);
      }
    });
    path.addEventListener('mouseenter', (event) => {
      if (!path.classList.contains('selected')) {
        path.style.stroke = '#FF9933';
        path.style.strokeWidth = '2.5';
      }
      handleStateHover(event);
    });
    path.addEventListener('mousemove', handleStateHover);
    path.addEventListener('mouseleave', () => {
      if (!path.classList.contains('selected')) {
        path.style.stroke = '#ffffff';
        path.style.strokeWidth = '0.75';
      }
      hideTooltip();
    });
    path.addEventListener('focus', (event) => {
      if (!path.classList.contains('selected')) {
        path.style.stroke = '#E87722';
      }
      handleStateHover(event);
    });
    path.addEventListener('blur', (event) => {
      if (!path.classList.contains('selected')) {
        path.style.stroke = '#ffffff';
      }
      hideTooltip();
    });
  });
}

async function loadHeatmapData(force = false) {
  if (force) clearApiCache();
  else hydrateHeatmapFromCache();

  const fetchOptions = force ? { cacheMs: 0 } : {};
  updateProgressBar(70);
  const newData = await getHeatmapData(fetchOptions);
  applyHeatmapPayload(newData);
  updateProgressBar(100);
  return newData;
}

async function ensureSvgMap() {
  if (svgMap) return;
  svgLoadPromise = svgLoadPromise || loadSvgMap().catch((error) => {
    svgLoadPromise = null;
    throw error;
  });
  await svgLoadPromise;
}

async function refreshHeatmap(force = false) {
  if (refreshInFlight) return;
  refreshInFlight = true;
  const refreshButton = qs('#heatmap-refresh') || qs('#heatmap-header-refresh') || qs('#heatmap-refresh-mobile');
  if (refreshButton) refreshButton.disabled = true;

  try {
    await Promise.all([ensureSvgMap(), loadHeatmapData(force)]);
    syncHeatmapView();
    await Promise.allSettled([
      updateStats(),
      updateFeeds(Boolean(selectedState), { forceRefresh: force })
    ]);
  } catch (error) {
    console.error('Heatmap refresh failed:', error);
    hideLoading();
    if (!heatmapRecords().length) mapStatus('Connecting to spatial feed...', 'neutral');
    else syncHeatmapView();
  } finally {
    refreshInFlight = false;
    if (refreshButton) refreshButton.disabled = false;
  }
}

async function updateStats() {
  try {
    latestStats = await getStats();
    const processing = Boolean(latestStats.processing_active);
    const mlReady = Boolean(latestStats.ml_ready);
    mapStatus(processing ? 'Live processing' : mlReady ? 'System ready' : 'Map data loaded', processing || mlReady ? 'good' : 'neutral');
  } catch {
    latestStats = null;
  }
  updateStatsPopover();
}

function findStateData(pathElement) {
  if (!pathElement) return null;
  const rawName = pathElement.getAttribute('name') || pathElement.getAttribute('title') || pathElement.id || '';
  const normalizedSvgName = normalizeName(rawName);
  if (!normalizedSvgName) return null;

  const direct = stateLookup.get(normalizedSvgName);
  if (direct) return direct;

  const alias = STATE_ALIASES[normalizedSvgName];
  if (alias) {
    const aliasHit = stateLookup.get(normalizeName(alias));
    if (aliasHit) return aliasHit;
  }

  for (const [key, record] of stateLookup) {
    if (key.includes(normalizedSvgName) || normalizedSvgName.includes(key)) return record;
  }
  return null;
}

function applyHeatmapColors() {
  if (!svgMap) return;
  qsa('path', svgMap).forEach((path) => {
    const record = findStateData(path);
    const risk = riskFromRecord(record || { risk_level: 'insufficient_data' });
    path.setAttribute('fill', risk.color);
    path.style.fill = risk.color;
    path.style.stroke = '#ffffff';
    path.style.strokeWidth = '0.75';
    path.dataset.risk = risk.key;
    path.dataset.state = record ? toSafeText(record.state || record.name || path.getAttribute('name')) : toSafeText(path.getAttribute('name') || path.id);
  });
}

function handleStateClick(event) {
  event.stopPropagation();
  const path = event.currentTarget || event.target;
  if (!path || !svgMap) return;

  const candidateState = toSafeText(path.getAttribute('name') || path.id, 'Unknown state');
  const record = findStateData(path);
  const stateName = record ? toSafeText(record.state || record.name) : candidateState;

  if (selectedState === stateName) {
    clearStateSelection();
    return;
  }

  if (path.parentNode) {
    path.parentNode.appendChild(path);
  }
  qsa('.selected', svgMap).forEach((element) => {
    element.classList.remove('selected');
    element.style.strokeWidth = '0.75';
    element.style.stroke = '#ffffff';
  });
  path.classList.add('selected');
  path.style.strokeWidth = '3.5';
  path.style.stroke = '#FF9933';
  selectedStateRecord = record;
  selectedState = stateName;
  mapInteractionActive = true;

  updateStatsPopover();
  updateFeeds(true);
}


function clearStateSelection() {
  selectedState = null;
  selectedStateRecord = null;
  if (svgMap) {
    qsa('.selected', svgMap).forEach((element) => {
      element.classList.remove('selected');
      element.style.strokeWidth = '0.75';
      element.style.stroke = '#ffffff';
    });
  }

  updateStatsPopover();
  updateFeeds(true);
}

function handleStateHover(event) {
  const path = event.currentTarget || event.target;
  if (!path) return;
  const record = findStateData(path);
  const fallbackName = path.getAttribute('name') || path.id || 'Unknown state';
  showTooltip(event, record, fallbackName);
}

function showTooltip(event, record, fallbackName) {
  const tooltip = qs('#heatmap-tooltip');
  if (!tooltip) return;
  const risk = riskFromRecord(record || { risk_level: 'insufficient_data' });
  const children = [
    createElement('p', { className: 'font-bold text-white', text: record ? (record.state || record.name) : fallbackName })
  ];
  if (record) {
    const fakeCount = numberOrNull(record.fake_count ?? record.fake_events);
    const realCount = numberOrNull(record.real_count ?? record.real_events ?? record.verified_count ?? record.verified_events);
    children.push(
      createElement('p', { text: `Events: ${formatCount(record.event_count ?? record.total_events ?? record.events)}` }),
      createElement('p', { text: `Fake News: ${formatCount(fakeCount)}` }),
      createElement('p', { text: `Verified News: ${formatCount(realCount)}` }),
      createElement('p', { text: `Fake ratio: ${formatRatioAsPercent(getFakeRatio(record))}` }),
      createElement('p', { text: `Risk: ${risk.label}` })
    );
  } else {
    children.push(createElement('p', { className: 'text-slate-300', text: 'No live metrics available for this region.' }));
  }

  replaceChildren(tooltip, children);
  tooltip.style.display = 'block';
  tooltip.setAttribute('aria-hidden', 'false');

  // Dynamic positioning to prevent clipping
  const tooltipRect = tooltip.getBoundingClientRect();
  const gap = 15;
  let left = event.clientX + gap;
  let top = event.clientY + gap;

  // Horizontal clamping
  if (left + tooltipRect.width > window.innerWidth - gap) {
    left = event.clientX - tooltipRect.width - gap;
  }

  // Vertical clamping - if near bottom, show above cursor
  if (top + tooltipRect.height > window.innerHeight - gap) {
    top = event.clientY - tooltipRect.height - gap;
  }

  // Ensure it doesn't go off the top/left
  left = Math.max(gap, left);
  top = Math.max(gap, top);

  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function hideTooltip() {
  const tooltip = qs('#heatmap-tooltip');
  if (!tooltip) return;
  tooltip.style.display = 'none';
  tooltip.setAttribute('aria-hidden', 'true');
}

function activeMapStates() {
  return heatmapRecords()
    .filter((record) => (getRecordCount(record) || 0) > 0)
    .sort((a, b) => (getRecordCount(b) || 0) - (getRecordCount(a) || 0));
}

function matchesNormalizedState(candidate, expected) {
  if (!candidate || !expected) return false;
  return candidate === expected || candidate.includes(expected) || expected.includes(candidate);
}

function getCanonicalState(stateName) {
  const norm = normalizeName(stateName);
  if (!norm) return null;
  const alias = STATE_ALIASES[norm];
  return alias ? normalizeName(alias) : norm;
}

function eventMatchesState(event, stateName) {
  const expected = getCanonicalState(stateName);
  if (!expected) return false;

  // Primary check: state field
  const eventState = getEventState(event);
  if (eventState && getCanonicalState(eventState) === expected) return true;

  // Secondary checks: other fields
  const candidates = [
    event.location,
    event.region,
    getEventTitle(event)
  ].map(getCanonicalState).filter(Boolean);

  return candidates.some((candidate) => candidate === expected || candidate.includes(expected) || expected.includes(candidate));
}

function dedupeEvents(events) {
  const seen = new Set();
  return (Array.isArray(events) ? events : []).filter((event) => {
    if (!event) return false;
    const key = `${normalizeName(getEventTitle(event))}|${normalizeName(getEventState(event))}|${event.timestamp || ''}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function feedEmptyOptions(type, stateName = selectedState) {
  const isFake = type === 'fake';
  return {
    type,
    emptyTitle: stateName
      ? (isFake ? `No alerts for ${stateName}` : `No verified news for ${stateName}`)
      : (isFake ? 'Clear signal' : 'Awaiting updates'),
    emptyDetail: isFake
      ? 'Monitoring for new misinformation signals across active map regions.'
      : 'Verified reports appear here as they are authenticated by the pipeline.'
  };
}

async function renderFeedsProgressively(fakeEvents, realEvents, generation, stateName) {
  if (generation !== feedsGeneration) return;
  const alertsEl = qs('#heatmap-misinformation-feed');
  const newsEl = qs('#heatmap-real-news-feed');
  const displayLimit = stateName ? 20 : FEED_DISPLAY_LIMIT;
  const fakeList = fakeEvents.slice(0, displayLimit);
  const realList = realEvents.slice(0, displayLimit);

  if (alertsEl) {
    if (fakeList.length) {
      replaceChildren(alertsEl, fakeList.map(event => createEventItem(event, { type: 'fake' })));
    } else {
      renderEventList('#heatmap-misinformation-feed', [], feedEmptyOptions('fake', stateName));
    }
    setText('#heatmap-misinformation-count', `${fakeList.length} item${fakeList.length === 1 ? '' : 's'}`);
  }
  if (newsEl) {
    if (realList.length) {
      replaceChildren(newsEl, realList.map(event => createEventItem(event, { type: 'real' })));
    } else {
      renderEventList('#heatmap-real-news-feed', [], feedEmptyOptions('real', stateName));
    }
    setText('#heatmap-real-news-count', `${realList.length} item${realList.length === 1 ? '' : 's'}`);
  }
}

async function updateFeeds(forceState = false, options = {}) {
  const feedAlerts = qs('#heatmap-misinformation-feed');
  const feedNews = qs('#heatmap-real-news-feed');
  const stateAtRequest = selectedState;
  const generation = ++feedsGeneration;

  // Immediately show loading placeholder in Alerts/Verified when state is selected/clicked
  if (stateAtRequest) {
    if (feedAlerts) replaceChildren(feedAlerts, [createFeedLoadingSpinner()]);
    if (feedNews) replaceChildren(feedNews, [createFeedLoadingSpinner()]);
  }

  const forceRefresh = Boolean(options.forceRefresh);

  if (forceRefresh && stateAtRequest) {
    clearStateEventsCache(stateAtRequest);
  }

  try {
    if (stateAtRequest) {
      // 1. Fetch latest 10 quickly
      const fetchOptions = forceRefresh ? { cacheMs: 0, force: true } : {};
      const events10 = await getStateEvents(stateAtRequest, { ...fetchOptions, limit: 10 });
      if (generation !== feedsGeneration) return;

      const deduped10 = dedupeEvents(events10);
      const filtered10 = deduped10.filter((event) => eventMatchesState(event, stateAtRequest));
      const fake10 = filtered10.filter((event) => getEventClassification(event) === 'fake');
      const real10 = filtered10.filter((event) => getEventClassification(event) === 'real');

      await renderFeedsProgressively(fake10, real10, generation, stateAtRequest);

      // 2. Fetch up to 20 in the background
      getStateEvents(stateAtRequest, { ...fetchOptions, limit: 20 })
        .then(async (events20) => {
          if (generation !== feedsGeneration) return;
          const deduped20 = dedupeEvents(events20);
          const filtered20 = deduped20.filter((event) => eventMatchesState(event, stateAtRequest));
          const fake20 = filtered20.filter((event) => getEventClassification(event) === 'fake');
          const real20 = filtered20.filter((event) => getEventClassification(event) === 'real');
          await renderFeedsProgressively(fake20, real20, generation, stateAtRequest);
        })
        .catch((err) => {
          console.warn('Background feed fetch failed:', err);
        });
    } else {
      // No state selected: fetch only live events (global pool)
      const fetchOptions = forceRefresh ? { cacheMs: 0, force: true } : {};
      const events = await getLiveEvents(LIVE_EVENTS_FETCH_LIMIT, fetchOptions);
      if (generation !== feedsGeneration) return;

      const deduped = dedupeEvents(events);
      const fakeEvents = deduped.filter((event) => getEventClassification(event) === 'fake');
      const realEvents = deduped.filter((event) => getEventClassification(event) === 'real');
      await renderFeedsProgressively(fakeEvents, realEvents, generation, stateAtRequest);
    }
  } catch (error) {
    if (generation !== feedsGeneration) return;
    console.error('Feed update failed:', error);
    if (feedAlerts) {
      renderEventList('#heatmap-misinformation-feed', [], {
        ...feedEmptyOptions('fake', stateAtRequest),
        emptyTitle: 'Feed unavailable',
        emptyDetail: 'Could not load events. Use Refresh to try again.'
      });
    }
    if (feedNews) {
      renderEventList('#heatmap-real-news-feed', [], {
        ...feedEmptyOptions('real', stateAtRequest),
        emptyTitle: 'Feed unavailable',
        emptyDetail: 'Could not load events. Use Refresh to try again.'
      });
    }
    setText('#heatmap-misinformation-count', '0 items');
    setText('#heatmap-real-news-count', '0 items');
  }
}

function setupControls() {
  const refresh = qs('#heatmap-refresh');
  const refreshHeader = qs('#heatmap-header-refresh');
  const refreshMobile = qs('#heatmap-refresh-mobile');

  const refreshHandler = () => refreshHeatmap(true);
  if (refresh) refresh.addEventListener('click', refreshHandler);
  if (refreshHeader) refreshHeader.addEventListener('click', refreshHandler);
  if (refreshMobile) refreshMobile.addEventListener('click', refreshHandler);

  const zoomInButton = qs('#heatmap-zoom-in');
  const zoomOutButton = qs('#heatmap-zoom-out');
  const zoomResetButton = qs('#heatmap-zoom-reset');
  if (zoomInButton) zoomInButton.addEventListener('click', () => zoomBy(BUTTON_ZOOM_STEP));
  if (zoomOutButton) zoomOutButton.addEventListener('click', () => zoomBy(-BUTTON_ZOOM_STEP));
  if (zoomResetButton) zoomResetButton.addEventListener('click', resetZoom);

  const scrollDownBtn = qs('#scroll-down-btn');
  if (scrollDownBtn) {
    scrollDownBtn.addEventListener('click', () => {
      window.scrollBy({
        top: window.innerHeight * 0.7,
        behavior: 'smooth'
      });
    });
  }

  const legendToggle = qs('#risk-legend-toggle');
  const legendPanel = qs('#risk-legend-panel');
  const legendIcon = qs('#risk-legend-icon');
  if (legendToggle && legendPanel) {
    legendToggle.addEventListener('click', () => {
      const expanded = legendToggle.getAttribute('aria-expanded') === 'true';
      legendToggle.setAttribute('aria-expanded', String(!expanded));
      if (expanded) {
        legendPanel.style.maxHeight = '0px';
        legendIcon.style.transform = 'rotate(-180deg)';
      } else {
        legendPanel.style.maxHeight = '500px';
        legendIcon.style.transform = 'rotate(0deg)';
      }
    });

    // Collapse legend by default for mobile phones and Nest Hub (1024x600) to save space
    // EXCLUDE Surface Duo (540x720) as per user request to show legend
    const isNestHub = window.innerWidth === 1024 && window.innerHeight === 600;
    const isSurfaceDuo = window.innerWidth === 540 && window.innerHeight === 720;
    if ((window.innerWidth < 600 && !isSurfaceDuo) || isNestHub) {
      legendToggle.setAttribute('aria-expanded', 'false');
      legendPanel.style.maxHeight = '0px';
      legendIcon.style.transform = 'rotate(-180deg)';
    }
  }


  // Tab Logic
  const tabAlerts = qs('#tab-alerts');
  const tabNews = qs('#tab-news');
  const panelAlerts = qs('#panel-alerts');
  const panelNews = qs('#panel-news');

  if (tabAlerts && tabNews && panelAlerts && panelNews) {
    const setActiveTab = (activeTab) => {
      if (activeTab === 'alerts') {
        tabAlerts.className = 'flex-1 rounded-lg px-4 py-2.5 text-xs font-bold uppercase tracking-widest transition-all duration-200 bg-white text-red-600 shadow-sm border border-slate-200';
        tabNews.className = 'flex-1 rounded-lg px-4 py-2.5 text-xs font-bold uppercase tracking-widest transition-all duration-200 text-slate-500 hover:text-slate-700';
        panelAlerts.classList.remove('hidden');
        panelNews.classList.add('hidden');
      } else {
        tabNews.className = 'flex-1 rounded-lg px-4 py-2.5 text-xs font-bold uppercase tracking-widest transition-all duration-200 bg-white text-emerald-600 shadow-sm border border-slate-200';
        tabAlerts.className = 'flex-1 rounded-lg px-4 py-2.5 text-xs font-bold uppercase tracking-widest transition-all duration-200 text-slate-500 hover:text-slate-700';
        panelNews.classList.remove('hidden');
        panelAlerts.classList.add('hidden');
      }
    };

    tabAlerts.addEventListener('click', () => setActiveTab('alerts'));
    tabNews.addEventListener('click', () => setActiveTab('news'));
  }

  const stateClearButton = qs('#heatmap-state-clear');
  if (stateClearButton) {
    stateClearButton.addEventListener('click', clearStateSelection);
  }

  const svgRoot = qs('#heatmap-svg-root');
  if (svgRoot) {
    svgRoot.addEventListener('click', (event) => {
      if (event.target && event.target.tagName !== 'path') {
        clearStateSelection();
      }
    });
  }

  setupEventModal();
  document.addEventListener('keydown', handleHeatmapShortcuts);
}

function setupEventModal() {
  const modal = qs('#event-detail-modal');
  const overlay = qs('#event-detail-overlay');
  const closeBtn = qs('#event-detail-close');

  if (!modal) return;
  let lastFocusedElement = null;

  const closeModal = () => {
    modal.classList.add('opacity-0', 'pointer-events-none');
    modal.classList.remove('opacity-100', 'pointer-events-auto');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('overflow-hidden');
    const card = qs('#event-detail-card');
    if (card) {
      card.classList.add('scale-95');
      card.classList.remove('scale-100');
    }
    if (lastFocusedElement instanceof HTMLElement) {
      lastFocusedElement.focus({ preventScroll: true });
    }
    lastFocusedElement = null;
  };

  closeBtn?.addEventListener('click', closeModal);
  overlay?.addEventListener('click', closeModal);
  modal.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab' || modal.classList.contains('pointer-events-none')) return;
    const focusable = qsa('button:not([disabled]), a[href]', modal)
      .filter((element) => element instanceof HTMLElement && !element.classList.contains('hidden'));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal.classList.contains('pointer-events-auto')) {
      closeModal();
    }
  });

  document.addEventListener('openEventModal', (e) => {
    lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    populateEventDetailModal(e.detail || {});

    // Show modal
    modal.classList.remove('opacity-0', 'pointer-events-none');
    modal.classList.add('opacity-100', 'pointer-events-auto');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('overflow-hidden');
    const card = qs('#event-detail-card');
    if (card) {
      card.classList.remove('scale-95');
      card.classList.add('scale-100');
    }
    closeBtn?.focus({ preventScroll: true });
  });
}

function setupZoomAndPan() {
  const root = qs('#heatmap-svg-root');
  if (!root || !svgMap) return;

  root.addEventListener('pointerenter', () => {
    mapInteractionActive = true;
  });
  root.addEventListener('focusin', () => {
    mapInteractionActive = true;
  });
  root.addEventListener('mousedown', () => {
    mapInteractionActive = true;
  });
  root.addEventListener('touchstart', () => {
    mapInteractionActive = true;
  }, { passive: true });

  root.addEventListener('wheel', (event) => {
    if (event.cancelable) event.preventDefault();
    const direction = event.deltaY > 0 ? -1 : 1;
    const magnitude = Math.min(1, Math.abs(event.deltaY) / 600);
    zoomBy(direction * 0.10 * Math.max(0.25, magnitude), event.clientX, event.clientY);
  }, { passive: false });

  root.addEventListener('mousedown', (event) => {
    if (event.button !== 0) return;
    isDragging = true;
    lastPointerX = event.clientX;
    lastPointerY = event.clientY;
    root.classList.add('cursor-grabbing');
  });

  document.addEventListener('mousemove', (event) => {
    if (!isDragging) return;
    currentX += event.clientX - lastPointerX;
    currentY += event.clientY - lastPointerY;
    lastPointerX = event.clientX;
    lastPointerY = event.clientY;
    updateTransform();
  });

  document.addEventListener('mouseup', () => {
    isDragging = false;
    root.classList.remove('cursor-grabbing');
  });

  root.addEventListener('touchstart', (event) => {
    if (event.touches.length === 2) {
      pinchStartDistance = getTouchDistance(event.touches);
      pinchStartZoom = currentZoom;
    } else if (event.touches.length === 1) {
      isDragging = true;
      lastPointerX = event.touches[0].clientX;
      lastPointerY = event.touches[0].clientY;
    }
  }, { passive: true });

  root.addEventListener('touchmove', (event) => {
    if (event.cancelable) event.preventDefault();
    if (event.touches.length === 2 && pinchStartDistance > 0) {
      const distance = getTouchDistance(event.touches);
      const ratio = distance / pinchStartDistance;
      const dampened = 1 + (ratio - 1) * 0.45;
      currentZoom = clampZoom(pinchStartZoom * dampened);
      updateTransform();
    } else if (event.touches.length === 1 && isDragging) {
      currentX += event.touches[0].clientX - lastPointerX;
      currentY += event.touches[0].clientY - lastPointerY;
      lastPointerX = event.touches[0].clientX;
      lastPointerY = event.touches[0].clientY;
      updateTransform();
    }
  }, { passive: false });

  root.addEventListener('touchend', () => {
    isDragging = false;
    pinchStartDistance = 0;
  });
}

function getTouchDistance(touches) {
  const dx = touches[0].clientX - touches[1].clientX;
  const dy = touches[0].clientY - touches[1].clientY;
  return Math.sqrt(dx * dx + dy * dy);
}

function clampZoom(value) {
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, value));
}

function zoomBy(delta, clientX, clientY) {
  const nextZoom = clampZoom(currentZoom + delta);
  applyZoom(nextZoom, clientX, clientY);
}

function applyZoom(nextZoom, clientX, clientY) {
  if (!svgMap) return;
  const root = qs('#heatmap-svg-root');
  const previous = currentZoom;
  if (previous === nextZoom) return;

  if (root && Number.isFinite(clientX) && Number.isFinite(clientY)) {
    const rect = root.getBoundingClientRect();
    const focalX = clientX - rect.left - rect.width / 2;
    const focalY = clientY - rect.top - rect.height / 2;
    const zoomRatio = nextZoom / previous;
    currentX = focalX - (focalX - currentX) * zoomRatio;
    currentY = focalY - (focalY - currentY) * zoomRatio;
  }

  currentZoom = nextZoom;
  updateTransform();
}

function resetZoom() {
  currentZoom = window.innerWidth < 1024 ? 0.95 : 1.15;
  currentX = 0;
  currentY = 0;
  updateTransform();
}

function updateTransform() {
  if (!svgMap) return;

  // Enforce bounds
  const root = qs('#heatmap-svg-root');
  if (root) {
    const rect = root.getBoundingClientRect();
    const halfW = rect.width / 2;
    const halfH = rect.height / 2;

    // Calculate allowed movement based on zoom
    // We want to keep the map somewhat visible at all times
    const maxShiftX = halfW * currentZoom + MAP_BOUNDS_PADDING;
    const maxShiftY = halfH * currentZoom + MAP_BOUNDS_PADDING;

    currentX = Math.max(-maxShiftX, Math.min(maxShiftX, currentX));
    currentY = Math.max(-maxShiftY, Math.min(maxShiftY, currentY));
  }

  svgMap.style.transform = `translate(${currentX}px, ${currentY}px) scale(${currentZoom})`;
  // setText('#heatmap-zoom-level', `${Math.round(currentZoom * 100)}%`);
}

function handleHeatmapShortcuts(event) {
  if (!event.ctrlKey || !mapInteractionActive || isInteractiveInput(event.target)) return;
  const key = event.key;
  if (key === '+' || key === '=') {
    event.preventDefault();
    zoomBy(BUTTON_ZOOM_STEP);
  } else if (key === '-') {
    event.preventDefault();
    zoomBy(-BUTTON_ZOOM_STEP);
  } else if (key === ' ') {
    event.preventDefault();
    resetZoom();
  }
}

function hydrateFeedsFromCache() {
  const payload = peekCached(`/api/v1/events/live?limit=${LIVE_EVENTS_FETCH_LIMIT}`);
  if (!payload) return;
  let events = Array.isArray(payload) ? payload : (payload.events || payload.data || []);
  if (!events.length) return;

  const active = activeMapStates();
  if (active.length) {
    const onMap = events.filter((event) =>
      active.some((record) => eventMatchesState(event, record.state || record.name))
    );
    if (onMap.length >= 3) events = onMap;
  }

  const fakeEvents = events.filter((event) => getEventClassification(event) === 'fake');
  const realEvents = events.filter((event) => getEventClassification(event) === 'real');
  renderEventList('#heatmap-misinformation-feed', fakeEvents, { type: 'fake', limit: FEED_DISPLAY_LIMIT });
  renderEventList('#heatmap-real-news-feed', realEvents, { type: 'real', limit: FEED_DISPLAY_LIMIT });
  setText('#heatmap-misinformation-count', `${Math.min(fakeEvents.length, FEED_DISPLAY_LIMIT)} items`);
  setText('#heatmap-real-news-count', `${Math.min(realEvents.length, FEED_DISPLAY_LIMIT)} items`);
}

export async function initHeatmap() {
  if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
  }
  window.scrollTo(0, 0);

  setupControls();
  mapStatus('Loading map', 'neutral');
  hydrateHeatmapFromCache();
  hydrateFeedsFromCache();
  updateStatsPopover();

  try {
    await loadSvgMap();
    syncHeatmapView();
  } catch (error) {
    console.error('Heatmap map load failed:', error);
    hideLoading();
    showMapError(error && error.message ? error.message : 'The local SVG could not be loaded.');
    mapStatus('Reconnecting to map frame...', 'neutral');
    return;
  }

  // Background refresh — map stays interactive; feeds fill progressively
  loadHeatmapData(false)
    .then(() => {
      syncHeatmapView();
      return Promise.allSettled([updateStats(), updateFeeds(false)]);
    })
    .catch((error) => console.warn('Heatmap data refresh:', error));

  window.setInterval(() => {
    if (document.visibilityState === 'visible') refreshHeatmap();
  }, 45000);
}
