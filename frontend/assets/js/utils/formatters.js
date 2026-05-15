import { toSafeText } from './security.js';

export function numberOrNull(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function formatCount(value, fallback = '--') {
  const number = numberOrNull(value);
  if (number === null) return fallback;
  const rounded = Math.max(0, Math.round(number));
  if (rounded >= 1000000) return `${(rounded / 1000000).toFixed(1)}M`;
  if (rounded >= 1000) return `${(rounded / 1000).toFixed(1)}K`;
  return String(rounded);
}

export function normalizePercent(value) {
  const number = numberOrNull(value);
  if (number === null) return null;
  const percent = Math.abs(number) <= 1 ? number * 100 : number;
  return Math.max(0, Math.min(100, percent));
}

export function formatPercent(value, fallback = '--', decimals = 0) {
  const percent = normalizePercent(value);
  if (percent === null) return fallback;
  if (decimals > 0) {
    return `${percent.toFixed(decimals)}%`;
  }
  return `${Math.round(percent)}%`;
}

export function formatRatioAsPercent(value, fallback = '--') {
  const number = numberOrNull(value);
  if (number === null) return fallback;
  return `${Math.round(Math.max(0, Math.min(100, number * 100)))}%`;
}

export function formatDateTime(value, fallback = '--') {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return date.toLocaleString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    day: '2-digit',
    month: 'short'
  });
}

export function formatClock(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '--';
  return date.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  });
}

export function normalizeClassification(value) {
  const text = toSafeText(value, 'unknown').toLowerCase();
  if (['fake', 'misinformation', 'misleading', 'false'].includes(text)) return 'fake';
  if (['real', 'verified', 'true', 'credible'].includes(text)) return 'real';
  if (['uncertain', 'review', 'under_review', 'needs_review'].includes(text)) return 'uncertain';
  return 'unknown';
}

export function classificationLabel(value) {
  const classification = normalizeClassification(value);
  if (classification === 'fake') return 'Misinformation';
  if (classification === 'real') return 'Verified';
  if (classification === 'uncertain') return 'Under review';
  return 'Unknown';
}

export function getEventTitle(event) {
  return toSafeText(event && (event.title || event.headline || event.name), 'Untitled event');
}

export function getEventSource(event) {
  return toSafeText(event && (event.source || event.source_name || event.publisher), 'Unknown source');
}

export function getEventState(event) {
  return toSafeText(event && (event.state || event.region || event.location), 'India');
}

export function normalizeName(value) {
  return toSafeText(value, '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export const RISK_LEVELS = {
  least: {
    key: 'least',
    label: 'Least',
    color: '#138808',
    badgeClass: 'border-emerald-200 bg-emerald-50 text-emerald-700'
  },
  leastMedium: {
    key: 'least-medium',
    label: 'Least-Medium',
    color: '#facc15',
    badgeClass: 'border-yellow-200 bg-yellow-50 text-yellow-700'
  },
  mediumHigh: {
    key: 'medium-high',
    label: 'Medium-High',
    color: '#f97316',
    badgeClass: 'border-orange-200 bg-orange-50 text-orange-700'
  },
  high: {
    key: 'high',
    label: 'High',
    color: '#ef4444',
    badgeClass: 'border-red-200 bg-red-50 text-red-700'
  },
  insufficient: {
    key: 'insufficient-data',
    label: 'Insufficient data',
    color: '#94a3b8',
    badgeClass: 'border-slate-200 bg-slate-50 text-slate-600'
  }
};

export function getFakeRatio(record = {}) {
  const candidates = [
    record.fake_probability,
    record.fake_ratio,
    record.fake_news_ratio,
    record.fakeRate,
    record.fake_rate
  ];
  const ratio = candidates.map(numberOrNull).find((value) => value !== null);
  if (ratio !== undefined) {
    return ratio > 1 ? ratio / 100 : ratio;
  }

  const fake = numberOrNull(record.fake_count ?? record.fake_events);
  const total = numberOrNull(record.event_count ?? record.total_events);
  if (fake !== null && total !== null && total > 0) return fake / total;
  return null;
}

export function riskFromRecord(record = {}) {
  const level = toSafeText(record.risk_level, '').toLowerCase().replace(/[\s-]+/g, '_');
  if (['low', 'least'].includes(level)) return RISK_LEVELS.least;
  if (['low_medium', 'least_medium', 'least_medium_risk'].includes(level)) return RISK_LEVELS.leastMedium;
  if (['medium', 'medium_high', 'moderate'].includes(level)) return RISK_LEVELS.mediumHigh;
  if (level === 'high') return RISK_LEVELS.high;
  if (level === 'insufficient_data' || level === 'no_data') return RISK_LEVELS.insufficient;

  const ratio = getFakeRatio(record);
  if (ratio === null) return RISK_LEVELS.insufficient;
  if (ratio < 0.02) return RISK_LEVELS.least;
  if (ratio < 0.05) return RISK_LEVELS.leastMedium;
  if (ratio < 0.10) return RISK_LEVELS.mediumHigh;
  return RISK_LEVELS.high;
}
